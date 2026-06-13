"""Fortify — domain action for the *battlefield* scene.

``Fortify(agent-i, room-k)`` builds defensive works (sandbags / barricades) in
a stronghold.  Planning model::

    pre : IsInRoom(agent-i, room-k)   # be inside the room (grid-derivable)
    add : IsFortified(room-k)         # the new domain fluent
    del : (none)

Unlike the *scout -> suppress -> secure* chain, fortifying is an **independent**
room-scoped task: it has no dependency on the threat-clearing chain, so the
planner can hand it to a free unit in parallel.  This widens the battlefield
action palette beyond the single tactical chain, mirroring how the home domain
mixes a layered chore (``Stock``) with flat ones (``Sweep`` / ``Wipe``).

Execution waits until the agent is in the room, then flips the fluent; a
simulator backend would run the real fortification behaviour.
"""
from core.envs.gridenv.minigrid.behavior_lib.base.Action import MinigridAction as Action
from core.behavior_tree import Status
from minigrid.core.actions import Actions
from core.envs.gridenv.minigrid.planning_action import PlanningAction


class Fortify(Action):
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
                "add": {f"IsFortified(room-{room_index})"},
                "del_set": set(),
                "cost": 1,
            }
            planning_action_list.append(
                PlanningAction(
                    f"Fortify(agent-{agent.id},room-{room_index})", **action_model
                )
            )
        return planning_action_list

    def update(self) -> Status:
        if self.check_if_pre_in_predict_condition():
            return Status.RUNNING

        # 自带「最后一公里进房」，规避门格判定死锁（详见 MinigridAction.reach_room_interior）。
        if self.reach_room_interior(self.room_index):
            self.env.set_fluent(f"IsFortified(room-{self.room_index})", True)
            self.agent.action = Actions.done
        return Status.RUNNING
