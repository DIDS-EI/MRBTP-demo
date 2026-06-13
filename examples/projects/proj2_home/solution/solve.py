"""
proj2 · 家庭整理：摆到锚点旁（进阶）—— 参考答案
================================================================================
这是 starter.py 的一份可运行参考实现。建议先独立完成 starter.py 的 TODO。

场景：家庭服务地图 `home`（四居室，门都**没锁**）。本题用相邻的两个房间：
厨房 room-1 ─door-2─ 客厅 room-3。

任务：把厨房 room-1 的杯子（绿球）搬到**相邻**的客厅 room-3，**摆在收纳篮
（红球）旁边**。
知识点：本项目用全新谓词 `IsNear` + 动作 `PutNearInRoom`——目标不再是"进某房间"，
        而是"挨着某个锚点物体"。收纳篮（ball-1，红）就是锚点。

运行：
    python examples/projects/proj2_home/solution/solve.py            # 弹出窗口可视化
    python examples/projects/proj2_home/solution/solve.py --headless  # 无头模式
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from _run import run_scenario
from app.scenario import Scenario
from scenes import home_service as home


def build_scenario() -> Scenario:
    return Scenario(
        name="proj2-home",
        env_id=home._home_map.ENV_ID,
        num_agent=2,
        # ball-0(绿)=杯子在厨房 room-1；ball-1(红)=收纳篮锚点在客厅 room-3。
        balls=[("green", 1), ("red", 3)],
        # 目标：杯子挨着收纳篮（而不是简单地"进 room-3"）。
        goal=frozenset({
            "IsNear(ball-0,ball-1)",
        }),
        composite_library=[
            {"TidyCupToBasket": [
                "GoToInRoom(self,ball-0,room-1)",
                "PickUp(self,ball-0)",
                "GoBtwRoom(self,room-1,room-3)",   # 厨房→客厅，共享 door-2，一跳
                "PutNearInRoom(self,ball-0,ball-1,room-3)",
            ]},
            {},  # agent-1 占位空宏。
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
