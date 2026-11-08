"""``virtualhome`` —— 纯符号 VirtualHome 仿真后端（SimBackend 实现）。

把 ``core/envs/domains/virtualhome`` 的 STRIPS 域接进主 app 的
``plan → execute → visualize`` 链路：世界是一个谓词集合，动作是原子 STRIPS
转移，不连 Unity、不开窗口、不依赖 MiniGrid。

用法::

    python -m app.run --scenario virtualhome --renderer none
    python -m app.run --backend virtualhome --domain virtualhome \\
        --scenario virtualhome --renderer none --agents 2

装配关系
--------
* ``Scenario.backend = "virtualhome"`` / ``--backend virtualhome`` →
  :func:`core.interfaces.make_backend` 调本模块的工厂；
* ``Scenario.behavior_lib = "virtualhome"`` / ``--domain virtualhome`` →
  :func:`core.envs.domains.resolve_behavior_lib_path` 给出本域自带的
  ``behavior_lib``（standalone，不叠加 MiniGrid 原语）；
* ``Scenario.symbolic_task`` 携带任务 JSON（objects / action_space /
  init_state / goal），与论文复现的 ``vh_*_25.json`` 同格式。

``SimBackend`` 协议之外的执行钩子
---------------------------------
``app.executor`` 的老路径是为 MiniGrid 的
``set_focus_agent/agent_step/get_focus_agent`` 三件套写的。符号后端没有位姿，
因此提供 :meth:`VirtualHomeBackend.tick_step`；executor 检测到该方法就走它，
MiniGrid 后端仍走原路径，行为不变。

``composite_library`` 的 0-cost 宏也受支持：域在 ``behavior_lib/Fix*`` 下提供
``IsSelfTask`` / ``SelfAcceptTask`` / ``FinishTask``，智能体沿用 MiniGrid 的
「接单后补一次 tick」语义，宏子树因此能被认领并展开执行。
"""
from __future__ import annotations

import copy
from typing import Any, Dict, List, Optional, Tuple

from py_trees.common import Status

from core.behavior_tree.behavior_library import BehaviorLibrary
from core.envs.domains import resolve_behavior_lib_path
from core.envs.domains.virtualhome.model import (build_action_lists,
                                                 make_conflict_fn,
                                                 normalize_action_space,
                                                 start_state)
from core.interfaces import register_backend


class SymbolicAgent:
    """一个机器人在符号世界里的运行时句柄。

    满足 :class:`core.interfaces.SimAgent` 的形状（id / position /
    front_pos / step），同时提供 executor 与行为树节点用到的 belief 字段。
    """

    def __init__(self, env: "VirtualHomeBackend", agent_id: int):
        self.env = env
        self.id = agent_id
        self.behavior_lib: Any = None

        self.bt = None
        self.action = None
        self.bt_success = False

        # 协议形状：符号世界没有坐标，给恒定的哑值。
        self.position: Tuple[int, int] = (0, 0)
        self.front_pos: Tuple[int, int] = (0, 0)
        self.direction = 0
        self.carrying = None

        # belief space（--no-share-belief 时由 executor 清空 / 替换方法）
        self.predict_condition: Dict[str, set] = {"success": set(), "fail": set()}
        self.current_task = None
        self.last_accept_task = None

    @property
    def agent_id(self) -> str:
        return f"agent-{self.id}"

    def bind_bt(self, bt) -> None:
        self.bt = bt
        bt.bind_agent(self)

    def step(self, action: Any = None):
        """Tick 自己的行为树一拍，返回本拍选中的动作节点（可打印名字）。

        Composite-action 宏分支里，``SelfAcceptTask`` 在这一拍写下
        ``current_task``，要等下一拍 ``IsSelfTask`` 才放行宏子树；因此沿用
        MiniGrid ``Agent.step`` 的「同一拍补一次 tick」语义。无宏时
        ``current_task`` 恒为 None，行为与单 tick 完全一致。
        """
        if self.bt is None:
            self.bt_success = False
            return None
        self.action = None
        self.current_task = None
        self.bt.tick(verbose=True, bt_name=f"{self.agent_id} bt")

        if self.current_task != self.last_accept_task:
            self.finish_current_task()
            self.update_current_task()
            if self.current_task is not None:
                self.bt.tick(verbose=True, bt_name=f"{self.agent_id} bt (task)")

        self.bt_success = self.bt.root.status == Status.SUCCESS
        return self.action

    def finish_current_task(self):
        """宏任务完成：符号后端不做信念广播，保留接口占位。"""
        return None

    def update_current_task(self):
        # 只维护「我认领了哪段宏」，不做 MiniGrid 那套共享信念队列广播。
        self.last_accept_task = copy.deepcopy(self.current_task)

    def reset(self) -> None:
        self.action = None
        self.bt_success = False
        self.predict_condition = {"success": set(), "fail": set()}
        self.current_task = None
        self.last_accept_task = None


