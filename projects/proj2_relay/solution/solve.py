"""
proj2 · 接力开门搬运 —— 参考答案
================================================================================
任务：只有 **2 个机器人**，却要完成 **3 件事**——开门 + 搬 ball-0 + 搬 ball-1。
所以必须有人"身兼两职"：agent-0 先开门，再接着去搬一个球。

这正是 composite_library 的一个关键点：**一份宏库里可以放多个宏**，
规划器会把它们都派给同一个机器人，按需要的顺序展开。

运行：
    python projects/proj2_relay/solution/solve.py            # 带窗口可视化
    python projects/proj2_relay/solution/solve.py --headless  # 无头模式
"""
from __future__ import annotations

import os
import sys

# 只有显式 --headless 时才把 pygame 切到 dummy 驱动（不开窗口）。
HEADLESS = "--headless" in sys.argv
if HEADLESS:
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import random

from mrbtp_demo.scenario import Scenario
from mrbtp_demo.planner import plan_behavior_trees
from mrbtp_demo.executor import execute
from mrbtp_demo.visualize import Visualizer


def build_scenario() -> Scenario:
    return Scenario(
        name="proj2-relay",
        env_id="MiniGrid-DoorKey-8x8-v0",
        num_agent=2,
        balls=[("green", 0), ("purple", 0)],
        goal=frozenset({
            "IsInRoom(ball-0,room-1)",
            "IsInRoom(ball-1,room-1)",
        }),
        composite_library=[
            # —— agent-0：开门 + 搬 ball-0（一份库里两个宏 = 身兼两职）——
            {
                "GetKeyAndOpenDoor": [
                    "GoToInRoom(self,key-0,room-0)",
                    "PickUp(self,key-0)",
                    "GoToInRoom(self,door-0,room-0)",
                    "Toggle(self,door-0)",
                ],
                "MoveBall0": [
                    "GoToInRoom(self,ball-0,room-0)",
                    "PickUp(self,ball-0)",
                    "GoBtwRoom(self,room-0,room-1)",
                    "PutInRoom(self,ball-0,room-1)",
                ],
            },
            # —— agent-1：搬 ball-1（依赖 agent-0 先把门打开）——
            {
                "MoveBall1": [
                    "GoToInRoom(self,ball-1,room-0)",
                    "PickUp(self,ball-1)",
                    "GoBtwRoom(self,room-0,room-1)",
                    "PutInRoom(self,ball-1,room-1)",
                ],
            },
        ],
        seed=0,
    )


def main() -> None:
    scenario = build_scenario()
    print(f"目标 goal = {set(scenario.goal)}")
    print(f"团队规模 = {scenario.num_agent} 个机器人（要做 3 件事 → 有人身兼两职）\n")

    # 默认开窗口可视化；--headless 时只在终端打印。
    render = not HEADLESS
    viz = Visualizer(render=render, print_tree=render, fps=10.0)

    for i in range(6):
        seed = 50 + i
        print(f"--- 尝试 {i + 1}/6 (seed={seed}) ---")
        scenario = build_scenario()
        env = scenario.build_env(render=render)
        plan = plan_behavior_trees(
            env, scenario, optimal=True, use_composite_actions=True,
        )
        random.seed(seed)
        # share_belief=True 很关键：agent-1 能"听说"门已被 agent-0 打开。
        result = execute(
            env, plan, share_belief=True, max_steps=400, on_step=viz.on_step,
        )
        if result.success:
            print(f"\n✅ 成功！2 个机器人靠接力分工用 {result.steps} 步搬完了两个球。")
            viz.hold_open(env)  # 任务完成后让窗口停住，关掉窗口即退出。
            break
        print(f"   没成（{result.steps} 步），重试……\n")
    else:
        print("\n⚠️ 多次没成——重新运行一次脚本即可。")


if __name__ == "__main__":
    main()
