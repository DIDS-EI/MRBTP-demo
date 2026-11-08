"""
proj4 · VirtualHome 家电协同：异构三人各干各的（中等）—— 参考答案
================================================================================
这是 starter.py 的一份可运行参考实现。建议先独立完成 starter.py 的 TODO。

运行：
    python examples/projects/proj4_vh_appliances/solution/solve.py
    python examples/projects/proj4_vh_appliances/solution/solve.py --headless

实测：规划 ~0.001s / 展开 9 个节点，执行 3 步达成两个目标（确定性）。
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from _run import run_scenario
from app.scenario import Scenario

OBJECTS = ["milk", "fridge", "kitchentable", "tv"]
INIT_STATE = ["IsClose(fridge)", "IsSwitchedOff(tv)"]


def build_scenario() -> Scenario:
    task = {
        "id": "proj4-vh-appliances",
        "objects": OBJECTS,
        # 一人一份能力名单：域按 objects 的类别交集把它们 grounding 成
        # Walk(agent-0,fridge) / Open(agent-0,fridge) / ... 这样的具体动作。
        "action_space": [
            ["Walk", "Open", "Close"],                        # agent-0 开门工
            ["Walk", "SwitchOn", "SwitchOff"],                # agent-1 电器工
            ["Walk", "RightGrab", "RightPut", "RightPutIn"],  # agent-2 搬运工
        ],
        "init_state": INIT_STATE,
        "goal": [
            "IsOpen(fridge)",
            "IsSwitchedOn(tv)",
        ],
    }

    return Scenario(
        name="proj4-vh-appliances",
        env_id="symbolic://virtualhome",
        num_agent=3,
        balls=[],
        goal=frozenset(task["goal"]),
        composite_library=[],
        backend="virtualhome",
        behavior_lib="virtualhome",
        symbolic_task=task,
    )


def main() -> None:
    run_scenario(
        build_scenario,
        theme="home",
        success_msg="成功！开门工打开冰箱、电器工打开电视（搬运工待命）",
        headless="--headless" in sys.argv,
        record_gif="--gif" in sys.argv,
        attempts=1,
        max_steps=60,
    )


if __name__ == "__main__":
    main()
