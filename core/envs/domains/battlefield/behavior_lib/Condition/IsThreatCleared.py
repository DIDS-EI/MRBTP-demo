"""IsThreatCleared — domain fluent for the *battlefield* scene.

``IsThreatCleared(<room>)`` holds once a unit has suppressed the threats in a
room.  Symbolic fluent stored in :attr:`MiniGridToMAGridEnv.domain_state`, set
by the :class:`Suppress` action.  It is the precondition for :class:`Secure`,
so the planner naturally orders *suppress then secure*.
"""
from core.behavior_tree.base_nodes import Condition
from core.behavior_tree import Status


class IsThreatCleared(Condition):
    num_args = 1

    def __init__(self, *args):
        super().__init__(*args)
        self.room_id = args[0]

    def update(self) -> Status:
        is_in_predict, is_true = self.check_if_in_predict_condition()
        if is_in_predict:
            return Status.SUCCESS if is_true else Status.FAILURE

        if self.env.has_fluent(f"IsThreatCleared({self.room_id})"):
            return Status.SUCCESS
        return Status.FAILURE
