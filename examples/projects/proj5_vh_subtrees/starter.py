"""
proj5 · VirtualHome 双线搬运：左右手宏子树 + 意图接单（复杂）—— 你的练习
================================================================================
骨架已搭好，填掉所有 `TODO` 后运行：

    python examples/projects/proj5_vh_subtrees/starter.py
    python examples/projects/proj5_vh_subtrees/starter.py --headless

完整说明见 README.md；卡住了对照 solution/solve.py。

────────────────────────────────────────────────────────────────────────────
三条目标同时要满足：

    1. IsIn(milk,fridge)         agent-0 右手搬运工（5 步链 → 写成宏）
    2. IsIn(apple,microwave)     agent-1 左手搬运工（5 步链 → 写成宏）
    3. IsSwitchedOn(tv)          agent-2 电器工（浅链，自动回链即可）

为什么不直接让规划器回链前两条？`Walk(self,fridge)` 会删掉
`IsNear(self,milk)`，而 `check_conflict` 又禁止一个前提集合里同时出现两个
`IsNear`。把 5 步链写进 `composite_library`，`CompositeActionPlanner` 会先用
CABTP 规划出子树，再把它折叠成一个 cost=0 的动作，主搜索于是一步达成目标。

宏里的 `self` 会被替换成 `agent-i`，所以动作名要和域 grounding 出的名字
逐字一致，例如 `RightPutIn(self,milk,fridge)`。
────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _run import run_scenario
from app.scenario import Scenario

OBJECTS = ["milk", "fridge", "apple", "microwave", "tv", "kitchentable"]
INIT_STATE = ["IsClose(fridge)", "IsClose(microwave)", "IsSwitchedOff(tv)"]


def build_scenario() -> Scenario:
    task = {
        "id": "proj5-vh-subtrees",
        "objects": OBJECTS,

        # TODO(2): 三份异构能力名单（长度必须 == num_agent）。
        #   agent-0: Walk / RightGrab / RightPut / RightPutIn / Open / Close
        #   agent-1: Walk / LeftGrab  / LeftPut  / LeftPutIn  / Open / Close
        #   agent-2: Walk / SwitchOn / SwitchOff / Open / Close
        "action_space": ...,

        "init_state": INIT_STATE,

        # TODO(3): 三个目标谓词（字符串列表）。
        #   IsIn(milk,fridge) / IsIn(apple,microwave) / IsSwitchedOn(tv)
        "goal": ...,
    }

    return Scenario(
        name="proj5-vh-subtrees",
        env_id="symbolic://virtualhome",

        # TODO(1): 两个搬运工 + 一个电器工 = ?
        num_agent=...,

        balls=[],
        goal=frozenset(task["goal"]),

        # TODO(4): 一人一份宏库，长度必须 == num_agent。
        #   agent-0「右手搬运」PutMilkInFridge：
        #     Walk(self,milk) → RightGrab(self,milk) → Walk(self,fridge)
        #     → Open(self,fridge) → RightPutIn(self,milk,fridge)
        #   agent-1「左手搬运」PutAppleInMicrowave：
        #     Walk(self,apple) → LeftGrab(self,apple) → Walk(self,microwave)
        #     → Open(self,microwave) → LeftPutIn(self,apple,microwave)
        #   agent-2 不写宏，留空 {}。
        composite_library=...,

        backend="virtualhome",
        behavior_lib="virtualhome",
        symbolic_task=task,
    )


def main() -> None:
    run_scenario(
        build_scenario,
        theme="home",
        success_msg="成功！牛奶进冰箱、苹果进微波炉、电视打开",
        headless="--headless" in sys.argv,
        record_gif="--gif" in sys.argv,
        attempts=1,
        max_steps=80,
    )


if __name__ == "__main__":
    main()
