"""
proj3 · 战场补给：跨多个房间（挑战）—— 你的练习
================================================================================
骨架已搭好，填掉所有 `TODO` 后运行：

    python examples/projects/proj3_battle/starter.py            # 弹出窗口可视化
    python examples/projects/proj3_battle/starter.py --headless  # 无头模式

完整说明见 README.md；卡住了对照 solution/solve.py。

────────────────────────────────────────────────────────────────────────────
场景：战场补给地图 `battle`（开阔交火区上散布三个据点，闸口都**没锁**）。
这张图是**星型**拓扑——三个据点各自只通过一道闸口连到中央的开阔交火区，
据点彼此**不直接相邻**：

    room-1 蓝方基地 ─door-0─┐
    room-2 红方基地 ─door-1─┤ room-0 开阔交火区
    room-3 中央据点 ─door-2─┘

任务：把**蓝方基地 room-1** 的弹药箱（绿球）运到**中央据点 room-3**。
知识点：跨多个房间的连续移动。蓝方基地和中央据点不相邻，所以要经开阔区
        room-0 中转——把跨房拆成**逐跳相邻**的两段：room-1→room-0、room-0→room-3。
        GoBtwRoom 只为「共享一道门的相邻房间对」生成动作，绝不能一步跨两房！

> 窗口里能看到开阔区里的掩体障碍和补给点标记——它们是渲染元数据，一期不影响
> 寻路，规划器看不见。
────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _run import run_scenario
from app.scenario import Scenario
# 直接复用成品场景 `battle` 的独立地图 + 据点中文别名 + 掩体元数据。
from scenes import battlefield as battle


def build_scenario() -> Scenario:
    return Scenario(
        name="proj3-battle",
        env_id=battle._battle_map.ENV_ID,
        num_agent=2,
        # 弹药箱（绿球）在蓝方基地 room-1。
        balls=[("green", 1)],

        # TODO(1): 目标——弹药(ball-0)运抵中央据点 room-3。
        goal=frozenset({
            ...,
        }),

        # TODO(2): agent-0 的宏：捡弹药 → 跨第 1 跳(1→0 经开阔区) →
        #   跨第 2 跳(0→3 进中央据点) → 放进 room-3。
        #   注意 GoBtwRoom 要写**两段相邻**的，不能一步从 room-1 跨到 room-3！
        #   （蓝方基地和中央据点不相邻，必须经开阔区 room-0 中转。）
        #   agent-1 给空 {} 占位。
        composite_library=[
            {...},
            {},
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
