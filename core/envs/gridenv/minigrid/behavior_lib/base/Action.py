from core.behavior_tree.base_nodes.BehaviorNode import BehaviorNode
from core.utils.tools import print_colored
from core.behavior_tree import Status
from core.behavior_tree.base_nodes import Action
class MinigridAction(Action):
    can_be_expanded = False

    def check_if_pre_in_predict_condition(self):

        act_pre = self.env.blackboard["action_pre"][self.name]

        # wait pre
        wait_cond = (act_pre & self.agent.predict_condition['success'])
        if  wait_cond!=set():
            if self.env.verbose: print_colored(f"{self.name}  Total Wait:{act_pre & self.agent.predict_condition['success']}",color="purple")
            return True

    # ------------------------------------------------------------------ #
    # 「最后一公里进房」共享 helper —— 房间级 domain 动作专用                  #
    # ------------------------------------------------------------------ #
    def reach_room_interior(self, room_index) -> bool:
        """把 agent 从房间门口真正带进房间内核，解决一处判定口径死锁。

        背景（房间级动作 Sweep/Tidy/Fortify/Secure/Scout/Suppress 的共同坑）：
        回链出的导航子树形如 ``Selector[ IsInRoom(agent,room-k)? , GoBtwRoom ]``。
        ``IsInRoom`` 对**门格**有特判——站在连接 room-k 的门上就算「已在 room-k」
        并返回 SUCCESS，于是 Selector 短路、``GoBtwRoom`` 停止推进，agent 被撂在
        门口。但房间级动作的 ``update()`` 用严格的 ``get_room_index(pos)==k`` 判定，
        而门格 ``get_room_index`` 返回 -1≠k → 判定「还没到」→ 原地 idle 等导航 →
        导航又认为「已到」不动 → **死锁**（实测卡满步数）。物体级动作走 GoToInRoom
        到房间内部物体坐标、从不停在门格，所以不受影响。

        本 helper 让房间级动作**自带最后一公里导航**：被撂在门口时，自己用 A* 朝
        房间内离当前最近的空格走一步，直到 ``get_room_index`` 真正等于 room_index。

        Returns:
            True  —— agent 当前格已在 room_index 内核，调用方可安全 flip fluent。
            False —— 尚未进入；本 helper 已设置好本 tick 的移动动作，调用方应 idle
                     返回 ``Status.RUNNING``，下一 tick 再判。
        """
        from core.utils.astar import astar
        from core.envs.gridenv.minigrid.utils import get_direction_index
        from minigrid.core.actions import Actions

        pos = tuple(int(x) for x in self.agent.position)
        if self.env.get_room_index(pos) == room_index:
            return True

        # 选房间内「离当前最近且 A* 可达」的空格作为推进目标，首次选定后缓存，
        # 避免每 tick 重选导致目标抖动；目标失效（被占/换房）时才重选。
        goal = getattr(self, "_interior_goal", None)
        if goal is None or self.env.get_room_index(goal) != room_index \
                or self.env.grid.get(goal[0], goal[1]) is not None:
            best, best_len = None, None
            for (cx, cy) in self.env.room_cells[room_index]:
                if self.env.grid.get(cx, cy) is not None:
                    continue  # 跳过被物体/门占用的格
                p = astar(self.env.grid, start=pos, goal=(cx, cy))
                if p is not None and (best_len is None or len(p) < best_len):
                    best, best_len = (cx, cy), len(p)
            self._interior_goal = best
            goal = best

        if goal is None:  # 房间内无可达空格（极端情形）：原地等待
            self.agent.action = Actions.done
            return False

        path = astar(self.env.grid, start=pos, goal=goal)
        if not path:  # None（不可达）或 []（已在 goal 却仍判不在内核）：等待
            self.agent.action = Actions.done
            return False

        # 朝 path 第一步转向 / 前进一步。
        direction_int = get_direction_index(path[0])
        diff = (direction_int - self.agent.direction) % 4
        if diff == 0:
            self.agent.action = Actions.forward
        elif diff == 3:
            self.agent.action = Actions.left
        else:
            self.agent.action = Actions.right
        return False
