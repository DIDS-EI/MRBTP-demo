"""
proj2 · 接力开门搬运（进阶）—— 你的练习
================================================================================
填完所有 `TODO` 后运行：

    python projects/proj2_relay/starter.py            # 带窗口可视化
    python projects/proj2_relay/starter.py --headless  # 无头模式

完整说明见同目录 README.md；卡住了对照 solution/solve.py。

────────────────────────────────────────────────────────────────────────────
任务：只有 **2 个机器人**，却要做 **3 件事**——开门 + 搬 ball-0 + 搬 ball-1。
关键点：必须让某个机器人"身兼两职"。做法是——**在它那份宏库 dict 里放两个宏**，
规划器会把这两份工作都派给它。
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
        name="proj2-relay",
        env_id="MiniGrid-DoorKey-8x8-v0",
        num_agent=2,
        balls=[("green", 0), ("purple", 0)],
        goal=frozenset({
            "IsInRoom(ball-0,room-1)",
            "IsInRoom(ball-1,room-1)",
        }),
        composite_library=[
            # —— agent-0：身兼两职 = 开门 + 搬 ball-0 ——
            #    注意：这一份 dict 里要放 **两个** 宏。
            {
                "GetKeyAndOpenDoor": [
                    "GoToInRoom(self,key-0,room-0)",
                    "PickUp(self,key-0)",
                    "GoToInRoom(self,door-0,room-0)",
                    "Toggle(self,door-0)",
                ],
                # TODO(1): 在同一个 dict 里再加一个宏 "MoveBall0"，
                #   内容是把 ball-0 从 room-0 搬到 room-1 的 4 步。
                #   （参考上面的范式：GoToInRoom → PickUp → GoBtwRoom → PutInRoom）
                ...
            },
            # —— agent-1：搬 ball-1 ——
            # TODO(2): 写出 agent-1 的宏库（一个 "MoveBall1" 宏即可）。
            {...},
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
        # share_belief=True：agent-1 能"听说"门已被 agent-0 打开，是协作的关键。
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
