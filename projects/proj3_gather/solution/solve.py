"""
proj3 · 聚集 IsNear —— 参考答案
================================================================================
这是最有挑战的一课，因为它引入一个新谓词 **IsNear**，和一个新动作
**PutNearInRoom**。

前两个项目的目标都是 "把球放进某房间"（IsInRoom）。这次换一种目标：
不关心球具体在哪个格子，只要求 **ball-1 紧挨着 ball-0**（IsNear）。

任务设定：
  · ball-0(红) 是"锚点"，一开始就在 room-1。
  · ball-1(绿) 在 room-0，要被搬到 room-1 并**停在 ball-0 旁边**。
  · 门是锁的，所以仍要有人开门。

关键新 API：
  · 目标谓词 IsNear(a, b)      —— a 和 b 相邻。
  · 动作  PutNearInRoom(self, obj, anchor, room)
        —— 把手里的 obj 放到 room 里 anchor 物体的旁边（而不是随便找空格）。

运行：
    python projects/proj3_gather/solution/solve.py            # 带窗口可视化
    python projects/proj3_gather/solution/solve.py --headless  # 无头模式
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
        name="proj3-gather",
        env_id="MiniGrid-DoorKey-8x8-v0",
        num_agent=3,
        # ball-0(红) 当锚点，一开始就在 room-1；ball-1(绿) 在 room-0 待搬。
        balls=[("red", 1), ("green", 0)],
        # 目标用 IsNear，而不是 IsInRoom：只要求 ball-1 挨着 ball-0。
        goal=frozenset({
            "IsNear(ball-1,ball-0)",
        }),
        composite_library=[
            # agent-0：开门
            {"GetKeyAndOpenDoor": [
                "GoToInRoom(self,key-0,room-0)",
                "PickUp(self,key-0)",
                "GoToInRoom(self,door-0,room-0)",
                "Toggle(self,door-0)",
            ]},
            # agent-1：把 ball-1 搬到 room-1，并停到 ball-0 旁（PutNearInRoom）
            {"GatherBall1": [
                "GoToInRoom(self,ball-1,room-0)",
                "PickUp(self,ball-1)",
                "GoBtwRoom(self,room-0,room-1)",
                "PutNearInRoom(self,ball-1,ball-0,room-1)",
            ]},
            # agent-2：这个任务用不上第三个人，给个空库即可（长度仍要 == num_agent）。
            {},
        ],
        seed=0,
    )


def main() -> None:
    scenario = build_scenario()
    print(f"目标 goal = {set(scenario.goal)}  ← 注意这是 IsNear，不是 IsInRoom")
    print(f"团队规模 = {scenario.num_agent} 个机器人\n")

    # 默认开窗口可视化；--headless 时只在终端打印。
    render = not HEADLESS
    viz = Visualizer(render=render, print_tree=render, fps=10.0)

    for i in range(8):
        seed = 30 + i
        print(f"--- 尝试 {i + 1}/8 (seed={seed}) ---")
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
            print(f"\n✅ 成功！用 {result.steps} 步把绿球搬到了红球旁边（IsNear 达成）。")
            viz.hold_open(env)  # 任务完成后让窗口停住，关掉窗口即退出。
            break
        print(f"   没成（{result.steps} 步），重试……\n")
    else:
        print("\n⚠️ 多次没成——重新运行一次脚本即可。")


if __name__ == "__main__":
    main()
