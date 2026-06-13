"""Suppress — domain action for the *battlefield* scene.

``Suppress(agent-i, room-k)`` clears the threats in a room — but only after the
room has been scouted.  Planning model::

    pre : IsInRoom(agent-i, room-k) AND IsScouted(room-k)
    add : IsThreatCleared(room-k)          # domain fluent
    del : (none)

The ``IsScouted`` precondition turns the old two-step (*suppress -> secure*)
plan into a genuine **three-step** chain ``Scout -> Suppress -> Secure``: back-
chaining ``IsThreatCleared(room-k)`` now first forces ``IsScouted`` (via
:class:`Scout`) and only then runs ``Suppress``.  Each link is owned by a
different predicate so three units can divide the work.  Execution waits until
the agent is in the room (the scouting precondition is guaranteed by the plan
structure), then flips the fluent — a simulator backend would run the real
suppression behaviour.
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
                "pre": {
                    f"IsInRoom(agent-{agent.id},room-{room_index})",
                    f"IsScouted(room-{room_index})",
                },
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

        # 自带「最后一公里进房」，规避门格判定死锁（详见 MinigridAction.reach_room_interior）。
        if self.reach_room_interior(self.room_index):
            self.env.set_fluent(f"IsThreatCleared(room-{self.room_index})", True)
            self.agent.action = Actions.done
        return Status.RUNNING
