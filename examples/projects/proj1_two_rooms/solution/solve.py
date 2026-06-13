"""
proj1 · 跨房间搬运（基础）—— 参考答案
================================================================================
这是 starter.py 的一份可运行参考实现。建议先独立完成 starter.py 的 TODO，
卡住了再来对照这里。

场景：家庭服务地图 `home`（悬浮在花园里的四居室，门都**没锁**）。室内房间各自
只通过一道门连到室外花园，本题用到的相邻对是：花园 room-0 ─door-0─ 厨房 room-1。

任务：把**室外花园 room-0** 的绿球搬进**相邻**的**厨房 room-1**（只跨一道门 = 1 跳）。
思路：一人搬球就够，但本 demo 的任务分配机制要求**至少 2 个机器人**，所以
      第二个机器人给一份空宏库（没活干，但必须占位）。

> 三个项目都不用钥匙——门都不上锁。难度靠「搬几跳 / 用什么谓词 / 几人协作」
> 递进。规划开销随「目标数 × 跳数 × 房间大小」增长，所以每个项目都只设**一个
> 短目标**，保证秒级规划。

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
from scenes import home_service as home


def build_scenario() -> Scenario:
    return Scenario(
        name="proj1-two-rooms",
        env_id=home._home_map.ENV_ID,
        num_agent=2,
        # 绿球丢在室外花园 room-0，自动编号 ball-0。
        balls=[("green", 0)],
        # 目标只关心"结果状态"：球最终在相邻的厨房 room-1。
        goal=frozenset({
            "IsInRoom(ball-0,room-1)",
        }),
        # 一人一份宏（共 2 份）：搬球的、占位的空宏。
        composite_library=[
            {"MoveBall0": [
                "GoToInRoom(self,ball-0,room-0)",
                "PickUp(self,ball-0)",
                "GoBtwRoom(self,room-0,room-1)",   # 花园→厨房，共享 door-0，一跳
                "PutInRoom(self,ball-0,room-1)",
            ]},
            {},  # agent-1 没活干，但长度必须 == num_agent。
        ],
        unlock_all_doors=True,
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
