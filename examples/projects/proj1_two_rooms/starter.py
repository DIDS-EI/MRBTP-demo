"""
proj1 · 原生 MiniGrid · 带钥匙开门的三人协作搬运（基础）—— 你的练习
================================================================================
这是你的第一个小项目。骨架已经搭好，凡是写着 `TODO` 的地方就是留给你填的。
填完后直接运行：

    python examples/projects/proj1_two_rooms/starter.py            # 弹出窗口可视化
    python examples/projects/proj1_two_rooms/starter.py --headless  # 无头模式

完整说明见同目录的 README.md；卡住了可对照 solution/solve.py。

────────────────────────────────────────────────────────────────────────────
场景：**MiniGrid 原生 DoorKey-16x16 环境**（不是自建语义地图！），用**纯原生
行为库**（不挂任何 domain 专属库）。这是三个项目里最朴素的一个，先把「钥匙—门
—搬运」这套最基础的网格原语吃透：

    ┌──────────────┬──────────────┐
    │   room-0     ║   room-1     │     ║ = 一道**上锁**的门 door-0
    │ (钥匙+两球)   ║  (目标房)     │     钥匙 key-0 也在 room-0
    └──────────────┴──────────────┘

任务：room-0 里有一把钥匙、两个球（绿 ball-0、蓝 ball-1），门 door-0 **上锁**。
三人小队要把两个球都搬进 room-1。这逼出一个天然的**异构三人分工**：

    * agent-0「开门工」：取钥匙 → 走到门 → 开锁开门。
    * agent-1「搬运工A」：把绿球 ball-0 搬进 room-1（要等门开）。
    * agent-2「搬运工B」：把蓝球 ball-1 搬进 room-1（要等门开）。

三个 agent 的宏库**各不相同**——这就是「每个 agent 动作空间各异」的落点。

> 注意：proj1 **不** unlock_all_doors，门是真上锁的——没人开门，搬运工进不去。
> 这才是 DoorKey 环境的本意，也是「原生态」三个字的分量。
────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations

import sys
from pathlib import Path

# 把仓库根加入 import 路径（细节封装在 examples/projects/_run.py）。
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _run import run_scenario
from app.scenario import Scenario


def build_scenario() -> Scenario:
    return Scenario(
        name="proj1-two-rooms",
        # MiniGrid 官方原生环境：一把钥匙 + 一道上锁的门，两个房间。
        env_id="MiniGrid-DoorKey-16x16-v0",

        # TODO(1): 这个任务要几个机器人？（开门 1 人 + 搬两个球 2 人 = 3）
        num_agent=...,

        # TODO(2): 往 room-0 放两个球：绿、蓝。格式 [(颜色, 房间号), ...]，
        #   先写的是 ball-0，后写的是 ball-1。钥匙 key-0 由 DoorKey 环境自带。
        balls=...,

        # TODO(3): 目标——两个球都进 room-1。
        #   语法示例：IsInRoom(ball-0,room-1)
        goal=frozenset({
            ...,
        }),

        # TODO(4): 三人各一份**不同**的宏库（长度必须 == num_agent）。
        #   常用原子动作：
        #     GoToInRoom(self, 物体, 房间)   PickUp(self, 物体)
        #     Toggle(self, 门)               GoBtwRoom(self, 起房, 终房)
        #     PutInRoom(self, 物体, 房间)
        composite_library=[
            # —— agent-0「开门工」：取钥匙 → 走到门 door-0 → Toggle 开门 ——
            # TODO(4a): 写出 取 key-0 → 走到 door-0 → Toggle 的 4 步宏。
            {...},
            # —— agent-1「搬运工A」：搬绿球 ball-0 进 room-1 ——
            # TODO(4b): 写出 取 ball-0 → 跨房 → 放进 room-1 的 4 步宏。
            {...},
            # —— agent-2「搬运工B」：搬蓝球 ball-1 进 room-1 ——
            # TODO(4c): 同上，但搬的是 ball-1。
            {...},
        ],

        # proj1 用原生地图 + 原生库：不设 behavior_lib（默认原生），也不
        # unlock_all_doors——门真上锁，必须靠开门工取钥匙。
        seed=0,
    )


def main() -> None:
    headless = "--headless" in sys.argv
    record_gif = "--gif" in sys.argv
    run_scenario(
        build_scenario,
        theme="default",
        success_msg="成功！开门工取钥匙开锁，两名搬运工把绿球和蓝球都搬进了 room-1",
        headless=headless,
        record_gif=record_gif,
        gif_path="app/output/projects/proj1_two_rooms.gif",
    )


if __name__ == "__main__":
    main()
