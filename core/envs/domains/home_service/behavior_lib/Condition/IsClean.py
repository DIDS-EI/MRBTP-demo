"""IsClean — domain fluent for the *home-service* scene.

``IsClean(<obj>)`` holds once a robot has wiped the object clean.  It is **not**
derivable from grid geometry, so it lives in the env's additive fluent store
(:attr:`MiniGridToMAGridEnv.domain_state`).  The :class:`Wipe` action sets it
once an agent is next to the object; this condition just reads it back.

This is the canonical pattern for *every* domain-specific predicate: a tiny
``Condition`` that reads one fluent, paired with an ``Action`` that writes it
after the physical (grid) precondition is met.  A robot-simulator backend keeps
the same predicate contract, only sourcing the truth value from real sensors.
"""
from core.behavior_tree.base_nodes import Condition
from core.behavior_tree import Status


class IsClean(Condition):
    num_args = 1

    def __init__(self, *args):
        super().__init__(*args)
        self.obj_id = args[0]

    def update(self) -> Status:
        # Honour the planner's hypothesis space first (same protocol every
        # grid condition uses), then fall back to the real fluent store.
        is_in_predict, is_true = self.check_if_in_predict_condition()
        if is_in_predict:
            return Status.SUCCESS if is_true else Status.FAILURE

        if self.env.has_fluent(f"IsClean({self.obj_id})"):
            return Status.SUCCESS
        return Status.FAILURE
