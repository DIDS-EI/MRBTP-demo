"""Suppress — domain action for the *battlefield* scene.

``Suppress(agent-i, room-k)`` clears the threats in a room.  Planning model::

    pre : IsInRoom(agent-i, room-k)        # be in the room
    add : IsThreatCleared(room-k)          # domain fluent
    del : (none)

so back-chaining ``IsThreatCleared(room-k)`` expands to ``GoTo... -> Suppress``.
This is the first half of the two-step *suppress -> secure* battlefield plan
(see :class:`Secure`).  Execution waits until the agent is in the room, then
flips the fluent — a simulator backend would run the real suppression behaviour.
"""
from core.envs.gridenv.minigrid.behavior_lib.base.Action import MinigridAction as Action
from core.behavior_tree import Status
from minigrid.core.actions import Actions
from core.envs.gridenv.minigrid.planning_action import PlanningAction


class Suppress(Action):
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
                "pre": {f"IsInRoom(agent-{agent.id},room-{room_index})"},
                "add": {f"IsThreatCleared(room-{room_index})"},
                "del_set": set(),
                "cost": 1,
            }
            planning_action_list.append(
                PlanningAction(
                    f"Suppress(agent-{agent.id},room-{room_index})", **action_model
                )
            )
        return planning_action_list

    def update(self) -> Status:
        if self.check_if_pre_in_predict_condition():
            return Status.RUNNING

        if self.env.get_room_index(self.agent.position) == self.room_index:
            self.env.set_fluent(f"IsThreatCleared(room-{self.room_index})", True)
            self.agent.action = Actions.done
            return Status.RUNNING

        self.agent.action = Actions.done
        return Status.RUNNING
