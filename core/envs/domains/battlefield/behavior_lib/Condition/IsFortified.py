"""IsFortified — domain fluent for the *battlefield* scene.

``IsFortified(<room>)`` holds once a unit has built defensive works in a
stronghold.  Symbolic fluent in :attr:`MiniGridToMAGridEnv.domain_state`, set by
the :class:`Fortify` action.  It is an *independent* objective (no dependency on
the scout/suppress/secure chain), so the planner can assign it to a spare unit
in parallel with the tactical chain.
"""
from core.behavior_tree.base_nodes import Condition
from core.behavior_tree import Status


class IsFortified(Condition):
    num_args = 1

    def __init__(self, *args):
        super().__init__(*args)
        self.room_id = args[0]

    def update(self) -> Status:
        is_in_predict, is_true = self.check_if_in_predict_condition()
        if is_in_predict:
            return Status.SUCCESS if is_true else Status.FAILURE

        if self.env.has_fluent(f"IsFortified({self.room_id})"):
            return Status.SUCCESS
        return Status.FAILURE
