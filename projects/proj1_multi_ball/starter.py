"""
proj1 · 多球搬运（基础）—— 你的练习
================================================================================
这是你的第一个小项目。骨架已经搭好，凡是写着 `TODO` 的地方就是留给你填的。
填完后直接运行：

    python projects/proj1_multi_ball/starter.py            # 带窗口可视化
    python projects/proj1_multi_ball/starter.py --headless  # 无头模式

完整说明见同目录的 README.md；卡住了可对照 solution/solve.py。

────────────────────────────────────────────────────────────────────────────
任务：room-0 里有 **2 个球（绿、紫）**，把它们**都搬进 room-1**。
提示：门是锁的，得有人先开门。所以最小团队 = 开门 1 人 + 搬球 2 人 = 3 个机器人。
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
        name="proj1-multi-ball",
        env_id="MiniGrid-DoorKey-8x8-v0",

        # TODO(1): 这个任务需要几个机器人？（开门 1 + 搬 2 个球）
        num_agent=...,

        # TODO(2): 往 room-0 放两个球。格式是 [(颜色, 房间号), ...]
        #   它们会按顺序自动编号成 ball-0 / ball-1。
        balls=...,

        # TODO(3): 写出目标谓词集合——"两个球最终都在 room-1"。
        #   语法示例：IsInRoom(ball-0,room-1)
        goal=frozenset({
            ...,
        }),

        # TODO(4): 一人一份宏动作库（长度必须 == num_agent）。
        #   下面已给你第 1 份（开门）作范例；照葫芦画瓢补出搬两个球的两份。
        #   常用原子动作：
        #     GoToInRoom(self, 物体, 房间)  PickUp(self, 物体)
        #     GoBtwRoom(self, 起房, 终房)   PutInRoom(self, 物体, 房间)
        composite_library=[
            # —— agent-0：拿钥匙开门（范例，照抄即可）——
            {"GetKeyAndOpenDoor": [
                "GoToInRoom(self,key-0,room-0)",
                "PickUp(self,key-0)",
                "GoToInRoom(self,door-0,room-0)",
                "Toggle(self,door-0)",
            ]},
            # —— agent-1：把 ball-0 搬进 room-1 ——
            # TODO(4a): 仿照上面，写出搬 ball-0 的 4 步宏。
            {...},
            # —— agent-2：把 ball-1 搬进 room-1 ——
            # TODO(4b): 写出搬 ball-1 的 4 步宏。
            {...},
        ],
        seed=0,
    )


def main() -> None:
    scenario = build_scenario()
    print(f"目标 goal = {set(scenario.goal)}")
    print(f"团队规模 = {scenario.num_agent} 个机器人\n")

    # 执行有随机性（单次约 70%），下面已帮你写好"自动重试"，不用改。
    # 默认开窗口可视化；--headless 时只在终端打印。
    render = not HEADLESS
    viz = Visualizer(render=render, print_tree=render, fps=10.0)

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
            print(f"\n✅ 成功！团队用 {result.steps} 步把两个球都搬进了 room-1。")
            viz.hold_open(env)  # 任务完成后让窗口停住，关掉窗口即退出。
            break
        print(f"   没成（{result.steps} 步），重试……\n")
    else:
        print("\n⚠️ 多次没成——重新运行一次脚本即可（执行有随机性）。")


if __name__ == "__main__":
    main()