class VirtualHomeBackend:
    """满足 :class:`core.interfaces.SimBackend` 的纯符号世界。"""

    def __init__(self, scene: Any, *, render: bool = False, **kwargs):
        self.scene = scene
        self.render = render  # 符号后端没有画面，保留参数只为满足工厂签名

        task = getattr(scene, "symbolic_task", None)
        if task is None:
            raise ValueError(
                "virtualhome 后端需要一个符号任务：请使用 "
                "'--scenario virtualhome'（场景自带 symbolic_task），或给 "
                "Scenario 传入 symbolic_task={'objects', 'action_space', "
                "'init_state', 'goal'}。"
            )
        for key in ("objects", "action_space", "init_state", "goal"):
            if key not in task:
                raise ValueError(f"symbolic_task 缺少字段 '{key}'。")

        self.task = task
        self.num_agent = int(getattr(scene, "num_agent", None)
                             or len(task["action_space"]))
        space = normalize_action_space(task["action_space"], self.num_agent)

        self.objects = list(task["objects"])
        self.action_space = space
        self._start = start_state({**task, "action_space": space}, self.num_agent)
        self.goal = frozenset(getattr(scene, "goal", None) or task["goal"])
        self.state = set(self._start)

        # ---- 行为库（standalone 域，单路径） -------------------------- #
        lib_path = resolve_behavior_lib_path("virtualhome")
        self.behavior_lib = BehaviorLibrary(lib_path)

        # ---- 规划接口 ------------------------------------------------- #
        self.action_lists: List[List[Any]] = build_action_lists(self.objects, space)
        self.action_models: Dict[str, Any] = {
            act.name: act for acts in self.action_lists for act in acts
        }
        self.blackboard: Dict[str, Any] = {
            "predict_condition": {"success": set(), "fail": set()},
            "task_agents_queue": [],
            "action_pre": {name: frozenset(act.pre)
                           for name, act in self.action_models.items()},
        }
        self._conflict_fn = make_conflict_fn(self.num_agent)
        self.action_model = self.action_lists
        self._validate_behavior_lib()

        self.agents: List[SymbolicAgent] = [
            SymbolicAgent(self, i) for i in range(self.num_agent)
        ]
        for agent in self.agents:
            agent.behavior_lib = self.behavior_lib

        # ---- executor / BehaviorTree 需要的公共属性 ------------------- #
        self.step_count = 0
        self.print_ticks = False
        self.verbose = False
        self.render_mode = None
        self.simulation_mode = None
        self._width = 0
        self._height = 0

    # ------------------------------------------------------------------ #
    # SimBackend: 世界生命周期
    # ------------------------------------------------------------------ #
    def reset(self, *, seed: Optional[int] = None) -> frozenset:
        self.state = set(self._start)
        self.step_count = 0
        self.blackboard["predict_condition"] = {"success": set(), "fail": set()}
        self.blackboard["task_agents_queue"] = []
        for agent in self.agents:
            agent.reset()
            if agent.bt is not None:
                self._reset_tree(agent.bt.root)
        return frozenset(self.state)

    @staticmethod
    def _reset_tree(root) -> None:
        stack = [root]
        while stack:
            node = stack.pop()
            if hasattr(node, "status"):
                node.status = Status.INVALID
            stack.extend(getattr(node, "children", ()) or ())

    # ------------------------------------------------------------------ #
    # SimBackend: 规划接口
    # ------------------------------------------------------------------ #
    def get_initial_state(self) -> set:
        return set(self._start)

    def create_action_model(self) -> List[List[Any]]:
        # 返回外层 list 的浅拷贝，避免 planner 注入宏时改到后端自己的模型。
        return [list(acts) for acts in self.action_lists]

    def check_conflict(self, premise_condition) -> bool:
        """规划器每次回链都会调它（协议外但属真实调用契约）。"""
        return bool(self._conflict_fn(frozenset(premise_condition)))

    # ------------------------------------------------------------------ #
    # SimBackend: 空间查询（符号世界无几何，返回哑值）
    # ------------------------------------------------------------------ #
    def get_room_index(self, pos: Tuple[int, int]) -> int:
        return -1

    @property
    def width(self) -> int:
        return self._width

    @property
    def height(self) -> int:
        return self._height

    # ------------------------------------------------------------------ #
    # 执行钩子：让 executor 不必假装这里有 MiniGrid 的位姿三件套
    # ------------------------------------------------------------------ #
    def tick_step(self) -> bool:
        """推进一拍；返回所有行为树是否都 SUCCESS（= 任务完成）。"""
        self.step_count += 1
        done = True
        for agent in self.agents:
            agent.step()
            if not agent.bt_success:
                done = False
        return done

    # ------------------------------------------------------------------ #
    def _validate_behavior_lib(self) -> None:
        """确保 BTML 里可能出现的每个类名都在行为库里注册了。"""
        action_names = {act.name.split("(", 1)[0]
                        for acts in self.action_lists for act in acts}
        literals = set(self._start) | set(self.goal)
        for acts in self.action_lists:
            for act in acts:
                literals |= set(act.pre) | set(act.add) | set(act.del_set)
        condition_names = {lit.split("(", 1)[0] for lit in literals}

        missing_a = sorted(action_names - set(self.behavior_lib["Action"]))
        missing_c = sorted(condition_names - set(self.behavior_lib["Condition"]))
        if missing_a or missing_c:
            raise RuntimeError(
                "virtualhome 行为库不完整："
                f"缺少 Action={missing_a}、Condition={missing_c}；"
                f"库路径 = {resolve_behavior_lib_path('virtualhome')}"
            )


def make_virtualhome_backend(scene: Any, *, render: bool = False,
                             **kwargs) -> VirtualHomeBackend:
    """``register_backend`` 用的工厂：``factory(scene, *, render=False)``。"""
    return VirtualHomeBackend(scene, render=render, **kwargs)


# 导入本模块即完成注册（与 backends/mujoco 的做法一致）。
register_backend("virtualhome", make_virtualhome_backend)

__all__ = ["VirtualHomeBackend", "SymbolicAgent", "make_virtualhome_backend"]
