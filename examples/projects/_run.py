"""examples/projects/_run.py —— 三个练习共用的「跑 + 实时可视化」运行器。

把 starter / solution 里高度重复的样板收拢到一处：规划 → 执行 → 用 **pygame
增强渲染器**（带中文房间名 / 家具 / 掩体 / agent 形状）实时画到一个窗口，行为树
tick 同步打印到终端；任务成功后窗口停住，关掉即退出。

为什么不再用 minigrid 原生窗口
------------------------------
练习场景已经换成各自专属的独立地图（``home`` 用 _home_map、``battle`` 用
_battle_map）。这些地图的「卧室 / 掩体」等语义和家具元数据只有 **pygame 增强
渲染器** 认得；minigrid 的原生 ``env.render()`` 只会画灰底色块。所以这里统一
走 ``PygameGridRenderer(live=True)``，让练习窗口和 ``python -m app.run
--renderer pygame`` 跑出来的成品画面完全一致。

无显示器 / SSH / CI：传 ``--headless`` 自动切到 dummy 视频驱动，只在终端打印
行为树 tick，不开窗口。
"""
from __future__ import annotations

import os
import random
import sys
from pathlib import Path
from typing import Callable

# 让脚本无论从哪个目录、哪个嵌套层级运行，都能 import 到仓库顶层的 scenes / app。
# starter.py 在 projN_xxx/ 下（parents[2] = projects/，parents[3] = 仓库根）；
# solution/solve.py 多一层（parents[4] = 仓库根）。两种都覆盖到。
_HERE = Path(__file__).resolve()
for _root in (_HERE.parents[2], _HERE.parents[1]):
    if (_root / "app").is_dir() and (_root / "scenes").is_dir():
        if str(_root) not in sys.path:
            sys.path.insert(0, str(_root))
        break


def _displayable_reason() -> tuple[bool, str]:
    """判断当前进程能不能开出真实窗口，并返回**人话理由**（便于自诊断）。

    开不出窗口的典型场景：SSH / CI / 容器里跑——拿不到本机窗口服务
    （macOS 的 WindowServer、Linux 的 X11/Wayland）。这时硬开 ``live`` 窗口
    要么静默失败、要么崩，用户只看到终端在刷 tick 却没有画面。

    关键设计：**本函数不再因 ``SDL_VIDEODRIVER=dummy`` 就否决窗口**。那个变量
    极易被早先跑过的无头脚本 / 手动 ``export`` 残留在 shell 里，一旦残留就会
    让本该弹窗的练习静默退化成纯终端——这正是「BT 在跑却没有窗口」最常见的
    坑。是否要无头由命令行参数（``--headless`` / ``--gif``）显式表达，环境变量
    只作旁证打印，不参与否决。

    判据：
      * Linux 下既没有 ``DISPLAY`` 又没有 ``WAYLAND_DISPLAY`` → 没有图形会话。
      * 其余（macOS 桌面 / 有 DISPLAY 的 Linux）→ 放行，真开不出来再退化。
    """
    if sys.platform.startswith("linux"):
        if os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"):
            return True, "Linux 图形会话可用"
        return False, "Linux 下没有 DISPLAY / WAYLAND_DISPLAY（无图形会话）"
    return True, f"{sys.platform} 桌面默认可开窗口"


