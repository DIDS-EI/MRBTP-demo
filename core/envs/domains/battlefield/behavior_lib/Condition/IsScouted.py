"""IsScouted — domain fluent for the *battlefield* scene.

``IsScouted(<room>)`` holds once a unit has reconnoitered a stronghold.
Symbolic fluent in :attr:`MiniGridToMAGridEnv.domain_state`, set by the
:class:`Scout` action.  It is the precondition for :class:`Suppress`, so the
planner naturally orders *scout -> suppress -> secure* — the battlefield
domain's three-step tactical chain.
"""
from core.behavior_tree.base_nodes import Condition
from core.behavior_tree import Status


class IsScouted(Condition):
    num_args = 1

    def __init__(self, *args):
        super().__init__(*args)
        self.room_id = args[0]

    def update(self) -> Status:
        is_in_predict, is_true = self.check_if_in_predict_condition()
        if is_in_predict:
            return Status.SUCCESS if is_true else Status.FAILURE

        if self.env.has_fluent(f"IsScouted({self.room_id})"):
            return Status.SUCCESS
        return Status.FAILURE
