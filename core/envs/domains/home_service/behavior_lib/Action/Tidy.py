"""Tidy — domain action for the *home-service* scene.

``Tidy(agent-i, room-k)`` marks a room tidy once a robot is inside it.  Planning
model::

    pre : IsInRoom(agent-i, room-k)   # be in the room (grid-derivable)
    add : IsTidy(room-k)              # domain fluent
    del : (none)

so back-chaining ``IsTidy(room-k)`` expands to ``GoToInRoom/GoBtwRoom -> Tidy``.
At execution it waits until the agent's current cell is in the room, then flips
the fluent.  Pure symbolic-on-grid today; a simulator backend would run the real
tidying routine and read ``IsTidy`` back from perception.
"""
from core.envs.gridenv.minigrid.behavior_lib.base.Action import MinigridAction as Action
from core.behavior_tree import Status
from minigrid.core.actions import Actions
from core.envs.gridenv.minigrid.planning_action import PlanningAction


class Tidy(Action):
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
        room_num = len(env.room_cells)
        for room_index in range(room_num):
            action_model = {
                "pre": {f"IsInRoom(agent-{agent.id},room-{room_index})"},
                "add": {f"IsTidy(room-{room_index})"},
                "del_set": set(),
                "cost": 1,
            }
            planning_action_list.append(
                PlanningAction(
                    f"Tidy(agent-{agent.id},room-{room_index})", **action_model
                )
            )
        return planning_action_list

    def update(self) -> Status:
        if self.check_if_pre_in_predict_condition():
            return Status.RUNNING

        if self.env.get_room_index(self.agent.position) == self.room_index:
            self.env.set_fluent(f"IsTidy(room-{self.room_index})", True)
            self.agent.action = Actions.done
            return Status.RUNNING

        # Not in the room yet: idle and let the navigation subtree move us.
        self.agent.action = Actions.done
        return Status.RUNNING
