"""
proj1 · 多球搬运 —— 参考答案
================================================================================
这是 starter.py 的一份可运行参考实现。建议你先独立完成 starter.py 的 TODO，
卡住了再来对照这里。

任务：把 room-0 的 2 个球（绿、紫）都搬进 room-1。
思路：一人开门 + 两人各搬一个球 = 3 个机器人，一人一份宏动作库。

运行：
    python projects/proj1_multi_ball/solution/solve.py            # 带窗口可视化
    python projects/proj1_multi_ball/solution/solve.py --headless  # 无头模式
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
        name="proj1-multi-ball",
        env_id="MiniGrid-DoorKey-8x8-v0",
        num_agent=3,
        # 两个球都丢在 room-0，自动编号 ball-0(绿) / ball-1(紫)。
        balls=[("green", 0), ("purple", 0)],
        # 目标只关心"结果状态"：两个球最终都在 room-1。
        goal=frozenset({
            "IsInRoom(ball-0,room-1)",
            "IsInRoom(ball-1,room-1)",
        }),
        # 一人一份宏（共 3 份）：开门的、搬绿球的、搬紫球的。
        composite_library=[
            {"GetKeyAndOpenDoor": [
                "GoToInRoom(self,key-0,room-0)",
                "PickUp(self,key-0)",
                "GoToInRoom(self,door-0,room-0)",
                "Toggle(self,door-0)",
            ]},
            {"MoveBall0": [
                "GoToInRoom(self,ball-0,room-0)",
                "PickUp(self,ball-0)",
                "GoBtwRoom(self,room-0,room-1)",
                "PutInRoom(self,ball-0,room-1)",
            ]},
            {"MoveBall1": [
                "GoToInRoom(self,ball-1,room-0)",
                "PickUp(self,ball-1)",
                "GoBtwRoom(self,room-0,room-1)",
                "PutInRoom(self,ball-1,room-1)",
            ]},
        ],
        seed=0,
    )


def main() -> None:
    scenario = build_scenario()
    print(f"目标 goal = {set(scenario.goal)}")
    print(f"团队规模 = {scenario.num_agent} 个机器人\n")

    # 默认开窗口可视化；--headless 时只在终端打印。
    render = not HEADLESS
    viz = Visualizer(render=render, print_tree=render, fps=10.0)

    # 执行有随机性（单次约 70%），多试几个 seed 兜住。
    for i in range(6):
        seed = 40 + i
        print(f"--- 尝试 {i + 1}/6 (seed={seed}) ---")
        scenario = build_scenario()
        env = scenario.build_env(render=render)
        plan = plan_behavior_trees(
            env, scenario, optimal=True, use_composite_actions=True,
        )
        random.seed(seed)
        result = execute(
            env, plan, share_belief=True, max_steps=400, on_step=viz.on_step,
        )
        if result.success:
            print(f"\n✅ 成功！3 个机器人用 {result.steps} 步把两个球都搬进了 room-1。")
            viz.hold_open(env)  # 任务完成后让窗口停住，关掉窗口即退出。
            break
        print(f"   没成（{result.steps} 步），重试……\n")
    else:
        print("\n⚠️ 多次没成——重新运行一次脚本即可。")


if __name__ == "__main__":
    main()
