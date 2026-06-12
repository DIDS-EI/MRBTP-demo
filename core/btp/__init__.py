"""core.btp — Behavior-Tree Planning algorithms.

This sub-package collects the multi-robot behavior-tree planners used in
the MRBTP paper
(*MRBTP: Efficient Multi-Robot Behavior Tree Planning and Collaboration*,
AAAI Oral, https://arxiv.org/abs/2502.18072).

================================  ===========  ====================================
Module                            Public class Description
================================  ===========  ====================================
``core.btp.base``               PlanningAgent FIFO back-chaining primitives
                                  / PlanningCondition
``core.btp.multi_robot_basic``  MABTP        Multi-Robot BTP — FIFO baseline
``core.btp.multi_robot_optimal``MAOBTP       Multi-Robot Optimal BTP — cost
                                               heap, supports composite actions
``core.btp.composite_action``   CABTP        Composite-Action BTP — single-agent
                                               sub-tree macro builder
``core.btp.multi_robot``        MRBTP        Top-level paper facade wiring
                                               MABTP / MAOBTP into runnable BTs
================================  ===========  ====================================

For convenience, every public class is also re-exported here::

    from core.btp import MRBTP, MABTP, MAOBTP, CABTP
    from core.btp import PlanningAgent, PlanningCondition

Backward compatibility
----------------------
The top-level facade was historically called ``DMR`` (Decentralized
Multi-Robot). The class-level alias ``DMR = MRBTP`` is preserved at the
package root, so ``DMR is MRBTP`` evaluates to ``True``::

    from core.btp import DMR     # alias of MRBTP, still works
"""

from core.btp.base import PlanningAgent, PlanningCondition
from core.btp.composite_action import CABTP
from core.btp.multi_robot_basic import MABTP
from core.btp.multi_robot_optimal import (
    MAOBTP,
    BfsPlanningAgent,
    CostAwarePlanningAgent,
)
from core.btp.multi_robot import MRBTP, DMR  # ``DMR`` is alias of MRBTP

__all__ = [
    "PlanningAgent",
    "PlanningCondition",
    "CABTP",
    "MABTP",
    "MAOBTP",
    "MRBTP",
    "DMR",  # legacy alias for MRBTP, kept for backward compatibility
    "CostAwarePlanningAgent",
    "BfsPlanningAgent",  # legacy alias for CostAwarePlanningAgent
]
