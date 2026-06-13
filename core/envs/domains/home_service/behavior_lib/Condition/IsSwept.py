"""IsSwept — domain fluent for the *home-service* scene.

``IsSwept(<room>)`` holds once a robot has swept that room's floor.  Like
:class:`IsTidy` it is **not** derivable from grid geometry, so it lives in the
env's additive fluent store (:attr:`MiniGridToMAGridEnv.domain_state`).  The
:class:`Sweep` action sets it once an agent is inside the room; this condition
just reads it back.

Same canonical pattern as every domain predicate: a tiny ``Condition`` that
reads one fluent, paired with an ``Action`` that writes it after the physical
(grid) precondition is met.
"""
from core.behavior_tree.base_nodes import Condition
from core.behavior_tree import Status


class IsSwept(Condition):
    num_args = 1

    def __init__(self, *args):
        super().__init__(*args)
        self.room_id = args[0]

    def update(self) -> Status:
        is_in_predict, is_true = self.check_if_in_predict_condition()
        if is_in_predict:
            return Status.SUCCESS if is_true else Status.FAILURE

        if self.env.has_fluent(f"IsSwept({self.room_id})"):
            return Status.SUCCESS
        return Status.FAILURE
