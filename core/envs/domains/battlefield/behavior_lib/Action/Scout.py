"""Scout — domain action for the *battlefield* scene.

``Scout(agent-i, room-k)`` reconnoiters a stronghold, marking its threats as
*identified* so a follow-up unit can suppress them.  Planning model::

    pre : IsInRoom(agent-i, room-k)   # be inside the room (grid-derivable)
    add : IsScouted(room-k)           # the new domain fluent
    del : (none)

``IsScouted`` is the precondition that :class:`Suppress` now back-chains on, so
the battlefield domain grows from a two-step (*suppress -> secure*) plan into a
genuine **three-step** one:

    Scout  ->  Suppress  ->  Secure
   (recon)   (clear threats)  (occupy)

Each step is owned by a different predicate, which lets three units split the
work — a scout identifies, an assault unit suppresses, a holding unit secures.
Execution waits until the agent is in the room, then flips the fluent; a
simulator backend would run the real reconnaissance behaviour.
"""
from core.envs.gridenv.minigrid.behavior_lib.base.Action import MinigridAction as Action
from core.behavior_tree import Status
from minigrid.core.actions import Actions
from core.envs.gridenv.minigrid.planning_action import PlanningAction


class Scout(Action):
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
                "add": {f"IsScouted(room-{room_index})"},
                "del_set": set(),
                "cost": 1,
            }
            planning_action_list.append(
                PlanningAction(
                    f"Scout(agent-{agent.id},room-{room_index})", **action_model
                )
            )
        return planning_action_list

    def update(self) -> Status:
        if self.check_if_pre_in_predict_condition():
            return Status.RUNNING

        # 自带「最后一公里进房」，规避门格判定死锁（详见 MinigridAction.reach_room_interior）。
        if self.reach_room_interior(self.room_index):
            self.env.set_fluent(f"IsScouted(room-{self.room_index})", True)
            self.agent.action = Actions.done
        return Status.RUNNING
