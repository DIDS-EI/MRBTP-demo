"""VirtualHome 符号域的 py_trees 节点基类。

``behavior_lib/Action/*.py`` 与 ``behavior_lib/Condition/*.py`` 里的每个具体
节点都只是这里两个基类的一行子类：文件名 = 节点类名（``BehaviorLibrary``
的加载契约），``get_ins_name()`` 会把它拼回 ``Cls(args)``，正好等于
``model.VHAction.name``，于是 ``bind_agent()`` 能直接从
``env.action_models`` 取回该 grounded 动作的 STRIPS 前后件。

执行语义与 ``repro/legacy_runtime/nodes.py`` 一致，但把老版本的
``act_max_step`` 计时压成「一拍完成」：主 app 的符号后端模拟的是*状态转移*，
不复现 VirtualHome 的 Unity 动画时长（``VH_DURATION`` 仍保留在模型里）。
"""
from __future__ import annotations

from py_trees.common import Status

from core.behavior_tree.base_nodes import Action, Condition


class SymbolicAction(Action):
    """原子动作：检查 pre → 原子地应用 STRIPS 转移 → RUNNING。

    返回 RUNNING 而非 SUCCESS 是刻意的：BT 的 ``Fallback`` 首个条件节点
    在下一拍读到新状态后就会 SUCCESS，整棵树随即完成；动作节点本身永远
    不会被再次 tick（与老版本 ``WareHouseAction`` 的语义一致）。
    """

    # 后端自己实现 create_action_model()，不走 Env.create_action_model 的
    # 「遍历行为库 + get_planning_action_list」路径。
    can_be_expanded = False

    def __init__(self, *args):
        super().__init__(*args)
        self.pre = frozenset()
        self.add = frozenset()
        self.del_set = frozenset()
        self.duration = 1

    @classmethod
    def get_planning_action_list(cls, agent, env):
        """占位：符号域的动作模型由 ``model.build_action_lists`` 统一生成。"""
        return []

    def bind_agent(self, agent):
        super().bind_agent(agent)
        models = getattr(self.env, "action_models", None) or {}
        model = models.get(self.name)
        if model is None:
            raise KeyError(
                f"VirtualHome 动作 '{self.name}' 没有 STRIPS 模型；"
                f"请通过 backends/virtualhome 后端构造世界。"
            )
        self.pre = frozenset(model.pre)
        self.add = frozenset(model.add)
        self.del_set = frozenset(model.del_set)
        self.duration = getattr(model, "duration", 1)

    def update(self) -> Status:
        # 意图共享：pre 中「别人打算达成但还没真实达成」的字面量 → 等待。
        predicted = self.agent.predict_condition.get("success", set())
        wait = self.pre & predicted
        if wait and not (self.env.state >= wait):
            return Status.RUNNING

        if not (self.env.state >= self.pre):
            return Status.FAILURE

        self.agent.action = self
        self.env.state = (self.env.state | self.add) - self.del_set
        return Status.RUNNING


class SymbolicCondition(Condition):
    """条件节点：belief success / failure 优先，否则查真实符号状态。"""

    def update(self) -> Status:
        is_in_predict, is_true = self.check_if_in_predict_condition()
        if is_in_predict:
            if is_true or (self.name in self.env.state):
                return Status.SUCCESS
            return Status.FAILURE
        return Status.SUCCESS if self.name in self.env.state else Status.FAILURE


# --------------------------------------------------------------------------- #
# Composite-action (LLM-style macro sub-tree) 的接单 / 完成节点。
#
# ``CompositeActionPlanner`` 把宏折叠成 cost=0 的动作后，
# ``PlanningAgent.create_anytree`` 会在 BTML 里插入 IsSelfTask /
# SelfAcceptTask / FinishTask 三个结构节点（见 planning_agent.py:321-365）。
# 它们不参与 STRIPS 状态转移，只负责「谁认领了这段子树」，所以单独放在
# ``behavior_lib/Fix*`` 下，与 13 个动作 / 13 个谓词节点分开。
# --------------------------------------------------------------------------- #
class TaskFlagCondition(Condition):
    """``IsSelfTask`` —— 本机器人是否已接下这个宏任务。"""

    can_be_expanded = False

    def __init__(self, task_id, action_name, sub_goal, sub_del):
        super().__init__(sub_goal)
        self.task_id = task_id
        self.task_action_name = action_name
        self.sub_goal = sub_goal
        self.sub_del = sub_del

    def update(self) -> Status:
        last = self.agent.last_accept_task
        if last is not None and self.task_id == last["task_id"]:
            self.agent.current_task = {
                "task_id": self.task_id,
                "sub_goal": self.sub_goal,
                "sub_del": self.sub_del,
            }
            return Status.SUCCESS
        return Status.FAILURE


class SelfAcceptAction(Action):
    """``SelfAcceptTask`` —— 接下宏任务，写进 agent 的 current_task。"""

    can_be_expanded = False

    def __init__(self, task_id, action_name, sub_goal, sub_del):
        super().__init__(sub_goal)
        self.task_id = task_id
        self.task_action_name = action_name
        self.sub_goal = sub_goal
        self.sub_del = sub_del

    def update(self) -> Status:
        self.agent.current_task = {
            "task_id": self.task_id,
            "sub_goal": self.sub_goal,
            "sub_del": self.sub_del,
        }
        return Status.RUNNING


class FinishTaskAction(Action):
    """``FinishTask`` —— 宏子树完成，撤销意图并让 selector 重新判定。"""

    can_be_expanded = False

    def update(self) -> Status:
        self.agent.finish_current_task()
        return Status.FAILURE
