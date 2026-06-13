"""Stock — domain action for the *home-service* scene.

``Stock(agent-i, <obj>)`` puts an item away into storage (a cupboard / drawer).
Unlike the *room-scoped* :class:`Sweep` / :class:`Tidy`, this is an
*object-scoped* chore with a genuine **two-step** precondition::

    pre : IsHolding(agent-i, obj)     # you must be carrying it first
    add : IsStocked(obj)              # the new domain fluent
    del : (none)

The ``IsHolding`` precondition is what makes ``Stock`` a real two-step plan:
back-chaining ``IsStocked(obj)`` forces the planner to first achieve
``IsHolding`` (via the shared ``GoToInRoom -> PickUp`` chain) and only then run
``Stock``.  This mirrors the battlefield domain's ``Suppress -> Secure`` shape,
giving the home domain its own layered chore on top of the flat ``Wipe`` /
``Tidy`` / ``Sweep`` actions.

At *execution* time the action simply confirms the item is in hand, then flips
the symbolic fluent.  A robot-simulator backend would replace the body with a
real "open cupboard + place item" motion and read ``IsStocked`` back from
perception, but the planning model and predicate contract stay identical.
"""
from core.envs.gridenv.minigrid.behavior_lib.base.Action import MinigridAction as Action
from core.behavior_tree import Status
from minigrid.core.actions import Actions
from core.envs.gridenv.minigrid.objects import CAN_PICKUP
from core.envs.gridenv.minigrid.planning_action import PlanningAction


class Stock(Action):
    can_be_expanded = True
    num_args = 2
    valid_args = [CAN_PICKUP]

    def __init__(self, *args):
        super().__init__(*args)
        self.agent_id = args[0]
        self.obj_id = args[1]

    @classmethod
    def get_planning_action_list(cls, agent, env):
        planning_action_list = []
        # Same "things you can pick up" set the grid actions build, so Stock
        # targets line up with PickUp targets.
        can_pickup = env.cache.get("can_pickup")
        if can_pickup is None:
            can_pickup = [o.id for o in env.obj_list if o.type in cls.valid_args[0]]
            env.cache["can_pickup"] = can_pickup

        for obj_id in can_pickup:
            action_model = {
                "pre": {f"IsHolding(agent-{agent.id},{obj_id})"},
                "add": {f"IsStocked({obj_id})"},
                "del_set": set(),
                "cost": 1,
            }
            planning_action_list.append(
                PlanningAction(f"Stock(agent-{agent.id},{obj_id})", **action_model)
            )
        return planning_action_list

    def update(self) -> Status:
        if self.check_if_pre_in_predict_condition():
            return Status.RUNNING

        obj = self.env.id2obj.get(self.obj_id)
        carried = obj is not None and self.agent.carrying is obj
        if carried:
            # Holding it -> commit the symbolic "put away" outcome.
            self.env.set_fluent(f"IsStocked({self.obj_id})", True)
            self.agent.action = Actions.done
            return Status.RUNNING

        # Not in hand yet: idle this tick; the sibling PickUp subtree carries
        # us through grabbing it first (mirrors how grid actions wait on pre).
        self.agent.action = Actions.done
        return Status.RUNNING
