"""IsSelfTask(task_id,action,sub_goal,sub_del) —— 是否已接下这段宏子树。"""
from core.envs.domains.virtualhome import nodes


class IsSelfTask(nodes.TaskFlagCondition):
    pass
