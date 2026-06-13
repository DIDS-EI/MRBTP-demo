"""IsStocked — domain fluent for the *home-service* scene.

``IsStocked(<obj>)`` holds once a robot has put an item away into storage.
Symbolic fluent in :attr:`MiniGridToMAGridEnv.domain_state`, set by the
:class:`Stock` action.  Stocking requires the item to be in hand first, which
the planner enforces through :class:`Stock`'s precondition on ``IsHolding`` —
giving the home domain a genuine two-step (pick-up -> stock) plan.
"""
from core.behavior_tree.base_nodes import Condition
from core.behavior_tree import Status


class IsStocked(Condition):
    num_args = 1

    def __init__(self, *args):
        super().__init__(*args)
        self.obj_id = args[0]

    def update(self) -> Status:
        is_in_predict, is_true = self.check_if_in_predict_condition()
        if is_in_predict:
            return Status.SUCCESS if is_true else Status.FAILURE

        if self.env.has_fluent(f"IsStocked({self.obj_id})"):
            return Status.SUCCESS
        return Status.FAILURE
