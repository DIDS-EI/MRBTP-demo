# -*- coding: utf-8 -*-
"""home_service · GoToInRoom —— **沿用共享原语，不改规划模型**。

位置无关导航的松绑**只放在 ``GoBtwRoom`` 上**；``GoToInRoom`` 必须保持原样，原因
在执行层：``GoToInRoom.update()`` 的 A* 只做**房间内寻路**（其 ``pre`` 里的
``IsInRoom(agent,room-k)`` 保证 agent 已在目标物体所在房间，从不穿门）。穿门是
``GoBtwRoom`` 的职责。

那 ``GoToInRoom`` 的 ``IsInRoom`` 前置怎么不再触发房间链爆炸？——配合两件事：

1. 同目录 ``GoBtwRoom`` 已松绑成 ``pre = { IsOpen(door) }``（位置无关）；
2. ``unlock_all_doors`` 现在让门**初始即开**（``scenario.py``），``IsOpen(door)`` 直接
   进 start_state。

于是 ``IsInRoom(agent,room-k)`` 由位置无关的 ``GoBtwRoom`` 一步补上、且其唯一前置
``IsOpen`` 初始即满足 → 回链一步即停，不再绕"开门"动作、不再穿越房间链（实测
proj2 规划从 20s 超时降到 ~0.5s）。

本文件只是**显式 re-export 共享版**（与 base 字节等价），位置无关松绑集中在
``GoBtwRoom.py``；proj1 用 base 库，字节级不受影响。
"""
from __future__ import annotations

from core.envs.gridenv.minigrid.behavior_lib.Action.GoToInRoom import (  # noqa: F401
    GoToInRoom,
)
