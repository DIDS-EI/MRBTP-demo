"""R1 structure sharing for the mainline planners.

Problem
-------
The main app's action models embed the robot id everywhere::

    Toggle(agent-0,door-0)   pre = {CanOpen(agent-0,door-0), IsClose(door-0)}
    Toggle(agent-1,door-0)   pre = {CanOpen(agent-1,door-0), IsClose(door-0)}

A raw action-set fingerprint therefore never groups two robots, and naively
sharing a representative's PlanningCondition nodes would put *agent-0's*
action names and literals into agent-1's behaviour tree.

Design
------
Share the **expansion outcome** of one representative, expressed as a
role-neutral template. Members replay it verbatim -- they do NOT re-run
relevance / subset / conflict checks (that was the source of an earlier
divergence: each agent's ``expanded_condition_dict`` had evolved differently).

A template entry carries the role-normalised accepted premise and action name.
Replaying rebinds ``@SELF@`` to the member's own id, then creates that
member's own ``PlanningCondition`` nodes and attaches them to its own tree.

Safety rules (conservative; a violation degrades to independent expansion)
-------------------------------------------------------------------------
  * Grouping requires an identical *ordered* role-neutral action fingerprint
    (name/pre/add/del_set/cost). Any difference -> own group.
  * An action that mentions another robot's id excludes that robot from
    sharing: the role model would not be self-contained.
  * Sharing is enabled only for conditions containing **no** ``agent-N``
    literal. Cross-tree conditions that name a specific robot are expanded
    independently by every agent (the original behaviour).
  * If a role-rebound name is missing from a member's action list, the whole
    group falls back to independent expansion for that condition.
  * ``single_expand`` mode is never shared (only one agent expands by design).
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Sequence, Tuple

from core.btp.base.planning_condition import PlanningCondition

SELF_TOKEN = "@SELF@"
_ROBOT_ID = re.compile(r"(?<![A-Za-z0-9_-])agent-(\d+)(?![A-Za-z0-9_-])")


def _to_role(text: Any, agent_id: int) -> str:
    return str(text).replace(f"agent-{agent_id}", SELF_TOKEN)


def _from_role(text: str, agent_id: int) -> str:
    return text.replace(SELF_TOKEN, f"agent-{agent_id}")


def condition_is_shareable(condition) -> bool:
    """Only identity-free conditions can be shared safely."""
    return not any(_ROBOT_ID.search(str(x)) for x in condition)


def has_foreign_robot_id(action_list: Sequence[Any], agent_id: int) -> bool:
    own = str(agent_id)
    for action in action_list:
        texts = [str(action.name)]
        for field in (action.pre, action.add, action.del_set):
            texts.extend(str(x) for x in field)
        for text in texts:
            if any(m.group(1) != own for m in _ROBOT_ID.finditer(text)):
                return True
    return False


def capability_key(action_list: Sequence[Any], agent_id: int) -> Tuple:
    """Ordered, role-neutral fingerprint of an agent's capability set."""
    return tuple(
        (
            _to_role(action.name, agent_id),
            tuple(sorted(_to_role(x, agent_id) for x in action.pre)),
            tuple(sorted(_to_role(x, agent_id) for x in action.add)),
            tuple(sorted(_to_role(x, agent_id) for x in action.del_set)),
            float(action.cost),
        )
        for action in action_list
    )


MIN_GROUP_SIZE = 3


