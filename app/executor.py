"""Part 2 — Execute the planned behavior trees.

This is the *execution* half of MRBTP.  Every simulation step, each agent
ticks its own behavior tree, decides a primitive MiniGrid action, and the
environment applies it.

The headline feature is the ``share_belief`` switch, which controls the
**multi-agent communication / belief space**:

    * ``share_belief=True``  (default, the paper's behaviour)
        Agents coordinate through ``env.blackboard["predict_condition"]``.
        When one agent accepts a macro task, its sub-goals are broadcast so
        the others *assume those literals will become true* and therefore
        (a) don't redundantly redo the same job and (b) wait on preconditions
        a teammate is about to satisfy (e.g. "door will be opened").

    * ``share_belief=False``
        Each agent's belief space is kept empty, so every agent reasons
        purely from the *real* environment state with no knowledge of what
        the others intend.  This is the useful ablation: you can watch the
        team lose coordination (duplicated work / deadlocks) when the shared
        channel is switched off.

How the toggle works under the hood
-----------------------------------
The coordination is implemented in ``Agent.finish_current_task`` /
``Agent.update_current_task`` (they write predicted literals into the
blackboard and copy them onto every agent's ``predict_condition``).  The
behavior-tree nodes then read ``agent.predict_condition`` in
``check_if_in_predict_condition`` (conditions) and
``check_if_pre_in_predict_condition`` (actions).

To disable sharing *without editing the library*, we replace those two
methods on each agent instance with no-broadcast versions and keep every
``predict_condition`` empty.  Conditions/actions then always fall through
to the real-state checks.
"""

from __future__ import annotations

import copy
import types
from dataclasses import dataclass, field
from typing import Callable, List, Optional

from core.behavior_tree.utils import Status
from core.utils.tools import print_colored

from app.planner import PlanResult


@dataclass
class TickRecord:
    """The behavior-tree tick outcome for one agent in one simulation step."""

    agent_id: int
    action_name: str          # the MiniGrid primitive chosen this step
    bt_status: str            # SUCCESS / RUNNING / FAILURE of the BT root
    tick_output: str          # per-node status lines from the StatusVisitor


@dataclass
class StepRecord:
    """All agents' tick outcomes for a single simulation step."""

    step: int
    ticks: List[TickRecord] = field(default_factory=list)
    done: bool = False


@dataclass
class ExecutionResult:
    """Summary of a full execution run."""

    success: bool
    steps: int
    share_belief: bool
    history: List[StepRecord] = field(default_factory=list)


# A hook called after every simulation step (used by the visualizer to
# render + print the tick result live).
StepCallback = Callable[[StepRecord, "object"], None]


def execute(
    env,
    plan: PlanResult,
    *,
    share_belief: bool = True,
    max_steps: int = 500,
    on_step: Optional[StepCallback] = None,
    should_stop: Optional[Callable[[StepRecord, "object"], bool]] = None,
    print_ticks: bool = False,
) -> ExecutionResult:
    """Run the planned behavior trees until the goal is met or steps run out.

    Args:
        env: the built environment whose ``agents`` will run the plan.
        plan: the :class:`PlanResult` returned by ``plan_behavior_trees``.
        share_belief: enable/disable the shared communication belief space.
        max_steps: hard cap on simulation steps (safety against deadlocks).
        on_step: optional callback invoked with each :class:`StepRecord`
            (and the env) right after the step is applied — the visualizer
            uses this to render and print.
        should_stop: optional predicate ``(record, env) -> bool`` checked
            after each step; returning ``True`` aborts the run early (still
            reported as ``success=False``). Useful to bail out of a detected
            deadlock instead of spinning all the way to ``max_steps``.
        print_ticks: if ``True``, print a compact tick summary each step.

    Returns:
        An :class:`ExecutionResult` with the full per-step history.
    """
    # Bind each behavior tree to its agent.
    for agent, bt in zip(env.agents, plan.bt_list):
        agent.bind_bt(bt)

    # Configure the belief space according to the toggle.
    if not share_belief:
        _disable_belief_sharing(env)

    # The env prints its own verbose tick block when this is on; we keep it
    # off and produce our own compact summary instead.
    env.print_ticks = False

    history: List[StepRecord] = []
    done = False
    aborted = False
    step = 0

    while not done and step < max_steps:
        # Drive every agent one tick and apply their actions to the world.
        done = _step_all_agents(env)

        record = _collect_step_record(env, step, done)
        history.append(record)

        if print_ticks:
            _print_step(record)
        if on_step is not None:
            on_step(record, env)

        step += 1

        if not done and should_stop is not None and should_stop(record, env):
            aborted = True
            break

    if aborted:
        print_colored(f"\nAborted early at step {step} (deadlock detected, "
                      f"share_belief={share_belief}).", "red")
    elif done:
        print_colored(f"\nTask finished in {step} steps "
                      f"(share_belief={share_belief}).", "green")
    else:
        print_colored(f"\nReached max_steps={max_steps} without finishing "
                      f"(share_belief={share_belief}).", "red")

    return ExecutionResult(
        success=done, steps=step, share_belief=share_belief, history=history
    )


