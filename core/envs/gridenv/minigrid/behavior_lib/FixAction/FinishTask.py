import copy

from core.behavior_tree.base_nodes import Action
from core.behavior_tree import Status
from minigrid.core.actions import Actions
import random

class FinishTask(Action):
    can_be_expanded = False
    num_args = 0

    def update(self) -> Status:
        self.agent.finish_current_task()

        return Status.FAILURE
