"""Part 1 — Plan one behavior tree per agent from a shared goal.

This is the *planning* half of MRBTP.  Given a :class:`Scenario` and a
built environment, :func:`plan_behavior_trees` performs three steps:

    1. Build the per-agent **action model** (every grounded primitive
       action each agent could execute, derived from the behavior library).
    2. Optionally pre-plan **composite-action macros** (LLM-style reusable
       sub-trees such as *GetKeyAndOpenDoor*) and append them to the action
       model so the search can treat a whole macro as a single 0-cost step.
    3. Run a multi-robot back-chaining search (``MAOBTP`` or ``MABTP``) to
       back-chain the goal into one runnable ``BehaviorTree`` per agent.

The result is returned as a tidy :class:`PlanResult` dataclass instead of
the loose tuples the original script juggled.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from core.behavior_tree.behavior_tree import BehaviorTree
from core.btp.multi_robot_basic import MABTP
from core.btp.multi_robot_optimal import MAOBTP
from core.utils.composite_action_tools import CompositeActionPlanner
from core.utils.tools import print_colored

from mrbtp_demo.scenario import Scenario


@dataclass
class PlanResult:
    """Everything Part 2 needs to actually run the plan."""

    bt_list: List[BehaviorTree]          # one runnable BehaviorTree per agent
    btml_list: List                      # the underlying BTML descriptions
    behavior_libs: List                  # per-agent BehaviorLibrary
    start_state: frozenset               # the grounded initial state
    planning_time: float                 # wall-clock seconds spent searching
    expanded_num: int                    # search nodes expanded (a cost proxy)


def plan_behavior_trees(
    env,
    scenario: Scenario,
    *,
    optimal: bool = True,
    use_composite_actions: bool = True,
    save_dir: Optional[str] = None,
    verbose: bool = False,
) -> PlanResult:
    """Plan a behavior tree for every agent.

    Args:
        env: a built :class:`MiniGridToMAGridEnv` (see ``Scenario.build_env``).
        scenario: the problem definition (goal + composite library).
        optimal: ``True`` uses the cost-aware optimal planner ``MAOBTP``;
            ``False`` uses the simpler FIFO baseline ``MABTP``.
        use_composite_actions: whether to pre-plan the macro sub-trees from
            ``scenario.composite_library``.  ``MABTP`` does not support
            composite actions, so this is forced off when ``optimal=False``.
        save_dir: if given, write ``robot-i.bt`` and ``robot-i.svg`` (plus
            macro diagrams) into this directory for inspection.
        verbose: forwarded to the underlying planner.

    Returns:
        A populated :class:`PlanResult`.
    """
    num_agent = env.num_agent

    # ----- Step 1: per-agent primitive action model ---------------------- #
    action_lists = env.create_action_model()
    start_state = env.get_initial_state()
    if verbose:
        print_colored(f"Initial state literals: {len(start_state)}", "blue")

    # ----- Step 2: composite-action macros (optional) -------------------- #
    composite_btml_list = None
    if use_composite_actions and optimal and scenario.composite_library:
        cap = CompositeActionPlanner(action_lists, scenario.composite_library)
        cap.get_composite_action()
        composite_btml_list = cap.btml_ls

        # Append each agent's macro PlanningActions to its action model so the
        # back-chaining search can pick a macro as one 0-cost step.
        for i in range(num_agent):
            macros = [act for act in cap.planning_ls[i] if act]
            action_lists[i].extend(macros)
    elif use_composite_actions and not optimal:
        print_colored(
            "MABTP (optimal=False) does not support composite actions; "
            "running with primitive actions only.",
            "yellow",
        )

    # ----- Step 3: multi-robot back-chaining search ---------------------- #
    print_colored("Start Multi-Robot Behavior Tree Planning...", "green")
    t0 = time.time()

    if optimal:
        planner = MAOBTP(verbose=verbose, start=start_state, env=env)
        planner.bfs_planning(scenario.goal, action_lists=action_lists)
    else:
        planner = MABTP(verbose=verbose, start=start_state, env=env)
        planner.planning(scenario.goal, action_lists=action_lists)

    planning_time = time.time() - t0
    print_colored(f"Finish planning in {planning_time:.3f}s", "green")

    behavior_libs = [agent.behavior_lib for agent in env.agents]
    btml_list = planner.get_btml_list()

    # Merge macro sub-trees back into each agent's BTML so the runtime can
    # expand them when ticking.
    if composite_btml_list is not None:
        for i in range(num_agent):
            btml_list[i].sub_btml_dict = composite_btml_list[i].sub_btml_dict

    # ----- Build runnable BehaviorTrees ---------------------------------- #
    bt_list: List[BehaviorTree] = []
    for i in range(num_agent):
        bt = BehaviorTree(btml=btml_list[i], behavior_lib=behavior_libs[i])
        bt_list.append(bt)

    if save_dir is not None:
        _save_artifacts(bt_list, btml_list, behavior_libs, save_dir)

    return PlanResult(
        bt_list=bt_list,
        btml_list=btml_list,
        behavior_libs=behavior_libs,
        start_state=start_state,
        planning_time=planning_time,
        expanded_num=getattr(planner, "record_expanded_num", 0),
    )


def _save_artifacts(bt_list, btml_list, behavior_libs, save_dir: str) -> None:
    """Write ``robot-i.bt`` / ``robot-i.svg`` and macro diagrams to disk."""
    out = Path(save_dir)
    out.mkdir(parents=True, exist_ok=True)

    for i, bt in enumerate(bt_list):
        bt.save_btml(str(out / f"robot-{i}.bt"))
        bt.draw(file_name=f"robot-{i}", target_directory=str(out))

        # Also render every macro sub-tree this agent owns.
        for name, sub_btml in btml_list[i].sub_btml_dict.items():
            if sub_btml:
                macro_bt = BehaviorTree(btml=sub_btml, behavior_lib=behavior_libs[i])
                macro_bt.draw(file_name=f"{i}-{name}", target_directory=str(out))

    print_colored(f"Saved behavior-tree artifacts to {out}", "blue")
