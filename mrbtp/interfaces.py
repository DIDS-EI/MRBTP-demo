"""可插拔仿真后端 —— 两个核心协议（契约定义处）。

设计文档：docs/PLUGGABLE_BACKEND_DESIGN.html  §3 核心架构 / §4 接口契约

这里只定义「形状」，不含任何实现。后端（backends/<name>/）实现 SimBackend，
渲染器实现 Renderer，两者正交组合。规划器 / executor 只依赖这两个协议，
看不到具体后端是 MiniGrid 还是 Pygame。

Python 3.9 兼容：用 typing.Protocol（runtime_checkable 便于 isinstance 自检）。
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Protocol, Tuple, runtime_checkable


# ───────────────────────── 缝① 仿真后端 ──────────────────────────
@runtime_checkable
class SimBackend(Protocol):
    """一个「世界」该长什么样 —— 规划器 / executor 依赖的最小接口。

    现有 MiniGrid env 已经隐式满足其中大部分；P0 的工作是把它显式对齐到
    这个协议（见 backends/minigrid/）。新后端（Pygame…）照此实现即可。
    """

    # --- A 组：世界与智能体 ---
    agents: List[Any]                      # 每个 agent 暴露 B 组接口

    def reset(self, *, seed: Optional[int] = None) -> Any:
        """重置世界到初始状态，返回观测（具体类型由后端定义）。"""
        ...

    def get_initial_state(self) -> set:
        """返回初始谓词集合（如 {IsInRoom(ball,room-0), ...}）供规划器用。"""
        ...

    def create_action_model(self) -> Any:
        """构造该后端的动作模型（可用动作 / 前后条件），供规划器展开。"""
        ...

    # --- C 组：空间查询（谓词求值依赖）---
    def get_room_index(self, pos: Tuple[int, int]) -> int:
        """给定坐标，返回它所属的房间编号（IsInRoom 等谓词依赖）。"""
        ...

    @property
    def width(self) -> int: ...
    @property
    def height(self) -> int: ...


@runtime_checkable
class SimAgent(Protocol):
    """单个智能体的最小接口（SimBackend.agents 里的元素）。"""

    id: int

    @property
    def position(self) -> Tuple[int, int]: ...
    @property
    def front_pos(self) -> Tuple[int, int]: ...

    def step(self, action: Any) -> None:
        """执行一个离散原语动作（left/right/forward/pickup/drop/toggle/done）。"""
        ...


# ───────────────────────── 缝② 渲染器 ──────────────────────────
@runtime_checkable
class Renderer(Protocol):
    """怎么把一个世界「画出来」—— 与后端正交，可单独替换。

    渲染唯一入口经 executor 的 on_step 回调外置（executor 自身从不调渲染），
    所以换渲染 = 换 on_step 里调的对象，不动规划与执行逻辑。
    """

    def render(self, backend: SimBackend) -> Any:
        """把当前世界状态渲染出来（窗口 / 存帧 / headless 由 mode 决定）。"""
        ...

    def close(self) -> None:
        """收尾（关闭窗口、合成 GIF、释放资源等）。"""
        ...


# ───────────────────────── 工厂（占位，P1 实现）──────────────────────────
def make_backend(name: str, *, scene: Any) -> "SimBackend":   # noqa: D401
    """按名字造后端（'minigrid' / 'pygame' / ...）。P1 填实现。"""
    raise NotImplementedError(
        "make_backend 将在 P1 实现；P0 只定义协议契约。"
    )


def make_renderer(name: str, *, theme: str = "default",
                  mode: str = "save_gif") -> "Renderer":      # noqa: D401
    """按名字造渲染器，正交组合（远程默认 save_gif）。P2 填实现。"""
    raise NotImplementedError(
        "make_renderer 将在 P2 实现；P0 只定义协议契约。"
    )