def run_scenario(
    build_scenario: Callable[[], "object"],
    *,
    theme: str,
    success_msg: str,
    headless: bool = False,
    record_gif: bool = False,
    gif_path: str | None = None,
    attempts: int = 6,
    fps: float = 6.0,
    max_steps: int = 400,
) -> bool:
    """规划并执行一个练习场景，可选实时窗口 / 录制 GIF / 纯终端三种可视化。

    三种可视化模式（互斥，按优先级）：
      * ``record_gif=True``：把整段回放录成一个 GIF 文件（默认存到
        ``app/output/projects/<场景>.gif``）——**无显示器也能用**，跑完打印
        文件路径，最适合 SSH / 沙箱 / 写教程截图。
      * ``headless=True`` 或当前环境开不出窗口：只在终端打印行为树 tick。
      * 否则：开一个 pygame 实时窗口边跑边画，任务成功后停在末帧等用户关窗。

    Args:
        build_scenario: 无参工厂，返回一个 ``app.scenario.Scenario``。每次重试都
            重新调用它，拿到干净的初始世界。
        theme:    pygame 渲染器配色主题（``"home"`` / ``"battle"``）。
        success_msg: 成功时打印的中文提示（会自动补上步数）。
        headless: True = 不开窗口、只打印（SSH/CI 友好）。
        record_gif: True = 录制 GIF 而不是开实时窗口。
        gif_path: GIF 输出路径；为 None 时落到 ``app/output/projects/replay.gif``。
        attempts: 最多重试几次（执行有随机性，单次约 70% 成功）。
        fps:      实时播放 / GIF 帧率。
        max_steps: 单次执行的安全步数上限。

    Returns:
        是否最终成功。
    """
    # 决定走哪种可视化。GIF 优先；否则 headless / 真开不出窗口 → 纯终端；
    # 剩下才开真实窗口。GIF 与窗口都走 pygame 增强渲染器，画面完全一致。
    can_show, why = _displayable_reason()
    want_window = (not record_gif) and (not headless) and can_show

    if headless and not record_gif:
        # 用户显式要无头：这时才设 dummy。
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

    # 延迟到设好 SDL 之后再 import，确保 headless 时不会尝试开真实窗口。
    # 注意：import backends.pygame.render 时它顶部会 setdefault SDL_VIDEODRIVER=dummy
    # （为远程 GIF 友好）。所以「清掉残留 dummy」必须放在 import **之后**——否则刚
    # pop 掉又被 import 设回来，窗口仍开不出。
    from app.planner import plan_behavior_trees
    from app.executor import execute
    from app.visualize import Visualizer
    from core.interfaces import make_renderer

    if want_window and os.environ.get("SDL_VIDEODRIVER") == "dummy":
        # 用户没要无头、环境却有 dummy（先前无头脚本/手动 export 残留，或刚才 import
        # render.py 顶部 setdefault 写进来的）。它会让窗口静默开不出来——这正是
        # 「BT 在跑却没画面」的元凶。既然此刻明确要窗口，就主动清掉它，让 SDL 回到
        # 系统默认驱动（cocoa/x11）。
        os.environ.pop("SDL_VIDEODRIVER", None)
        print("⚠️ 检测到 SDL_VIDEODRIVER=dummy，已自动清除以便开窗。")

    scenario = build_scenario()
    print(f"目标 goal = {set(scenario.goal)}")
    print(f"团队规模 = {scenario.num_agent} 个机器人")
    if record_gif:
        print("可视化：录制 GIF（无需显示器）")
    elif want_window:
        print("可视化：实时 pygame 窗口")
    else:
        # 没开窗口：说清是用户主动要的（--headless）还是环境开不出。
        if headless:
            print("可视化：纯终端（--headless；想要画面去掉它，或加 --gif 出图）")
        else:
            print(f"可视化：纯终端（{why}；想要画面请加 --gif 录制 GIF）")
    print()

    # 行为树 tick 始终打印；窗口/GIF 只在对应模式下走渲染器。
    viz = Visualizer(render=False, print_tree=True, fps=fps)

    out_dir = "app/output/projects"
    gif_name = Path(gif_path).name if gif_path else "replay.gif"
    if gif_path:
        out_dir = str(Path(gif_path).resolve().parent)

    renderer = None
    if record_gif:
        renderer = make_renderer(
            "pygame", theme=theme, mode="save_gif",
            fps=fps, out_dir=out_dir, gif_name=gif_name,
        )
    elif want_window:
        renderer = make_renderer("pygame", theme=theme, fps=fps, live=True)

    def on_step(record, env):
        viz.on_step(record, env)            # 终端打印行为树 tick
        if renderer is not None:
            renderer.render(env)            # + 画一帧（窗口实时 / GIF 攒帧）
            if getattr(renderer, "_closed_by_user", False):
                raise KeyboardInterrupt     # 用户关窗 → 提前结束

    success = False
    try:
        for i in range(attempts):
            seed = 40 + i
            print(f"--- 尝试 {i + 1}/{attempts} (seed={seed}) ---")
            scenario = build_scenario()
            env = scenario.build_env(render=False)   # env 始终 headless，画面交给渲染器
            plan = plan_behavior_trees(
                env, scenario, optimal=True, use_composite_actions=True,
            )
            random.seed(seed)
            result = execute(
                env, plan, share_belief=True, max_steps=max_steps,
                on_step=on_step, print_ticks=False,
            )
            if result.success:
                print(f"\n✅ {success_msg}（用 {result.steps} 步）。")
                success = True
                if want_window and renderer is not None:
                    renderer.hold_open()      # 停在最后一帧，等用户关窗
                break
            print(f"   没成（{result.steps} 步），重试……\n")
        else:
            print("\n⚠️ 多次没成——重新运行一次脚本即可（执行有随机性）。")
    except KeyboardInterrupt:
        print("\n（窗口被关闭，提前退出。）")
    finally:
        if renderer is not None:
            gif = renderer.close()            # GIF 模式返回路径，其余返回 None
            if gif:
                print(f"\n🎬 回放已存成 GIF：{gif}")

    return success