def build_groups(action_lists: Sequence[Sequence[Any]], enabled: bool,
                 min_group_size: int = MIN_GROUP_SIZE):
    """Return (group_keys, representative_index, profitable).

    Role-normalisation and template construction are not free. With only two
    robots in a group, a shared condition saves at most one expansion and the
    bookkeeping dominates (measured: the main app smoke scenario slowed down).
    Groups smaller than ``min_group_size`` therefore stay separate, and when
    no group qualifies ``profitable`` is False so callers can take the
    original code path with zero extra work.
    """
    n = len(action_lists)
    if not enabled or n < min_group_size:
        # Zero-overhead fast path: not enough robots for sharing to pay off,
        # or the caller explicitly disabled it. Skip all fingerprinting.
        return ([("__unique__", i) for i in range(n)], list(range(n)), False)

    keys: List[Tuple] = []
    rep_of: Dict[Tuple, int] = {}
    rep_index: List[int] = []
    counts: Dict[Tuple, int] = {}
    for i, actions in enumerate(action_lists):
        if has_foreign_robot_id(actions, i):
            key = ("__unique__", i, capability_key(actions, i))
        else:
            key = capability_key(actions, i)
        keys.append(key)
        rep_of.setdefault(key, i)
        rep_index.append(rep_of[key])
        counts[key] = counts.get(key, 0) + 1
    profitable = any(c >= min_group_size for c in counts.values())
    if not profitable:
        keys = [("__unique__", i, keys[i]) for i in range(len(keys))]
        rep_index = list(range(len(keys)))
    return keys, rep_index, profitable


# Template entry: (role_premise_literals, role_action_name, composition_flag,
#                  role_sub_goal, role_sub_del)
TemplateEntry = Tuple[Tuple[str, ...], str, bool, Tuple[str, ...], Tuple[str, ...]]


def make_template(premises: Sequence[PlanningCondition], rep_id: int) -> Tuple[TemplateEntry, ...]:
    """Role-neutral snapshot of what the representative accepted."""
    out: List[TemplateEntry] = []
    for pc in premises:
        if not pc.action:
            continue
        out.append((
            tuple(sorted(_to_role(x, rep_id) for x in pc.condition_set)),
            _to_role(pc.action, rep_id),
            bool(pc.composition_action_flag),
            tuple(sorted(_to_role(x, rep_id) for x in (pc.sub_goal or ()))),
            tuple(sorted(_to_role(x, rep_id) for x in (pc.sub_del or ()))),
        ))
    return tuple(out)


def _instantiate(agent, entry: TemplateEntry, cost_aware: bool):
    """Create ONE PremiseCondition for this agent from a template entry."""
    role_cond, role_action, comp, role_sg, role_sd = entry
    own_name = _from_role(role_action, agent.id)
    name2act = {a.name: a for a in agent.action_list}
    if own_name not in name2act:
        raise LookupError(f"cannot rebind {role_action!r} for agent-{agent.id}")
    premise = frozenset(_from_role(x, agent.id) for x in role_cond)
    sub_goal = frozenset(_from_role(x, agent.id) for x in role_sg)
    sub_del = frozenset(_from_role(x, agent.id) for x in role_sd)
    if cost_aware:
        pc = PlanningCondition(premise, own_name, comp, sub_goal, sub_del)
    else:
        pc = PlanningCondition(premise, own_name)
    return pc, name2act[own_name].cost


def replay(agent, template: Tuple[TemplateEntry, ...], condition):
    """FIFO replay: verbatim decisions, per-agent concrete output."""
    inside_condition = agent.expanded_condition_dict.get(condition, None)
    produced: List[PlanningCondition] = []
    for entry in template:
        pc, _cost = _instantiate(agent, entry, cost_aware=False)
        produced.append(pc)
        agent.expanded_condition_dict[pc.condition_set] = pc
    if inside_condition:
        agent.inside_expand(inside_condition, produced)
    elif produced:
        agent.outside_expand(condition, produced)
    return produced


def replay_cost(agent, template: Tuple[TemplateEntry, ...], condition_cost):
    """Cost-aware replay; returns a list of ``CondCostPair``."""
    from core.btp.multi_robot_optimal import CondCostPair

    condition = condition_cost.cond
    inbound_cost = condition_cost.cost
    inside_condition = agent.expanded_condition_dict.get(condition, None)
    produced: List[PlanningCondition] = []
    costs: List[Any] = []
    for entry in template:
        pc, action_cost = _instantiate(agent, entry, cost_aware=True)
        produced.append(pc)
        agent.expanded_condition_dict[pc.condition_set] = pc
        costs.append(CondCostPair(pc.condition_set, inbound_cost + action_cost))
    if inside_condition:
        agent.inside_expand(inside_condition, produced)
    elif produced:
        agent.outside_expand(condition, produced)
    return costs
