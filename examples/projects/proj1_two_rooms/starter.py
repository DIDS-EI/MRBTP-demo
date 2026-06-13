"""
proj1 · 跨房间搬运（基础）—— 你的练习
================================================================================
这是你的第一个小项目。骨架已经搭好，凡是写着 `TODO` 的地方就是留给你填的。
填完后直接运行：

    python examples/projects/proj1_two_rooms/starter.py            # 弹出窗口可视化
    python examples/projects/proj1_two_rooms/starter.py --headless  # 无头模式

完整说明见同目录的 README.md；卡住了可对照 solution/solve.py。

────────────────────────────────────────────────────────────────────────────
场景：家庭服务地图 `home`（一栋悬浮在花园里的四居室，门都**没锁**）。
室内四个房间各自只通过一道门连到室外花园，相邻关系是：

    room-0 室外花园 ─door-0─ room-1 厨房
                    └─door-2─ room-3 客厅 ...（其余房间见 README）

任务：把散落在**室外花园 room-0** 的绿球搬进**相邻**的**厨房 room-1**
（只跨一道门 = 1 跳）。
提示：一人搬球就够，但任务分配机制要求**至少 2 个机器人**，第二个给空宏库占位。

> 这一版练习用的就是仓库成品场景 `home` 的同款独立地图——所以窗口里能看到
> 中文房间名、冰箱 / 沙发 / 床等家具，和 `python -m app.run --scenario home
> --renderer pygame` 跑出来的画面完全一致。家具是渲染元数据，规划器看不见。
────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations

import sys
from pathlib import Path

# 把仓库根加入 import 路径（细节封装在 examples/projects/_run.py）。
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _run import run_scenario
from app.scenario import Scenario
# 直接复用成品场景 `home` 的独立地图 + 房间中文别名 + 家具元数据。
from scenes import home_service as home


def build_scenario() -> Scenario:
    return Scenario(
        name="proj1-two-rooms",
        # home 场景专属的独立地图 gym id（含花园 / 厨房 / 客厅 / 卧室 / 卫生间）。
        env_id=home._home_map.ENV_ID,

        # TODO(1): 这个任务需要几个机器人？（搬球 1 人，但最少要 2 个）
        num_agent=...,

        # TODO(2): 往室外花园 room-0 放一个绿球。格式 [(颜色, 房间号), ...]，
        #   自动编号 ball-0。
        balls=...,

        # TODO(3): 写出目标谓词集合——"绿球最终在厨房 room-1"。
        #   语法示例：IsInRoom(ball-0,room-1)
        goal=frozenset({
            ...,
        }),

        # TODO(4): 一人一份宏动作库（长度必须 == num_agent）。
        #   agent-0 搬球；agent-1 没活干，给空 {} 占位。
        #   花园 room-0 与厨房 room-1 直接相邻（共享 door-0），所以一跳即可。
        #   常用原子动作：
        #     GoToInRoom(self, 物体, 房间)  PickUp(self, 物体)
        #     GoBtwRoom(self, 起房, 终房)   PutInRoom(self, 物体, 房间)
        composite_library=[
            # —— agent-0：把 ball-0 从花园 room-0 搬进厨房 room-1 ——
            # TODO(4a): 仿照 README 的范例，写出搬 ball-0 的 4 步宏。
            {...},
            # —— agent-1：没活干 ——
            {},
        ],

        # 门都不上锁：保留多房间分隔，但谁都能开门。
        unlock_all_doors=True,
        # 渲染元数据：房间中文名 + 家具，直接复用 home 场景的声明（规划器看不见）。
        room_aliases=home.ROOM_ALIASES,
        decor=home.DECOR,
        seed=0,
    )


def main() -> None:
    headless = "--headless" in sys.argv
    record_gif = "--gif" in sys.argv
    run_scenario(
        build_scenario,
        theme=home.THEME,
        success_msg="成功！把绿球搬进了相邻的厨房 room-1",
        headless=headless,
        record_gif=record_gif,
        gif_path="app/output/projects/proj1_two_rooms.gif",
    )


if __name__ == "__main__":
    main()
