"""
proj5 · VirtualHome 双线搬运：左右手宏子树 + 意图接单（复杂）—— 参考答案
================================================================================
这是 starter.py 的一份可运行参考实现。建议先独立完成 starter.py 的 TODO。

运行：
    python examples/projects/proj5_vh_subtrees/solution/solve.py
    python examples/projects/proj5_vh_subtrees/solution/solve.py --headless

实测：规划 ~0.43s / 展开 759 个节点，执行 12 步达成三个目标（确定性）。
把 composite_library 改成 [{}, {}, {}] 可关掉宏做对照：约 1.35s /
展开 1474 个节点、执行 8 步。
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from _run import run_scenario
from app.scenario import Scenario

OBJECTS = ["milk", "fridge", "apple", "microwave", "tv", "kitchentable"]
INIT_STATE = ["IsClose(fridge)", "IsClose(microwave)", "IsSwitchedOff(tv)"]


def build_scenario() -> Scenario:
    task = {
        "id": "proj5-vh-subtrees",
        "objects": OBJECTS,
        "action_space": [
            # agent-0：右手搬运工
            ["Walk", "RightGrab", "RightPut", "RightPutIn", "Open", "Close"],
            # agent-1：左手搬运工（左右手状态彼此独立）
            ["Walk", "LeftGrab", "LeftPut", "LeftPutIn", "Open", "Close"],
            # agent-2：电器工，只管把电视打开
            ["Walk", "SwitchOn", "SwitchOff", "Open", "Close"],
        ],
        "init_state": INIT_STATE,
        "goal": [
            "IsIn(milk,fridge)",
            "IsIn(apple,microwave)",
            "IsSwitchedOn(tv)",
        ],
    }

    composite_library = [
        {"PutMilkInFridge": [
            "Walk(self,milk)",             # 站到牛奶旁
            "RightGrab(self,milk)",        # 右手拿起
            "Walk(self,fridge)",           # 走到冰箱（会删掉旧的 IsNear）
            "Open(self,fridge)",           # 冰箱可开合，放东西前必须打开
            "RightPutIn(self,milk,fridge)",
        ]},
        {"PutAppleInMicrowave": [
            "Walk(self,apple)",
            "LeftGrab(self,apple)",
            "Walk(self,microwave)",
            "Open(self,microwave)",
            "LeftPutIn(self,apple,microwave)",
        ]},
        {},                                # agent-2 不写宏：IsSwitchedOn 自动回链
    ]

    return Scenario(
        name="proj5-vh-subtrees",
        env_id="symbolic://virtualhome",
        num_agent=3,
        balls=[],
        goal=frozenset(task["goal"]),
        composite_library=composite_library,
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
