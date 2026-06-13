"""backends/pygame/render.py —— Pygame 网格渲染器（路线 A：只换皮）。

实现 core.interfaces.Renderer 协议（render / close）。它从后端无关的 env
读 grid 数据 + agents pose，用 pygame 离屏 Surface 画一帧；每帧存 PNG，
close() 时用 PIL 把帧序列合成 GIF。

为什么能复用现有逻辑：规划器 / 执行器 / minigrid 物理完全照旧，本渲染器
只是经 executor 的 on_step 回调被外置调用（executor 自身从不调渲染）。

远程友好：默认 headless（SDL_VIDEODRIVER=dummy），无显示器也能跑出 GIF/PNG。

它向 env 要的数据（鸭子接口，minigrid env 已满足）：
    env.width / env.height                  网格尺寸
    env.grid.get(i, j)                      cell：.type / .color / .is_open
    env.get_room_index((i, j))              房间编号（用于房间底色）
    env.agents[i].position / .direction     agent 位姿（direction 0..3）
    env.agents[i].carrying                  持有物（画在 agent 身上）
"""
from __future__ import annotations

import os
import time
from pathlib import Path
from typing import List, Optional, Tuple

# headless 默认：必须在 import pygame 之前设好，远程无显示器也能离屏渲染。
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame  # noqa: E402

from themes import get_theme, Theme  # noqa: E402

# minigrid 的 4 向：0→右 1→下 2→左 3→上（与 DIR_TO_VEC 一致）。
_DIR_VEC = [(1, 0), (0, 1), (-1, 0), (0, -1)]


