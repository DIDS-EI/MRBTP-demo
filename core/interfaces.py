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


# ───────────────────────── 工厂（已落地）──────────────────────────
# 后端注册表：名字 -> 一个「用 scene 造出 SimBackend」的构造函数。
# 内置 'minigrid' 走现有 env；接入真实仿真器时，在自己的后端模块里调用
# ``register_backend('pybullet', factory)`` 即可挂接，无需改动这里或规划/执行层。
# 这正是「后端可插拔」的落点：规划器 / executor 只认 SimBackend 协议。
_BACKEND_REGISTRY: Dict[str, Callable[..., "SimBackend"]] = {}


def register_backend(name: str, factory: Callable[..., "SimBackend"]) -> None:
    """注册一个后端构造函数。

    Args:
        name:    后端名（大小写不敏感），如 ``'minigrid'`` / ``'pybullet'``。
        factory: 形如 ``factory(scene, *, render=False, **kwargs) -> SimBackend``
                 的可调用对象；``scene`` 是一个 :class:`~app.scenario.Scenario`。

    重复注册同名后端会覆盖旧的（方便热替换 / 测试桩）。
    """
    _BACKEND_REGISTRY[(name or "").strip().lower()] = factory


def available_backends() -> List[str]:
    """返回当前已注册的后端名（已排序），供 CLI / 文档 / 自检使用。"""
    return sorted(_BACKEND_REGISTRY)


def _register_builtin_minigrid_backend() -> None:
    """把内置 MiniGrid 后端登记进注册表（惰性，避免顶层强依赖 env 链）。"""
    if "minigrid" in _BACKEND_REGISTRY:
        return

    def _minigrid_factory(scene: Any, *, render: bool = False, **kwargs) -> "SimBackend":
        # 现有 ``Scenario.build_env`` 已经构造并 reset 了一个满足 SimBackend
        # 形状的 MiniGridToMAGridEnv（agents / reset / get_initial_state /
        # create_action_model / get_room_index / width / height 一应俱全）。
        # 工厂在此只是把「按名字造后端」这层抽象补齐。
        return scene.build_env(render=render)

    _BACKEND_REGISTRY["minigrid"] = _minigrid_factory


def make_backend(name: str, *, scene: Any, render: bool = False, **kwargs) -> "SimBackend":
    """按名字构造一个仿真后端。

    Args:
        name:   后端名（大小写不敏感）。内置 ``'minigrid'``；其余由
                :func:`register_backend` 在各自后端模块里挂接。
        scene:  一个 :class:`~app.scenario.Scenario`，描述世界 / 物体 /
                目标 / 行为库选择，透传给后端构造函数。
        render: 是否让后端保留可渲染状态（窗口 / 抓帧）。
        **kwargs: 透传给具体后端构造函数。

    Returns:
        一个满足 :class:`SimBackend` 协议的实例。

    Raises:
        ValueError: 未知后端名（错误信息里列出已注册项，便于排查）。
    """
    _register_builtin_minigrid_backend()
    key = (name or "").strip().lower()
    factory = _BACKEND_REGISTRY.get(key)
    if factory is None:
        raise ValueError(
            f"未知后端 '{name}'。当前已注册：{available_backends()}。"
            f"接入新仿真器请在后端模块里调用 register_backend(name, factory)，"
            f"参见 docs/PLUGGABLE_BACKEND_DESIGN.html。"
        )
    return factory(scene, render=render, **kwargs)


def make_renderer(name: str, *, theme: str = "home",
                  mode: str = "save_gif", **kwargs) -> "Renderer":   # noqa: D401
    """按名字造渲染器，与后端正交组合（远程默认 save_gif）。

    Args:
        name:  渲染器后端名。当前支持 'pygame'（路线 A 薄后端）。
        theme: 主题名（'home' / 'battle' / 'default'）或 Theme 实例，透传给渲染器。
        mode:  'save_gif'（默认，攒帧→GIF，远程无显示器友好）/ 'save_frames' /
               'both'。
        **kwargs: 其余参数透传给具体渲染器构造（out_dir / tile / fps / gif_name）。

    Returns:
        一个满足 Renderer 协议的实例。

    Raises:
        ValueError: 未知渲染器名。
    """
    key = (name or "").strip().lower()
    if key == "pygame":
        # 延迟导入：避免在不渲染时也强依赖 pygame / PIL。
        from backends.pygame import PygameGridRenderer
        return PygameGridRenderer(theme, mode=mode, **kwargs)
    raise ValueError(
        f"未知渲染器 '{name}'。当前支持：'pygame'。"
    )
