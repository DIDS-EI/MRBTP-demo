# -*- coding: utf-8 -*-
"""home_service 专属·**位置无关**版 GoBtwRoom（覆盖共享原语）。

=== 为什么要覆盖 ===
共享版 ``GoBtwRoom`` 的规划模型把 ``IsInRoom(agent,room-from)`` 写进了 ``pre``：

    pre = { IsInRoom(agent-i, room-from), IsOpen(door) }

这要求"动作开始时 agent 必须已经站在 from_room"。可 agent 是**随机出生**的，
而 home 是 5 房环形拓扑——一旦出生房间 ≠ 宏入口要求的房间，规划器就得用一连串
``GoBtwRoom`` 去"补"房间链（room-4→room-3→room-1→…），每补一格分支因子相乘，
节点指数爆炸，撞上 20s ``max_time_limit`` 超时，吐半成品树 → BT root FAILURE。

=== 这版怎么解 ===
执行层 ``update()`` 用的是从 agent **当前位置**出发的全局 A*（见父类），本来就
能跨任意房间走到目标——"必须先在 from_room"纯粹是规划模型的人为约束。于是这里
把它拿掉：

    pre = { IsOpen(door) }                      # 只要门开，从任何位置都能到
    add = { IsInRoom(agent-i, room-to) }
    del = { IsInRoom(agent-i, 其它所有房间), IsNear(agent-i, *) }

回链找"谁能产出 ``IsInRoom(agent,room-k)``"时，候选动作的 pre 只剩一个初始即满足
的 ``IsOpen(door)``（home 场景 ``unlock_all_doors=True``）——**回链一步即停**，
不再穿越房间链，规划从 20s 超时降到秒级收敛。

只覆盖 home_service 库（overlay 机制：``[minigrid_root, domain_root]`` 同名文件
后者胜），**proj1 用 base 库，字节级不受影响**。
"""
from __future__ import annotations

from core.envs.gridenv.minigrid.behavior_lib.Action.GoBtwRoom import (
    GoBtwRoom as _BaseGoBtwRoom,
)
from core.envs.gridenv.minigrid.planning_action import PlanningAction


class GoBtwRoom(_BaseGoBtwRoom):
    """位置无关版：``pre`` 去掉 ``IsInRoom(from)``，只留 ``IsOpen(door)``。

    执行逻辑（``update`` / ``turn_to``）全部继承父类——只换规划模型。
    """

    @classmethod
    def create_action_model(cls, agent_id, door_id, from_room_id, to_room_id,
                            room_num, can_goto):
        action_model = {}
        # ★ 位置无关：删去 IsInRoom(agent,room-from)，只要门开即可从任意位置直达。
        action_model["pre"] = {f"IsOpen({door_id})"}
        action_model["add"] = {f"IsInRoom(agent-{agent_id},room-{to_room_id})"}
        # 进入 to_room 即"不在其它任何房间"；同时清掉旧的 IsNear（位置变了）。
        action_model["del_set"] = {
            f"IsInRoom(agent-{agent_id},room-{rid})"
            for rid in range(room_num) if rid != to_room_id
        }
        action_model["del_set"] |= {
            f"IsNear(agent-{agent_id},{obj})" for obj in can_goto
        }
        action_model["cost"] = 1
        return action_model
