"""``core.envs.domains.virtualhome`` —— VirtualHome 家庭服务**符号域**。

一个自包含的注册域（``DOMAIN_REGISTRY["virtualhome"]``）：

* :mod:`~.model` —— 物体类别、13 个动作的 STRIPS 模型、互斥检测、初始状态；
* :mod:`~.nodes` —— 符号 Action / Condition 的 py_trees 节点基类；
* ``behavior_lib/`` —— 每个 grounded 动作名 / 谓词名对应的节点类，
  由 :class:`core.behavior_tree.behavior_library.BehaviorLibrary` 按文件名加载；
  ``FixAction/`` 与 ``FixCondition/`` 另放宏子树的接单 / 完成结构节点
  （``SelfAcceptTask`` / ``FinishTask`` / ``IsSelfTask``），使
  ``composite_library`` 的 0-cost 宏能在这个域里真实 tick。

它是**纯符号**域，不含 Unity / MiniGrid 渲染；配套运行时是
:mod:`backends.virtualhome`。文档里 ``core/envs/README.md`` 提到的
``core/envs/virtualhome/envs/vh_computation_env.py`` 属于上游 ``mrbtp`` 包，
在这个精简仓库里从未落地，本模块就是它的替代接入点。
"""
from __future__ import annotations

from .model import (CAN_OPEN, CATEGORIES, CONTAINERS, DEFAULT_TASK,
                    EXPANDABLE_ACTIONS, GRABBABLE, HAS_SWITCH, SURFACES,
                    VH_DURATION, VHAction, build_action_lists,
                    filter_objects_to_get_category, goal_state,
                    make_conflict_fn, normalize_action_space, start_state)

__all__ = [
    "SURFACES", "GRABBABLE", "CAN_OPEN", "CONTAINERS", "HAS_SWITCH",
    "CATEGORIES", "VH_DURATION", "EXPANDABLE_ACTIONS", "DEFAULT_TASK",
    "VHAction", "build_action_lists", "filter_objects_to_get_category",
    "make_conflict_fn", "normalize_action_space", "start_state", "goal_state",
]
