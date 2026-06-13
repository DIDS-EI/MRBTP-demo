"""Sweep — domain action for the *home-service* scene.

``Sweep(agent-i, room-k)`` sweeps a room's floor clean of dust.  Planning
model::

    pre : IsInRoom(agent-i, room-k)   # be inside the room (grid-derivable)
    add : IsSwept(room-k)             # the new domain fluent
    del : (none)

so back-chaining ``IsSwept(room-k)`` expands to ``GoToInRoom/GoBtwRoom ->
Sweep`` for free, reusing the shared navigation actions.  At *execution* time
the action waits until the agent's current cell is inside the room, then flips
the symbolic fluent on the env's ``domain_state`` store and yields ``done`` —
the same "reach then mutate world" shape as :class:`Tidy`.

This is a deliberately *room-scoped* chore (cf. :class:`Stock`, which is
*object-scoped*).  Together with the pre-existing ``Wipe`` / ``Tidy`` they give
the home domain a genuinely **richer, heterogeneous** action palette so three
robots can each own a different kind of housework.
"""
from core.envs.gridenv.minigrid.behavior_lib.base.Action import MinigridAction as Action
from core.behavior_tree import Status
from minigrid.core.actions import Actions
from core.envs.gridenv.minigrid.planning_action import PlanningAction


class Sweep(Action):
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
                "add": {f"IsSwept(room-{room_index})"},
                "del_set": set(),
                "cost": 1,
            }
            planning_action_list.append(
                PlanningAction(
                    f"Sweep(agent-{agent.id},room-{room_index})", **action_model
                )
            )
        return planning_action_list

    def update(self) -> Status:
        if self.check_if_pre_in_predict_condition():
            return Status.RUNNING

        # 自带「最后一公里进房」：被导航子树撂在门口时，helper 会把 agent 拽进
        # 房间内核；真正落到房间内部格才 flip fluent，规避门格判定死锁。
        if self.reach_room_interior(self.room_index):
            self.env.set_fluent(f"IsSwept(room-{self.room_index})", True)
            from minigrid.core.actions import Actions
            self.agent.action = Actions.done
        return Status.RUNNING
