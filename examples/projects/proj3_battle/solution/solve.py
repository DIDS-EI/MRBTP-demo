"""
proj3 · 战场补给：跨多个房间（挑战）—— 参考答案
================================================================================
这是 starter.py 的一份可运行参考实现。建议先独立完成 starter.py 的 TODO。

场景：战场补给地图 `battle`（星型拓扑，三据点各只通开阔区，闸口都**没锁**）：

    room-1 蓝方基地 ─door-0─┐
    room-2 红方基地 ─door-1─┤ room-0 开阔交火区
    room-3 中央据点 ─door-2─┘

任务：把蓝方基地 room-1 的弹药箱（绿球）运到中央据点 room-3——两据点不相邻，
必须经开阔区 room-0 中转（跨 2 道闸口）。
知识点：跨多跳移动要拆成**逐段相邻**的 GoBtwRoom：room-1→room-0、room-0→room-3。
        一步从 room-1 跨到 room-3 没有对应的行动模型（GoBtwRoom 只为共享一道门
        的相邻房间对生成动作），规划会失败。

运行：
    python examples/projects/proj3_battle/solution/solve.py            # 弹出窗口可视化
    python examples/projects/proj3_battle/solution/solve.py --headless  # 无头模式
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from _run import run_scenario
from app.scenario import Scenario
from scenes import battlefield as battle


def build_scenario() -> Scenario:
    return Scenario(
        name="proj3-battle",
        env_id=battle._battle_map.ENV_ID,
        num_agent=2,
        # 弹药箱（绿球）在蓝方基地 room-1。
        balls=[("green", 1)],
        # 目标：弹药运抵中央据点 room-3（经开阔区中转，跨 2 道闸口）。
        goal=frozenset({
            "IsInRoom(ball-0,room-3)",
        }),
        composite_library=[
            {"DeliverAmmoToOutpost": [
                "GoToInRoom(self,ball-0,room-1)",
                "PickUp(self,ball-0)",
                "GoBtwRoom(self,room-1,room-0)",   # 第 1 跳：蓝方基地→开阔区
                "GoBtwRoom(self,room-0,room-3)",   # 第 2 跳：开阔区→中央据点
                "PutInRoom(self,ball-0,room-3)",
            ]},
            {},  # agent-1 占位空宏。
        ],
        unlock_all_doors=True,
        room_aliases=battle.ROOM_ALIASES,
        decor=battle.DECOR,
        seed=0,
    )


def main() -> None:
    headless = "--headless" in sys.argv
    record_gif = "--gif" in sys.argv
    run_scenario(
        build_scenario,
        theme=battle.THEME,
        success_msg="成功！把弹药经开阔区中转、跨 2 道闸口运到了中央据点 room-3",
        headless=headless,
        record_gif=record_gif,
        gif_path="app/output/projects/proj3_battle.gif",
    )


if __name__ == "__main__":
    main()
