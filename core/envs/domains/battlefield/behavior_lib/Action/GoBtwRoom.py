# -*- coding: utf-8 -*-
"""battlefield 专属·**位置无关**版 GoBtwRoom（覆盖共享原语）。

=== 为什么要覆盖 ===
共享版 ``GoBtwRoom`` 把 ``IsInRoom(agent,room-from)`` 写进 ``pre``，要求动作开始时
agent 必须已经站在 from_room。battlefield 是**星型**拓扑（三据点彼此不相邻，都只通
开阔区 room-0），agent 随机出生——出生据点 ≠ 目标据点时，规划器必须用一串
``GoBtwRoom`` 经 room-0 中转补房间链，分支因子相乘 → 节点指数爆炸 → 20s 超时 →
BT root FAILURE。proj3 的无宏 agent（突击兵 ``Scout→Suppress→Secure``、工兵
``Fortify``）回链到 ``IsInRoom(room-k)`` 时尤其会触发这条爆炸链。

=== 这版怎么解 ===
执行层 ``update()`` 用从 agent 当前位置出发的全局 A*（见父类），本就能跨任意据点
直达——"先在 from_room"纯属规划模型的人为约束。拿掉它：

    pre = { IsOpen(door) }                      # 闸口开着，从任何位置都能到（star 拓扑都未锁）
    add = { IsInRoom(agent-i, room-to) }
    del = { IsInRoom(agent-i, 其它所有据点), IsNear(agent-i, *) }

回链找"谁产出 ``IsInRoom(agent,room-k)``"时，候选 pre 只剩初始即满足的
``IsOpen(door)``（``unlock_all_doors=True``）→ **回链一步即停**，不再穿越据点链。

仅覆盖 battlefield 库（overlay：``[minigrid_root, domain_root]`` 同名文件后者胜）；
proj1 用 base 库，字节级不受影响。
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
        # ★ 位置无关：删去 IsInRoom(agent,room-from)，只要闸口开即可从任意位置直达。
        action_model["pre"] = {f"IsOpen({door_id})"}
        action_model["add"] = {f"IsInRoom(agent-{agent_id},room-{to_room_id})"}
        action_model["del_set"] = {
            f"IsInRoom(agent-{agent_id},room-{rid})"
            for rid in range(room_num) if rid != to_room_id
        }
        action_model["del_set"] |= {
            f"IsNear(agent-{agent_id},{obj})" for obj in can_goto
        }
        action_model["cost"] = 1
        return action_model
