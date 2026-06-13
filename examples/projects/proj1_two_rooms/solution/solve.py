"""
proj1 · 原生 MiniGrid · 带钥匙开门的三人协作搬运（基础）—— 参考答案
================================================================================
这是 starter.py 的一份可运行参考实现。建议先独立完成 starter.py 的 TODO，
卡住了再来对照这里。

场景：**MiniGrid 原生 DoorKey-16x16 环境**（不是自建语义地图！）。
------------------------------------------------------------------------------
proj1 刻意回到 MiniGrid 最原汁原味的官方环境，用**纯原生行为库**（不挂任何
domain 专属库），让你先把「钥匙—门—搬运」这套最基础的网格原语吃透：

    ┌──────────────┬──────────────┐
    │              │              │
    │   room-0     ║   room-1     │     ║ = 一道**上锁**的门 door-0
    │  (钥匙+球)    ║   (目标房)    │     钥匙 key-0 也在 room-0
    │              │              │
    └──────────────┴──────────────┘

和 proj2 / proj3 的对比（这正是三个项目「各不相同」的设计主线）：

    proj1：原生地图  + 原生库（无 domain）        —— 钥匙/门/搬运
    proj2：home 地图 + home_service 专属库         —— 清洁/整理/归置
    proj3：battle 地图 + battlefield 专属库        —— 侦察/压制/占领

任务：room-0 里有一把钥匙、两个球（绿、蓝）；门 door-0 **上锁**。三人小队要把
两个球都搬进 room-1。这逼出一个天然的**异构三人分工**：

    * agent-0「开门工」：取钥匙 key-0 → 走到门 door-0 → 开锁开门。
    * agent-1「搬运工A」：把绿球 ball-0 搬进 room-1（要等门开）。
    * agent-2「搬运工B」：把蓝球 ball-1 搬进 room-1（要等门开）。

三个 agent 的宏库（动作序列）**各不相同**——这就是「per-agent 动作空间各异」在
本框架里的真正落点：底层原子动作大家共享，但每人预置的多步宏不一样。

> 注意：proj1 **不再** `unlock_all_doors`，门是真上锁的——必须有人先取钥匙开门，
> 否则搬运工永远进不去。这才是 DoorKey 环境的本意，也是「原生态」三个字的分量。

运行：
    python examples/projects/proj1_two_rooms/solution/solve.py            # 弹出窗口可视化
    python examples/projects/proj1_two_rooms/solution/solve.py --headless  # 无头模式
"""
from __future__ import annotations

import sys
from pathlib import Path

# solution/ 比 starter 多一层，仓库根在 parents[2]；把它加进 import 路径。
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from _run import run_scenario
from app.scenario import Scenario


def build_scenario() -> Scenario:
    return Scenario(
        name="proj1-two-rooms",
        # MiniGrid 官方原生环境：一把钥匙 + 一道上锁的门，两个房间。
        env_id="MiniGrid-DoorKey-16x16-v0",
        num_agent=3,
        # room-0 里放两个要搬的球：绿(ball-0)、蓝(ball-1)。钥匙 key-0 由 DoorKey
        # 环境自带，已经在 room-0。
        balls=[("green", 0), ("blue", 0)],
        # 目标：两个球都进 room-1。
        goal=frozenset({
            "IsInRoom(ball-0,room-1)",
            "IsInRoom(ball-1,room-1)",
        }),
        # 三人各一份**不同**的宏库（长度必须 == num_agent）。
        composite_library=[
            # —— agent-0「开门工」：取钥匙 → 走到门 → 开锁开门 ——
            {"GetKeyAndOpenDoor": [
                "GoToInRoom(self,key-0,room-0)",
                "PickUp(self,key-0)",
                "GoToInRoom(self,door-0,room-0)",
                "Toggle(self,door-0)",
            ]},
            # —— agent-1「搬运工A」：搬绿球 ball-0 进 room-1 ——
            {"MoveGreenBall": [
                "GoToInRoom(self,ball-0,room-0)",
                "PickUp(self,ball-0)",
                "GoBtwRoom(self,room-0,room-1)",
                "PutInRoom(self,ball-0,room-1)",
            ]},
            # —— agent-2「搬运工B」：搬蓝球 ball-1 进 room-1 ——
            {"MoveBlueBall": [
                "GoToInRoom(self,ball-1,room-0)",
                "PickUp(self,ball-1)",
                "GoBtwRoom(self,room-0,room-1)",
                "PutInRoom(self,ball-1,room-1)",
            ]},
        ],
        # proj1 用原生地图 + 原生库：不挂 domain（behavior_lib=None），门真上锁
        # （不 unlock_all_doors）——必须靠 agent-0 取钥匙开门。
        seed=0,
    )


def main() -> None:
    headless = "--headless" in sys.argv
    record_gif = "--gif" in sys.argv
    run_scenario(
        build_scenario,
        # 原生 DoorKey 没有专属配色主题，用 default 即可（灰底网格 + 彩色球/门）。
        theme="default",
        success_msg="成功！开门工取钥匙开锁，两名搬运工把绿球和蓝球都搬进了 room-1",
        headless=headless,
        record_gif=record_gif,
        gif_path="app/output/projects/proj1_two_rooms.gif",
    )


if __name__ == "__main__":
    main()
