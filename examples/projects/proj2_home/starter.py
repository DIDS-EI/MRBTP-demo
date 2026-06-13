"""
proj2 · 家庭整理：摆到锚点旁（进阶）—— 你的练习
================================================================================
骨架已搭好，填掉所有 `TODO` 后运行：

    python examples/projects/proj2_home/starter.py            # 弹出窗口可视化
    python examples/projects/proj2_home/starter.py --headless  # 无头模式

完整说明见 README.md；卡住了对照 solution/solve.py。

────────────────────────────────────────────────────────────────────────────
场景：家庭服务地图 `home`（悬浮花园里的四居室，门都**没锁**）。本题用到的两个
房间直接相邻（共享 door-2）：

    room-1 厨房 ─door-2─ room-3 客厅

任务：把厨房 room-1 的杯子（绿球）搬到**相邻**的客厅 room-3，
**摆在收纳篮（红球）旁边**。
知识点：新谓词 `IsNear(a,b)` + 新动作 `PutNearInRoom(self,物体,锚点,房间)`——
        目标是"挨着锚点"，不再是"进某房间"。收纳篮 ball-1(红) 就是锚点。

> 窗口里能看到厨房的冰箱 / 灶台、客厅的沙发 / 电视——这些家具是渲染元数据，
> 规划器看不见，纯粹帮你认出"这是客厅"。
────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _run import run_scenario
from app.scenario import Scenario
from scenes import home_service as home


def build_scenario() -> Scenario:
    return Scenario(
        name="proj2-home",
        env_id=home._home_map.ENV_ID,
        num_agent=2,

        # TODO(1): 放两个球——杯子(绿)在厨房 room-1，收纳篮(红)在客厅 room-3。
        #   顺序决定编号：先写的是 ball-0，后写的是 ball-1。
        balls=...,

        # TODO(2): 目标——杯子(ball-0)挨着收纳篮(ball-1)。
        #   用新谓词：IsNear(ball-0,ball-1)
        goal=frozenset({
            ...,
        }),

        # TODO(3): agent-0 的宏：去 room-1 捡杯子 → 跨一跳到 room-3 →
        #   用 PutNearInRoom 摆到收纳篮旁。agent-1 给空 {} 占位。
        #   厨房 room-1 与客厅 room-3 直接相邻（共享 door-2），一跳即可。
        #   新动作：PutNearInRoom(self, 要放的物体, 锚点物体, 房间)
        composite_library=[
            {...},
            {},
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
        success_msg="成功！把杯子摆到了客厅的收纳篮旁",
        headless=headless,
        record_gif=record_gif,
        gif_path="app/output/projects/proj2_home.gif",
    )


if __name__ == "__main__":
    main()
