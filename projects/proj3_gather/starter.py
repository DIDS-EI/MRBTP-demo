"""
proj3 · 聚集 IsNear（挑战）—— 你的练习
================================================================================
填完所有 `TODO` 后运行：

    python projects/proj3_gather/starter.py            # 带窗口可视化
    python projects/proj3_gather/starter.py --headless  # 无头模式

完整说明见同目录 README.md；卡住了对照 solution/solve.py。

────────────────────────────────────────────────────────────────────────────
任务：把绿球(ball-1)搬到红球(ball-0)**旁边**。
  · ball-0(红) 是锚点，一开始就在 room-1。
  · ball-1(绿) 在 room-0，要搬进 room-1 并停在 ball-0 旁。
  · 门是锁的，要有人开门。

两个全新 API（前两个项目没用过）：
  · 目标谓词 IsNear(a, b)                       —— a 紧挨着 b。
  · 动作   PutNearInRoom(self, obj, anchor, room) —— 放到 anchor 旁，而非随便空格。
────────────────────────────────────────────────────────────────────────────
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

        # TODO(1): 放两个球——红球当锚点放在 room-1，绿球放在 room-0。
        #   提示：列表顺序决定编号，第 1 个是 ball-0、第 2 个是 ball-1。
        #   我们希望红=ball-0(锚点)、绿=ball-1(被搬)。
        balls=...,

        # TODO(2): 目标只有一条——绿球(ball-1)挨着红球(ball-0)。
        #   用 IsNear 谓词，不要用 IsInRoom。
        goal=frozenset({
            ...,
        }),

        composite_library=[
            # agent-0：开门（范例，照抄）
            {"GetKeyAndOpenDoor": [
                "GoToInRoom(self,key-0,room-0)",
                "PickUp(self,key-0)",
                "GoToInRoom(self,door-0,room-0)",
                "Toggle(self,door-0)",
            ]},
            # agent-1：搬 ball-1 并停到 ball-0 旁。
            # TODO(3): 写出这份宏。前三步和搬球一样
            #   （GoToInRoom → PickUp → GoBtwRoom），
            #   但最后一步要用 PutNearInRoom(self, ball-1, ball-0, room-1)，
            #   而不是 PutInRoom——这样才会停在锚点旁而非随便落地。
            {...},
            # agent-2：用不上，留空库（长度仍要 == num_agent）。
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
