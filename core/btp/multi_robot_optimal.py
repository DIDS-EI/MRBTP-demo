"""
MAOBTP — Multi-Robot Optimal Behavior Tree Planning.

Same back-chaining structure as ``MABTP`` but the search frontier is a
priority queue ordered by accumulated action cost, which lets the planner
prefer cheaper plans and integrates *composite* (sub-tree) actions whose
cost is recorded as 0.

The companion class ``CostAwarePlanningAgent`` is a drop-in replacement for
``PlanningAgent`` that propagates the action cost and tags premises with
composite-action metadata.
"""

from __future__ import annotations

import functools
import heapq
import time
from typing import List, Optional

from core.btp.base.planning_agent import PlanningAgent
from core.btp.base.planning_condition import PlanningCondition
from core.btp.multi_robot_basic import MABTP
from core.utils.tools import print_colored


@functools.total_ordering
class CondCostPair:
    """A (condition, cumulative-cost) pair ordered by cost (heap entry)."""

    __slots__ = ("cond", "cost")

    def __init__(self, cond, cost):
        self.cond = cond
        self.cost = cost

    def __eq__(self, other):
        return isinstance(other, CondCostPair) and self.cost == other.cost

    def __lt__(self, other):
        return self.cost < other.cost


class CostAwarePlanningAgent(PlanningAgent):
    """``PlanningAgent`` variant that tracks per-action cost and composite-action metadata."""

    def one_step_expand(self, condition_cost: CondCostPair) -> List[CondCostPair]:
        condition, cost = condition_cost.cond, condition_cost.cost

        # Decide tree-internal vs tree-external expansion *before* expanding.
        inside_condition = self.expanded_condition_dict.get(condition, None)

        premise_condition_list: List[PlanningCondition] = []
        premise_condition_cost_list: List[CondCostPair] = []
        for action in self.action_list:
            if not self.is_consequence(condition, action):
                continue
            premise_condition = frozenset((action.pre | condition) - action.add)
            if not self.has_no_subset(premise_condition):
                continue

            if self.env is not None and self.env.check_conflict(premise_condition):
                continue

            composition_action_flag = action.cost == 0
            sub_goal = frozenset(condition & frozenset(action.add))
            sub_del = action.del_set

            planning_condition = PlanningCondition(
                premise_condition,
                action.name,
                composition_action_flag,
                sub_goal,
                sub_del,
            )
            premise_condition_list.append(planning_condition)
            self.expanded_condition_dict[premise_condition] = planning_condition

            new_cost = cost + action.cost
            premise_condition_cost_list.append(
                CondCostPair(premise_condition, new_cost)
            )

            if self.verbose:
                print_colored("inside" if inside_condition else "outside", "purple")
                print_colored(
                    f"a:{action.name} \t c_attr:{premise_condition}", "orange"
                )

        if inside_condition:
            self.inside_expand(inside_condition, premise_condition_list)
        elif premise_condition_list:
            self.outside_expand(condition, premise_condition_list)

        return premise_condition_cost_list


# Backward-compatible alias (older scripts import ``BfsPlanningAgent``).
BfsPlanningAgent = CostAwarePlanningAgent


class MAOBTP(MABTP):
    """Cost-aware multi-robot behavior-tree planner with composite actions."""

    def bfs_planning(self, goal, action_lists, single_expand: bool = False) -> None:
        """Best-first multi-robot back-chaining search ordered by accumulated cost.

        Args:
            goal: the shared symbolic goal condition.
            action_lists: per-agent grounded action models.
            single_expand: expansion policy for each popped condition.

                * ``False`` (default, classic MAOBTP) — **every** agent expands
                  **every** popped condition.  Each agent grows its own tree and
                  whichever one can cover a sub-goal does; coordination is then
                  resolved at run time.  Maximally flexible but the branching
                  factor scales with the team size, so it explodes on
                  many-room / many-agent problems.

                * ``True`` (division-of-labour) — each popped condition is
                  expanded by **exactly one** agent.  We round-robin the
                  *starting* agent across successive pops (so different
                  sub-goals naturally fall to different robots instead of
                  agent-0 hogging the whole goal), and if the chosen agent
                  cannot act on the condition we hand it to the next agent that
                  can.  This prunes the redundant per-agent re-expansion, giving
                  a much smaller search and an explicit task split — at the cost
                  of the extra "let another robot take this sub-goal" plans the
                  classic mode keeps.
        """
        start_time = time.time()

        planning_agent_list = [
            CostAwarePlanningAgent(
                action_list, goal, id=i, verbose=self.verbose, env=self.env
            )
            for i, action_list in enumerate(action_lists)
        ]
        num_agent = len(planning_agent_list)

        frontier: List[CondCostPair] = []
        heapq.heappush(frontier, CondCostPair(goal, 0))

        # Round-robin cursor: the agent index we *prefer* to start with on the
        # next popped condition (only consulted in single_expand mode).
        rr_cursor = 0

        while frontier:
            self.record_expanded_num += 1

            condition_cost = heapq.heappop(frontier)
            condition = condition_cost.cond

            if self.verbose:
                print_colored(f"C:{condition}", "green")

            if not single_expand:
                # ---- classic mode: every agent expands this condition ------
                for agent in planning_agent_list:
                    if self.verbose:
                        print_colored(f"Agent:{agent.id}", "purple")
                    premise_condition_cost_list = agent.one_step_expand(condition_cost)
                    for cond_cost in premise_condition_cost_list:
                        heapq.heappush(frontier, cond_cost)
            else:
                # ---- division-of-labour: exactly one agent expands ---------
                # Try agents starting at the round-robin cursor; the first one
                # that actually produces a premise "claims" this condition.
                # If nobody can act on it, we simply drop it (a dead branch in
                # this agent assignment) — other branches still reach the goal.
                claimed = False
                for offset in range(num_agent):
                    agent = planning_agent_list[(rr_cursor + offset) % num_agent]
                    if self.verbose:
                        print_colored(f"Agent:{agent.id} (single)", "purple")
                    premise_condition_cost_list = agent.one_step_expand(condition_cost)
                    if premise_condition_cost_list:
                        for cond_cost in premise_condition_cost_list:
                            heapq.heappush(frontier, cond_cost)
                        # Advance the cursor past the claimer so the next
                        # condition prefers a different robot.
                        rr_cursor = (agent.id + 1) % num_agent
                        claimed = True
                        break
                if self.verbose and not claimed:
                    print_colored(f"  (no agent could expand {condition})", "orange")

            if self.start is not None and self.start >= condition:
                break
            if time.time() - start_time > self.max_time_limit:
                self.expanded_time = time.time() - start_time
                break

        self.planned_agent_list = planning_agent_list
