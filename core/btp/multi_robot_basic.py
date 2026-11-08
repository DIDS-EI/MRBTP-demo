"""
MABTP — Multi-Robot Behavior Tree Planning.

Drives a back-chaining search across multiple per-agent ``PlanningAgent``s
to produce one cooperating behavior tree per agent.

The search is a queue-based traversal of premise conditions; each popped
condition is expanded by every agent in turn. Termination conditions:
    - the queue is empty,
    - ``self.start`` (initial state) already satisfies the current
      condition (i.e. the plan is grounded), or
    - the wall-clock time exceeds ``max_time_limit`` seconds.
"""

from __future__ import annotations

import time
from typing import List, Optional

from core.btp.base.planning_agent import PlanningAgent
from core.btp.structure_sharing import (
    build_groups, condition_is_shareable, make_template, replay,
)
from core.utils.tools import print_colored


class MABTP:
    """Multi-Robot Behavior Tree Planner."""

    def __init__(
        self,
        verbose: bool = False,
        start=None,
        env=None,
        max_time_limit: float = 20.0,
        queue_dedup: bool = True,
        structure_sharing: bool = True,
    ):
        self.verbose = verbose
        self.start = start
        self.env = env
        self.max_time_limit = max_time_limit

        # Paper Alg.2 line 13 writes ``CU <- CU ∪ Cnew`` with a set union, so
        # CU cannot contain two equal conditions. The FIFO queue used here is
        # a list; ``queue_dedup`` restores the set semantics. Set it to False
        # to reproduce the legacy (pre-dedup) behaviour for A/B comparison.
        self.queue_dedup = queue_dedup

        # R1: robots with the same role-neutral capability set share one
        # expansion decision per condition; each still builds its own tree.
        self.structure_sharing = structure_sharing
        self.n_capability_groups: int = 0
        self.shared_expansion_hits: int = 0

        self.planned_agent_list: Optional[List[PlanningAgent]] = None
        self.record_expanded_num: int = 0
        self.expanded_time: float = 0.0

    # ------------------------------------------------------------------ #
    # Search
    # ------------------------------------------------------------------ #

    def planning(self, goal, action_lists) -> None:
        """Run the multi-robot back-chaining search to populate every agent's plan."""
        start_time = time.time()

        planning_agent_list = [
            PlanningAgent(action_list, goal, id=i, verbose=self.verbose, env=self.env)
            for i, action_list in enumerate(action_lists)
        ]

        goal = frozenset(goal)
        explored_condition_list = [goal]
        # Keep only the first enqueue of each distinct condition. Every agent
        # still expands the condition and still attaches its own branch to its
        # own tree; the dedup gate only prevents a second *queue entry*.
        pushed = {goal} if self.queue_dedup else None
        group_keys, rep_index, share_profitable = build_groups(
            action_lists, self.structure_sharing)
        self.n_capability_groups = len(set(group_keys))
        self.shared_expansion_hits = 0

        def collect(premise_condition_list):
            for pc in premise_condition_list:
                condition_set = frozenset(pc.condition_set)
                if pushed is not None:
                    if condition_set in pushed:
                        continue
                    pushed.add(condition_set)
                explored_condition_list.append(condition_set)

        while explored_condition_list:
            self.record_expanded_num += 1

            condition = explored_condition_list.pop(0)
            if self.verbose:
                print_colored(f"C:{condition}", "green")

            if not share_profitable:
                # Unchanged legacy path: every agent expands independently.
                for agent in planning_agent_list:
                    if self.verbose:
                        print_colored(f"Agent:{agent.id}", "purple")
                    collect(agent.one_step_expand(condition))
            else:
                # One template per capability group, recomputed per condition.
                # Conditions naming a specific robot are never shared: their
                # literals cannot be role-rebound without changing meaning.
                shareable = condition_is_shareable(condition)
                templates: Dict[Tuple, Tuple] = {}
                for i, agent in enumerate(planning_agent_list):
                    if self.verbose:
                        print_colored(f"Agent:{agent.id}", "purple")
                    key = group_keys[i]
                    rep = rep_index[i]
                    template = templates.get(key) if shareable else None
                    if template is None:
                        premise_condition_list = agent.one_step_expand(condition)
                        if shareable and rep == i:
                            templates[key] = make_template(
                                premise_condition_list, agent.id)
                    else:
                        try:
                            premise_condition_list = replay(agent, template,
                                                            condition)
                            self.shared_expansion_hits += 1
                        except LookupError:
                            premise_condition_list = agent.one_step_expand(
                                condition)
                    collect(premise_condition_list)

            if self.start is not None and self.start >= condition:
                break
            if time.time() - start_time > self.max_time_limit:
                self.expanded_time = time.time() - start_time
                break

        self.planned_agent_list = planning_agent_list

    # ------------------------------------------------------------------ #
    # Behavior-tree extraction (uses each agent's own conversion methods)
    # ------------------------------------------------------------------ #

    def _require_planned(self) -> List[PlanningAgent]:
        if self.planned_agent_list is None:
            raise RuntimeError(
                "planning() must be called before output_*() / get_btml_list()."
            )
        return self.planned_agent_list

    def output_bt_list(self, behavior_libs):
        """Return a list of ``BehaviorTree`` objects, one per agent."""
        return [
            agent.output_bt(behavior_libs[i])
            for i, agent in enumerate(self._require_planned())
        ]

    def output_pruned_bt_list(self, behavior_libs):
        """Return per-agent BTs with composite-action branches pruned."""
        return [
            agent.output_pruned_bt(behavior_libs[i])
            for i, agent in enumerate(self._require_planned())
        ]

    def get_btml_list(self):
        """Return a list of ``BTML`` objects, one per agent (rebuilds them)."""
        btml_list = []
        for agent in self._require_planned():
            agent.create_btml()
            btml_list.append(agent.btml)
        return btml_list
