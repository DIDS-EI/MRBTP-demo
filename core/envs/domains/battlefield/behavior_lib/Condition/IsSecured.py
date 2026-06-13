"""IsSecured — domain fluent for the *battlefield* scene.

``IsSecured(<room>)`` holds once a unit has secured a (threat-cleared) room.
Symbolic fluent in :attr:`MiniGridToMAGridEnv.domain_state`, set by the
:class:`Secure` action.  Securing requires the threat to be cleared first, which
the planner enforces through :class:`Secure`'s precondition on
``IsThreatCleared`` — giving a genuine two-step domain plan.
"""
from core.behavior_tree.base_nodes import Condition
from core.behavior_tree import Status


class IsSecured(Condition):
    num_args = 1

    def __init__(self, *args):
        super().__init__(*args)
        self.room_id = args[0]

    def update(self) -> Status:
        is_in_predict, is_true = self.check_if_in_predict_condition()
        if is_in_predict:
            return Status.SUCCESS if is_true else Status.FAILURE

        if self.env.has_fluent(f"IsSecured({self.room_id})"):
            return Status.SUCCESS
        return Status.FAILURE
