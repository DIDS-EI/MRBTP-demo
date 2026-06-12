import py_trees as ptree
from core.behavior_tree.base_nodes.BehaviorNode import BehaviorNode, Status

class Condition(BehaviorNode):
    print_name_prefix = "condition "
    type = 'Condition'

    def __init__(self,*args):
        super().__init__(*args)

    def check_if_in_predict_condition(self):

        if self.name in self.agent.predict_condition['success']:
            return True,True

        if self.name in self.agent.predict_condition['fail']:
            return True,False

        return False, False  # 确保总是返回两个值