class PygameGridRenderer:
    """把一个网格世界画成 PNG 帧序列，收尾合成 GIF。

    Args:
        theme:    主题名（"home" / "battle" / ...）或 Theme 实例。
        mode:     "save_gif"（默认，攒帧→GIF）/ "save_frames"（只存 PNG）/
                  "both"（两者都要）/ "live"（开一个真实窗口实时播放，不存盘）。
        out_dir:  输出目录（PNG 帧 + 最终 GIF）。"live" 模式不写盘。
        tile:     每格像素边长。
        fps:      合成 GIF 的帧率，"live" 模式下也用作实时播放的节流帧率。
        gif_name: 输出 GIF 文件名。
        live:     便捷开关；为 True 时等价于把 mode 强制设为 "live"。教学脚本
                  （examples/projects）用它开窗口实时观看带中文标签 / 家具 /
                  掩体的增强画面，而不是只在结尾出一张 GIF。
    """

    def __init__(
        self,
        theme="home",
        *,
        mode: str = "save_gif",
        out_dir: str = "app/output/pygame",
        tile: int = 40,
        fps: float = 6.0,
        gif_name: str = "replay.gif",
        live: bool = False,
    ) -> None:
        self.theme: Theme = theme if isinstance(theme, Theme) else get_theme(theme)
        self.mode = "live" if live else mode
        self.out_dir = Path(out_dir)
        self.tile = tile
        self.fps = fps
        self.gif_name = gif_name

        self._frame_paths: List[Path] = []
        self._surfaces: List[pygame.Surface] = []
        self._step = 0
        self._inited = False
        self._font: Optional[pygame.font.Font] = None

        # ── live（实时窗口）模式专用状态 ──
        self._live = self.mode == "live"
        self._screen: Optional[pygame.Surface] = None   # 真实窗口 Surface
        self._closed_by_user = False                     # 用户点了关闭按钮
        self._last_blit = 0.0                            # 节流用的上一帧时刻

        # save_* 模式才需要落盘目录；live 模式不写盘。
        if not self._live:
            self.out_dir.mkdir(parents=True, exist_ok=True)

    # ───────────────────────── Renderer 协议 ─────────────────────────
    def render(self, backend) -> None:
        """把 backend 当前状态画成一帧。被 executor 的 on_step 回调驱动。"""
        if not self._inited:
            self._init_pygame()

        surf = self._draw_frame(backend)

        if self._live:
            self._blit_live(surf)
        else:
            if self.mode in ("save_frames", "both"):
                p = self.out_dir / f"frame_{self._step:04d}.png"
                pygame.image.save(surf, str(p))
                self._frame_paths.append(p)
            if self.mode in ("save_gif", "both"):
                self._surfaces.append(surf.copy())
        self._step += 1

    def _init_pygame(self) -> None:
        """首帧惰性初始化 pygame；live 模式额外开一个真实窗口。

        live 模式必须让 SDL 用真实视频驱动——而模块顶部为了远程友好把
        ``SDL_VIDEODRIVER`` 默认设成了 ``dummy``。这里在确实要开窗口时，把那个
        *仅由我们用 setdefault 写入的* dummy 值清掉，让 SDL 回到系统默认驱动
        （macOS=cocoa / Linux=x11 等）。若用户自己显式设了 dummy，我们不动它，
        于是 set_mode 会拿到一个离屏 surface——窗口开不出来但不至于崩。
        """
        if self._live and os.environ.get("SDL_VIDEODRIVER") == "dummy":
            # 仅当当前进程没有可用显示器时才会真正失败；正常桌面会被清掉。
            os.environ.pop("SDL_VIDEODRIVER", None)
        # 硬保险：若 display 子系统已被**别处提前初始化**（最典型是 env 构造期
        # render_mode="human" 触发过一次），它可能已经绑定了 dummy 驱动且不会
        # 因为 set_mode 自动重选。live 模式下先把 display 关掉、确保环境变量为
        # 真实驱动，再让下面的 pygame.init() 用 cocoa/x11 重新初始化。
        if self._live and pygame.display.get_init():
            cur = None
            try:
                cur = pygame.display.get_driver()
            except Exception:
                pass
            if cur == "dummy":
                pygame.display.quit()
                os.environ.pop("SDL_VIDEODRIVER", None)
        pygame.init()
        self._font = self._load_font(13)
        self._inited = True

    def _blit_live(self, surf: pygame.Surface) -> None:
        """把离屏帧贴到真实窗口并刷新，按 fps 节流 + 处理窗口事件。

        关键：节流期间**必须持续泵事件**，不能用 ``time.sleep()`` 把主线程整段
        睡死。macOS 的 WindowServer 要求 App 持续回应事件，否则窗口会被标成「未
        响应」——红叉点不动、转圈鼠标，只能 Ctrl+C 杀进程（这正是之前的现象）。
        这里把等待拆成许多 ~16ms 的小片，每片都 flip + 泵一次事件，窗口全程灵敏。
        """
        if self._screen is None:
            pygame.display.set_caption(
                f"MRBTP · {self.theme.name}  —— 关闭窗口或按 Esc 退出"
            )
            self._screen = pygame.display.set_mode(surf.get_size())
            # macOS 关键修复：WorkBuddy 自带的解释器是 python-build-standalone，
            # **不是 framework build**（sysconfig PYTHONFRAMEWORK 为空）。这类进程
            # 默认不是「前台 GUI 应用」，set_mode 能拿到合法 surface（所以 hold_open
            # 照常卡循环），但 Cocoa 不把窗口提到前台、甚至不渲染——表现就是「程序
            # 在跑、屏幕上却没有窗口」。用 AppKit 显式 activate + 把每个 NSWindow
            # makeKeyAndOrderFront 才是完整解法（见 _macos_bring_to_front 的注释）。
            #
            # 时序要点：SDL 的 NSWindow 往往要等第一次 flip 之后才真正实例化，
            # 所以这里画一帧→flip→再 bring_to_front，并在预热循环里重复几轮，
            # 确保「窗口已存在」时至少有一次成功的提前调用。
            self._screen.blit(surf, (0, 0))
            pygame.display.flip()
            self._macos_bring_to_front()
            # 再泵几轮事件 + 画一帧并 flip + 反复提前，确保窗口真正可见。
            for _ in range(5):
                self._pump_events()
                self._screen.blit(surf, (0, 0))
                pygame.display.flip()
                self._macos_bring_to_front()
                time.sleep(0.02)

        # 先把这一帧画出去。
        self._pump_events()
        self._screen.blit(surf, (0, 0))
        pygame.display.flip()

        # 节流：保持和 GIF 同样的可观看速度。等待期间持续泵事件，保证窗口灵敏。
        if self.fps and self.fps > 0:
            deadline = time.time() + 1.0 / self.fps
            while time.time() < deadline and not self._closed_by_user:
                self._pump_events()
                pygame.display.flip()
                time.sleep(0.016)   # ~60Hz 事件轮询，远比一帧间隔细
        self._last_blit = time.time()

    def _pump_events(self) -> None:
        """抽干事件队列；记录用户是否点了关闭按钮 / 按下 Esc。"""
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                self._closed_by_user = True
            elif ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                self._closed_by_user = True

    @staticmethod
    def _macos_bring_to_front() -> None:
        """macOS：把当前进程激活成前台 GUI 应用，并把窗口真正提到屏幕最前。

        仅在 macOS 生效；其它平台直接返回。背景见 :meth:`_blit_live` 里的注释——
        python-build-standalone 这类非 framework 解释器开出的窗口默认拿不到前台。

        **关键经验**：光调 ``NSApp.activateIgnoringOtherApps_(True)`` 只激活了
        *应用进程*，窗口对象虽然创建成功（set_mode 返回合法 surface），但不会自动
        浮到可见层——表现就是「程序在跑、却看不到窗口」。必须再枚举 ``NSApp.windows()``
        逐个调用 ``makeKeyAndOrderFront_`` + ``orderFrontRegardless``，并临时把窗口
        层级抬到 floating（setLevel_(3)）「踹」一下，才能确保它真正出现在屏幕上；
        之后再把层级降回普通（setLevel_(0)），避免一直压住其它应用。

        装了 ``pyobjc-framework-Cocoa`` 才生效；没装就静默跳过（此时若窗口仍不可见，
        需要 ``pip install pyobjc-framework-Cocoa``）。
        """
        import sys as _sys
        if _sys.platform != "darwin":
            return
        try:
            from AppKit import NSApplication, NSApp  # type: ignore
            NSApplication.sharedApplication()
            # NSApplicationActivationPolicyRegular = 0：成为正常的前台应用，
            # 让窗口能显示、能拿焦点、能出现在 Dock。
            try:
                NSApp.setActivationPolicy_(0)
            except Exception:
                pass
            NSApp.activateIgnoringOtherApps_(True)
            # —— 决定性一步：把每个 NSWindow 真正提到最前 ——
            try:
                windows = list(NSApp.windows())
            except Exception:
                windows = []
            for _w in windows:
                try:
                    _w.setLevel_(3)                 # NSFloatingWindowLevel：强行浮顶
                    _w.makeKeyAndOrderFront_(None)
                    _w.orderFrontRegardless()
                except Exception:
                    pass
            # 提前完成后恢复普通层级，避免长期压住别的窗口。
            for _w in windows:
                try:
                    _w.setLevel_(0)
                except Exception:
                    pass
        except Exception:
            # 没装 pyobjc 或调用失败：不影响其它平台 / GIF 模式，静默跳过。
            pass

    def hold_open(self) -> None:
        """live 模式收尾：任务跑完后保持窗口开着，直到用户关闭它。

        非 live 模式（攒 GIF / 存帧）调用此方法是无害的 no-op。
        """
        if not self._live or self._screen is None or self._closed_by_user:
            return
        clock = pygame.time.Clock()
        while not self._closed_by_user:
            self._pump_events()
            pygame.display.flip()
            clock.tick(30)

    @staticmethod
    def _load_font(size: int) -> "pygame.font.Font":
        """加载一个**支持中文**的字体。

        渲染器要画「厨房 / 掩体」等中文标签，而 pygame 默认的 menlo/consolas
        等等宽英文字体没有 CJK 字形，会渲成豆腐块（□）。这里优先试常见的系统
        CJK 字体文件（macOS / Linux / Windows 都覆盖一些），全失败才退回默认
        英文字体。
        """
        # 1) 先试按字体名匹配（pygame 会做模糊匹配）。
        for name in ("pingfangsc,pingfang,stheiti,heiti,notosanscjksc,"
                     "microsoftyahei,simhei,arialunicodems"):
            try:
                path = pygame.font.match_font(name)
                if path:
                    return pygame.font.Font(path, size)
            except Exception:
                pass
        # 2) 再试常见的系统字体文件绝对路径。
        candidates = [
            "/System/Library/Fonts/PingFang.ttc",            # macOS
            "/System/Library/Fonts/STHeiti Light.ttc",       # macOS
            "/System/Library/Fonts/Hiragino Sans GB.ttc",    # macOS
            "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",  # Linux
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
            "C:/Windows/Fonts/msyh.ttc",                     # Windows 雅黑
            "C:/Windows/Fonts/simhei.ttf",
        ]
        for path in candidates:
            if os.path.exists(path):
                try:
                    return pygame.font.Font(path, size)
                except Exception:
                    pass
        # 3) 全失败：退回默认字体（中文仍会是豆腐块，但不至于崩）。
        try:
            return pygame.font.SysFont("menlo,consolas,monospace", size)
        except Exception:
            return pygame.font.Font(None, size + 3)

    def close(self) -> Optional[str]:
        """收尾：合成 GIF（如启用），关闭 pygame。返回 GIF 路径或 None。

        live 模式不写盘、不合成 GIF——窗口的存活由 :meth:`hold_open` 控制，
        这里只负责释放 pygame。
        """
        gif_path: Optional[str] = None
        if (not self._live and self.mode in ("save_gif", "both")
                and self._surfaces):
            gif_path = self._compose_gif()
        if self._inited:
            pygame.quit()
            self._inited = False
            self._screen = None
        return gif_path

    # ───────────────────────── 内部：画一帧 ─────────────────────────
    def _draw_frame(self, backend) -> pygame.Surface:
        w, h, t = backend.width, backend.height, self.tile
        margin_top = 28  # 顶部留一条状态带
        surf = pygame.Surface((w * t, h * t + margin_top))
        surf.fill(self.theme.background)

        # 1) 房间底色（先铺，作为地板）
        for j in range(h):
            for i in range(w):
                ri = self._safe_room_index(backend, (i, j))
                if ri >= 0:
                    pygame.draw.rect(
                        surf, self.theme.room_color(ri),
                        (i * t, j * t + margin_top, t, t),
                    )

        # 2) 房间语义标签（铺在地板之上、网格线之下）。仅当场景挂了
        #    ``scene_room_aliases`` 时才画——规划器无关的纯表现层信息。
        self._draw_room_labels(surf, backend, margin_top)

        # 3) 装饰 / 家具 / 掩体（场景元数据 ``scene_decor``，铺在地板之上）。
        #    这些东西**不在网格几何里**，规划器看不到，只有这里画。
        self._draw_decor(surf, backend, margin_top)

        # 4) 网格线
        for i in range(w + 1):
            pygame.draw.line(surf, self.theme.grid_line,
                             (i * t, margin_top), (i * t, h * t + margin_top))
        for j in range(h + 1):
            pygame.draw.line(surf, self.theme.grid_line,
                             (0, j * t + margin_top), (w * t, j * t + margin_top))

        # 5) 静态对象：墙 / 门 / 球 / 钥匙
        for j in range(h):
            for i in range(w):
                cell = backend.grid.get(i, j)
                if cell is not None:
                    self._draw_cell(surf, cell, i, j, margin_top)

        # 6) agents（画在最上层，按 render_style 选形状 + 朝向）
        for agent in backend.agents:
            self._draw_agent(surf, agent, margin_top)

        # 7) 顶部状态带
        if self._font is not None:
            txt = f"{self.theme.name}  ·  step {self._step}"
            label = self._font.render(txt, True, self.theme.label)
            surf.blit(label, (8, 6))

        return surf

    def _draw_room_labels(self, surf, backend, off) -> None:
        """把每个房间的中文别名画在该房间的几何中心。"""
        aliases = getattr(backend, "scene_room_aliases", None)
        if not aliases or self._font is None:
            return
        t = self.tile
        w, h = backend.width, backend.height
        # 收集每个房间的格子，算几何中心。
        cells: dict = {}
        for j in range(h):
            for i in range(w):
                ri = self._safe_room_index(backend, (i, j))
                if ri >= 0:
                    cells.setdefault(ri, []).append((i, j))
        for ri, name in aliases.items():
            pts = cells.get(ri)
            if not pts:
                continue
            cx = sum(p[0] for p in pts) / len(pts)
            cy = sum(p[1] for p in pts) / len(pts)
            label = self._font.render(str(name), True, self.theme.label)
            rect = label.get_rect(center=(int(cx * t + t / 2),
                                          int(cy * t + t / 2) + off))
            # 半透明描底，避免标签被底色淹没。
            bg = pygame.Surface((rect.width + 8, rect.height + 4), pygame.SRCALPHA)
            bg.fill((0, 0, 0, 110))
            surf.blit(bg, (rect.x - 4, rect.y - 2))
            surf.blit(label, rect)

    def _draw_decor(self, surf, backend, off) -> None:
        """画场景装饰元数据（家具 / 掩体 / 绿植 / 补给点）。

        每项是一个 dict：{"kind", "cell":(x,y), "size":(w,h), "label", "color"?}。
        规划器完全不知道这些东西——它们既不是墙也不是可拿物，纯表现层。
        """
        decor = getattr(backend, "scene_decor", None)
        if not decor:
            return
        t = self.tile
        for item in decor:
            try:
                kind = item.get("kind", "furniture")
                cx, cy = item["cell"]
                sw, sh = item.get("size", (1, 1))
            except Exception:
                continue
            x, y = cx * t, cy * t + off
            ww, hh = sw * t, sh * t
            color = item.get("color") or self.theme.decor_color(kind)

            if kind == "plant":
                # 绿植：圆形树冠
                pygame.draw.circle(surf, color,
                                   (x + ww // 2, y + hh // 2), min(ww, hh) // 2 - 2)
            elif kind == "supply":
                # 补给点：空心方框 + 内部小十字
                pygame.draw.rect(surf, color, (x + 3, y + 3, ww - 6, hh - 6), width=3)
                pygame.draw.line(surf, color, (x + ww // 2, y + 6),
                                 (x + ww // 2, y + hh - 6), 2)
                pygame.draw.line(surf, color, (x + 6, y + hh // 2),
                                 (x + ww - 6, y + hh // 2), 2)
            elif kind == "cover":
                # 掩体：实心障碍块 + 斜纹质感
                pygame.draw.rect(surf, color, (x + 2, y + 2, ww - 4, hh - 4),
                                 border_radius=3)
                hatch = tuple(min(255, c + 30) for c in color)
                step = max(6, t // 4)
                for d in range(0, ww + hh, step):
                    pygame.draw.line(surf, hatch,
                                     (x + 2, y + 2 + d), (x + 2 + d, y + 2), 1)
            else:  # furniture（默认）：圆角矩形 + 描边
                pygame.draw.rect(surf, color, (x + 3, y + 3, ww - 6, hh - 6),
                                 border_radius=4)
                edge = tuple(min(255, c + 40) for c in color)
                pygame.draw.rect(surf, edge, (x + 3, y + 3, ww - 6, hh - 6),
                                 width=1, border_radius=4)

            # 标签（家具名 / 掩体），画在图标中央偏下。
            label_txt = item.get("label")
            if label_txt and self._font is not None:
                lab = self._font.render(str(label_txt), True, self.theme.label)
                lr = lab.get_rect(center=(x + ww // 2, y + hh - max(8, t // 4)))
                surf.blit(lab, lr)

    def _draw_cell(self, surf, cell, i, j, off) -> None:
        t = self.tile
        x, y = i * t, j * t + off
        ctype = getattr(cell, "type", None)
        cname = getattr(cell, "color", None)

        if ctype == "wall":
            pygame.draw.rect(surf, self.theme.wall, (x, y, t, t))
        elif ctype == "door":
            is_open = bool(getattr(cell, "is_open", False))
            col = self.theme.door_open if is_open else self.theme.door_closed
            if is_open:
                # 开门：画一个空框，表示可通行
                pygame.draw.rect(surf, col, (x + 2, y + 2, t - 4, t - 4), width=3)
            else:
                pygame.draw.rect(surf, col, (x + 2, y + 2, t - 4, t - 4))
        elif ctype == "ball":
            pygame.draw.circle(surf, self.theme.object_color(cname),
                               (x + t // 2, y + t // 2), t // 3)
        elif ctype == "key":
            col = self.theme.object_color(cname)
            pygame.draw.circle(surf, col, (x + t // 2, y + t // 3), t // 6)
            pygame.draw.rect(surf, col, (x + t // 2 - 2, y + t // 3, 4, t // 2))
        elif ctype == "goal":
            pygame.draw.rect(surf, self.theme.object_color(cname or "green"),
                             (x + 4, y + 4, t - 8, t - 8))
        else:
            # 未知类型：用 fallback 描个边，方便发现没画对的东西
            pygame.draw.rect(surf, self.theme.object_fallback,
                             (x + 6, y + 6, t - 12, t - 12), width=2)

    def _draw_agent(self, surf, agent, off) -> None:
        t = self.tile
        pos = agent.position
        if pos is None or pos[0] < 0:
            return
        cx = pos[0] * t + t // 2
        cy = pos[1] * t + t // 2 + off
        aid = int(getattr(agent, "id", 0))

        # render_style 是可选的纯表现层属性（{shape,color,size}），只有渲染器读它；
        # 规划器从不看 agent 外观。缺省时按 agent 编号循环取色、画朝向三角。
        style = getattr(agent, "render_style", None) or {}
        color = style.get("color") or self.theme.agent_color(aid)
        shape = style.get("shape", "triangle")
        size_scale = float(style.get("size", 1.0))
        r = int((t // 2 - 4) * size_scale)

        d = int(getattr(agent, "direction", 0)) % 4
        dx, dy = _DIR_VEC[d]

        if shape == "circle":
            # 圆 + 一个朝向小缺口（短线指向 direction）
            pygame.draw.circle(surf, color, (cx, cy), r, width=3)
            pygame.draw.line(surf, color, (cx, cy),
                             (cx + dx * r, cy + dy * r), 3)
        elif shape == "square":
            pygame.draw.rect(surf, color,
                             (cx - r, cy - r, 2 * r, 2 * r), width=3, border_radius=3)
            pygame.draw.line(surf, color, (cx, cy),
                             (cx + dx * r, cy + dy * r), 3)
        else:  # triangle（默认）：尖端指向 direction
            tip = (cx + dx * r, cy + dy * r)
            px, py = -dy, dx
            base1 = (cx - dx * r + px * r * 0.7, cy - dy * r + py * r * 0.7)
            base2 = (cx - dx * r - px * r * 0.7, cy - dy * r - py * r * 0.7)
            pygame.draw.polygon(surf, color, [tip, base1, base2])

        # 持有物：在 agent 中心画一个小圈表示
        carrying = getattr(agent, "carrying", None)
        if carrying is not None:
            ccol = self.theme.object_color(getattr(carrying, "color", None))
            pygame.draw.circle(surf, ccol, (cx, cy), t // 7)

    # ───────────────────────── 内部：工具 ─────────────────────────
    @staticmethod
    def _safe_room_index(backend, pos) -> int:
        try:
            return backend.get_room_index(pos)
        except Exception:
            return -1

    def _compose_gif(self) -> str:
        """用 PIL 把攒下的 pygame Surface 合成 GIF。"""
        from PIL import Image

        frames = []
        for s in self._surfaces:
            raw = pygame.image.tostring(s, "RGB")
            img = Image.frombytes("RGB", s.get_size(), raw)
            frames.append(img)

        gif_path = self.out_dir / self.gif_name
        duration_ms = int(1000.0 / max(self.fps, 0.1))
        frames[0].save(
            str(gif_path),
            save_all=True,
            append_images=frames[1:],
            duration=duration_ms,
            loop=0,
            optimize=True,
        )
        return str(gif_path)
