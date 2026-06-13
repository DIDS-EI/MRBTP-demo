"""Secure — domain action for the *battlefield* scene.

``Secure(agent-i, room-k)`` secures a room, but only after its threats are
cleared.  Planning model::

    pre : IsInRoom(agent-i, room-k) AND IsThreatCleared(room-k)
    add : IsSecured(room-k)
    del : (none)

The ``IsThreatCleared`` precondition is what gives the battlefield domain a
genuine *two-step* plan: back-chaining ``IsSecured(room-k)`` forces the planner
to first achieve ``IsThreatCleared`` (via :class:`Suppress`) and only then run
``Secure``.  Execution flips the fluent once the agent is in the room (the
clearance precondition is guaranteed by the plan structure).
"""
from core.envs.gridenv.minigrid.behavior_lib.base.Action import MinigridAction as Action
from core.behavior_tree import Status
from minigrid.core.actions import Actions
from core.envs.gridenv.minigrid.planning_action import PlanningAction


class Secure(Action):
    can_be_expanded = True
    num_args = 2

    def __init__(self, *args):
        super().__init__(*args)
        self.agent_id = args[0]
        self.room_id = args[1]
        self.room_index = int("".join(filter(str.isdigit, self.room_id)))

    @classmethod
    def get_planning_action_list(cls, agent, env):
        planning_action_list = []
        for room_index in range(len(env.room_cells)):
            action_model = {
                "pre": {
                    f"IsInRoom(agent-{agent.id},room-{room_index})",
                    f"IsThreatCleared(room-{room_index})",
                },
                "add": {f"IsSecured(room-{room_index})"},
                "del_set": set(),
                "cost": 1,
            }
            planning_action_list.append(
                PlanningAction(
                    f"Secure(agent-{agent.id},room-{room_index})", **action_model
                )
            )
        return planning_action_list

    def update(self) -> Status:
        if self.check_if_pre_in_predict_condition():
            return Status.RUNNING

        if self.env.get_room_index(self.agent.position) == self.room_index:
            self.env.set_fluent(f"IsSecured(room-{self.room_index})", True)
            self.agent.action = Actions.done
            return Status.RUNNING

        self.agent.action = Actions.done
        return Status.RUNNING
