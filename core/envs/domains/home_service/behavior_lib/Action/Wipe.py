"""Wipe — domain action for the *home-service* scene.

``Wipe(agent-i, <obj>)`` makes a dirty object clean.  Its *planning model*
chains naturally onto the shared grid primitives:

    pre : IsNear(agent-i, obj)      # must be next to it (grid-derivable)
    add : IsClean(obj)              # the new domain fluent
    del : (none)

so the back-chaining planner expands ``IsClean(obj)`` into
``GoToInRoom(...) -> Wipe(...)`` for free, reusing the existing navigation
actions.  At *execution* time the action waits until the agent is physically
adjacent (the grid truth), then flips the symbolic fluent on the env's
``domain_state`` store and yields ``done`` for that tick — exactly the same
"reach then mutate world" shape as :class:`Toggle`.

A robot-simulator backend would replace the body of :meth:`update` with a real
wiping motion and read ``IsClean`` back from perception, but the planning model
and the predicate contract stay identical.
"""
from core.envs.gridenv.minigrid.behavior_lib.base.Action import MinigridAction as Action
from core.behavior_tree import Status
from minigrid.core.actions import Actions
from core.envs.gridenv.minigrid.objects import CAN_PICKUP
from core.envs.gridenv.minigrid.planning_action import PlanningAction
from core.utils.astar import is_near


class Wipe(Action):
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
        # Reuse the same "things you can stand next to" set the grid actions
        # build, so Wipe targets line up with GoToInRoom targets.
        can_pickup = env.cache.get("can_pickup")
        if can_pickup is None:
            can_pickup = [o.id for o in env.obj_list if o.type in cls.valid_args[0]]
            env.cache["can_pickup"] = can_pickup

        for obj_id in can_pickup:
            action_model = {
                "pre": {f"IsNear(agent-{agent.id},{obj_id})"},
                "add": {f"IsClean({obj_id})"},
                "del_set": set(),
                "cost": 1,
            }
            planning_action_list.append(
                PlanningAction(f"Wipe(agent-{agent.id},{obj_id})", **action_model)
            )
        return planning_action_list

    def update(self) -> Status:
        if self.check_if_pre_in_predict_condition():
            return Status.RUNNING

        obj = self.env.id2obj.get(self.obj_id)
        # If the object is being carried it has no cell; treat "in hand" as
        # adjacent so the team can still clean what it picked up.
        target_pos = None if obj is None else obj.cur_pos
        adjacent = (
            obj is not None
            and target_pos is not None
            and tuple(target_pos) != (-1, -1)
            and is_near(list(target_pos), self.agent.position)
        )
        carried = obj is not None and self.agent.carrying is obj

        if adjacent or carried:
            # Reached the object on the grid -> mutate the symbolic world.
            self.env.set_fluent(f"IsClean({self.obj_id})", True)
            self.agent.action = Actions.done
            return Status.RUNNING

        # Not adjacent yet: idle this tick and let the sibling GoTo subtree
        # carry us there (mirrors how the grid actions wait on their pre).
        self.agent.action = Actions.done
        return Status.RUNNING
