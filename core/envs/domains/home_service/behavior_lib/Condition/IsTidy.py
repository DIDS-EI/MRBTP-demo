"""IsTidy — domain fluent for the *home-service* scene.

``IsTidy(<room>)`` holds once a robot has tidied a room (e.g. all loose items
parked at their home spots).  Like :class:`IsClean` it is a symbolic fluent
maintained in :attr:`MiniGridToMAGridEnv.domain_state`, set by the :class:`Tidy`
action.  Rooms are referenced by their planning id ``room-<k>``.
"""
from core.behavior_tree.base_nodes import Condition
from core.behavior_tree import Status


class IsTidy(Condition):
    num_args = 1

    def __init__(self, *args):
        super().__init__(*args)
        self.room_id = args[0]

    def update(self) -> Status:
        is_in_predict, is_true = self.check_if_in_predict_condition()
        if is_in_predict:
            return Status.SUCCESS if is_true else Status.FAILURE

        if self.env.has_fluent(f"IsTidy({self.room_id})"):
            return Status.SUCCESS
        return Status.FAILURE
