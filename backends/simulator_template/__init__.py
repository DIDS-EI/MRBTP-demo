"""backends/simulator_template —— 机器人仿真器后端「实现模板」。

这是一个**可运行的骨架**（不依赖任何真实仿真器），用来证明
:class:`core.interfaces.SimBackend` 协议是自洽、可被规划器 / executor 直接
消费的。接入真实仿真器（PyBullet / Isaac Sim / Genesis / MuJoCo …）时，把每个
``# TODO(simulator)`` 处替换成对应的仿真器 API 调用即可，**规划内核与执行器
一行都不用改**。

完整接入规范见 docs/SIMULATOR_BACKEND_GUIDE.html。

核心约定（与 MiniGrid 后端逐字对齐）：

    * ``agents``                : 列表，每个元素暴露 SimAgent 接口（id/position/step）。
    * ``reset(seed=...)``        : 复位世界，返回观测。
    * ``get_initial_state()``    : 返回初始**谓词集合**（规划器的 start）。
    * ``create_action_model()``  : 返回每个 agent 的 PlanningAction 列表。
    * ``get_room_index(pos)``    : 坐标 → 房间号（空间谓词求值依赖）。
    * ``width`` / ``height``     : 世界尺寸。
    * 行为库节点的 ``update()`` 在 ``simulation_mode == simulator`` 时走
      ``simulator_update()``（见 core/behavior_tree/base_nodes/Action.py），
      真实仿真器在那里下发关节 / 末端执行器指令并回读传感器。

注意：本模板默认 **未注册**。要启用它，显式调用 ``register_simulator_template()``
（或在你的真实后端模块里 ``register_backend('your_sim', factory)``）。这样既能
当文档读，又不会污染默认后端列表。
"""
from __future__ import annotations

from typing import Any, List, Optional, Tuple

from core.interfaces import register_backend


class _TemplateAgent:
    """SimAgent 协议的最小实现（占位）。

    真实后端里，``position`` 应回读仿真器中机器人 base / end-effector 的位姿，
    ``step`` 应把离散原语动作翻译成仿真器的连续控制指令并 step 仿真器一拍。
    """

    def __init__(self, agent_id: int):
        self.id = agent_id
        self._position: Tuple[int, int] = (0, 0)
        self.direction: int = 0
        self.carrying: Any = None

    @property
    def position(self) -> Tuple[int, int]:
        # TODO(simulator): return self._sim.get_robot_base_xy(self.id)
        return self._position

    @property
    def front_pos(self) -> Tuple[int, int]:
        # TODO(simulator): 由 base 位姿 + 朝向推算正前方栅格 / 目标点。
        return self._position

    def step(self, action: Any) -> None:
        # TODO(simulator): 把 action（left/right/forward/pickup/drop/toggle/done）
        # 翻译成导航 / 抓取 motion，调用仿真器执行并 step 一拍。
        raise NotImplementedError(
            "simulator_template 是接口模板：请在真实后端里实现 agent.step()。"
        )


class SimulatorTemplateBackend:
    """SimBackend 协议的「实现模板」（可被 isinstance(b, SimBackend) 通过）。

    所有方法都给出**真实仿真器该做什么**的 TODO 注释；当前实现仅保证：
    (a) 形状满足协议；(b) 构造不抛错，便于在 CI 里做协议自检。
    """

    def __init__(self, scene: Any, *, render: bool = False, **kwargs):
        self.scene = scene
        self.render = render
        self.num_agent = getattr(scene, "num_agent", 1)
        self.agents: List[_TemplateAgent] = [
            _TemplateAgent(i) for i in range(self.num_agent)
        ]
        # TODO(simulator): 在此连接 / 启动仿真器，加载场景 USD/URDF，放置物体。
        self._width = 0
        self._height = 0

    # --- A 组：世界生命周期 ---
    def reset(self, *, seed: Optional[int] = None) -> Any:
        # TODO(simulator): 复位仿真器到初始关节角 / 物体位姿，返回首帧观测。
        raise NotImplementedError(
            "simulator_template.reset：接入真实仿真器后实现世界复位。"
        )

    # --- B 组：规划接口 ---
    def get_initial_state(self) -> set:
        # TODO(simulator): 从仿真器真值 / 感知模块读出初始谓词集合，例如
        # {f"IsInRoom({obj},room-{k})", ...}；可复用 MiniGrid 后端那套
        # 「枚举动作模型的 pre/add/del 再逐一求值」的方法。
        raise NotImplementedError(
            "simulator_template.get_initial_state：从仿真器真值构造初始谓词集。"
        )

    def create_action_model(self) -> Any:
        # TODO(simulator): 为每个 agent 收集行为库里各 Action 的
        # get_planning_action_list(agent, self)，与 MiniGrid 后端完全一致。
        raise NotImplementedError(
            "simulator_template.create_action_model：枚举行为库动作模型。"
        )

    # --- C 组：空间查询 ---
    def get_room_index(self, pos: Tuple[int, int]) -> int:
        # TODO(simulator): 把连续坐标映射到房间号（用场景的房间包围盒 / 语义地图）。
        return -1

    @property
    def width(self) -> int:
        return self._width

    @property
    def height(self) -> int:
        return self._height


def make_simulator_template_backend(scene: Any, *, render: bool = False, **kwargs):
    """工厂函数：造一个模板后端实例（供 register_backend 挂接）。"""
    return SimulatorTemplateBackend(scene, render=render, **kwargs)


def register_simulator_template(name: str = "simulator_template") -> None:
    """把本模板后端登记进全局注册表（默认不自动注册，需显式调用）。

    真实接入时，复制本文件改名为你的仿真器名，把 TODO 填实，然后在你的后端模块
    顶层调用 ``register_backend('your_sim', make_your_sim_backend)`` 即可被
    ``--backend your_sim`` / ``Scenario.backend='your_sim'`` 选中。
    """
    register_backend(name, make_simulator_template_backend)