# --------------------------------------------------------------------------- #
# Stepping
# --------------------------------------------------------------------------- #

def _step_all_agents(env) -> bool:
    """Tick every agent once and apply its chosen action. Returns ``done``.

    This mirrors ``MiniGridMAGridEnv.step`` but is spelled out here so the
    demo's main loop is transparent (and so we never accidentally trigger the
    env's own pygame rendering — the visualizer owns rendering).

    Backends that own their own stepping (e.g. the pure-symbolic VirtualHome
    backend, which has no poses to focus / update) may expose ``tick_step()``;
    it takes over the whole step and keeps the MiniGrid-specific
    ``set_focus_agent / agent_step / get_focus_agent`` triple out of the
    backend contract.  The built-in MiniGrid path is unchanged.
    """
    if hasattr(env, "tick_step"):
        return bool(env.tick_step())

    env.step_count += 1
    done = True

    for i in range(env.num_agent):
        agent = env.agents[i]
        action = agent.step()                # ticks the agent's behavior tree

        env.set_focus_agent(agent)           # load this agent's pose
        env.agent_step(action)               # apply the primitive to the grid
        env.get_focus_agent(agent)           # store the updated pose back

        if not agent.bt_success:
            done = False

    return done


def _collect_step_record(env, step: int, done: bool) -> StepRecord:
    """Read each agent's behavior-tree tick result into a StepRecord."""
    record = StepRecord(step=step, done=done)
    for i, agent in enumerate(env.agents):
        bt = agent.bt
        status = bt.root.status.value if bt.root.status is not None else "INVALID"
        record.ticks.append(
            TickRecord(
                agent_id=i,
                action_name=getattr(agent.action, "name", str(agent.action)),
                bt_status=status,
                tick_output=bt.visitor.output_str,
            )
        )
    return record


def _print_step(record: StepRecord) -> None:
    """Compact, colourised per-step summary."""
    print_colored(f"===== step {record.step} =====", "blue")
    for tick in record.ticks:
        colour = "green" if tick.bt_status == "SUCCESS" else "yellow"
        print_colored(
            f"  agent-{tick.agent_id}: action={tick.action_name:<8} "
            f"bt={tick.bt_status}",
            colour,
        )


# --------------------------------------------------------------------------- #
# Belief-space toggle
# --------------------------------------------------------------------------- #

def _disable_belief_sharing(env) -> None:
    """Turn every agent into an island: no shared predicted conditions.

    We swap the two coordination methods for no-broadcast stand-ins and
    clear the blackboard / per-agent prediction sets.  After this, the
    behavior-tree nodes always evaluate against the real environment state.
    """
    env.blackboard["predict_condition"] = {"success": set(), "fail": set()}
    env.blackboard["task_agents_queue"] = []

    for agent in env.agents:
        agent.predict_condition = {"success": set(), "fail": set()}

        def finish_current_task(self):
            # No teammate broadcast — only forget any finished task locally.
            return None

        def update_current_task(self):
            # Keep the step()-loop's re-tick bookkeeping intact, but never
            # write predicted literals into the (shared) belief space.
            self.last_accept_task = copy.deepcopy(self.current_task)
            self.predict_condition = {"success": set(), "fail": set()}

        agent.finish_current_task = types.MethodType(finish_current_task, agent)
        agent.update_current_task = types.MethodType(update_current_task, agent)
