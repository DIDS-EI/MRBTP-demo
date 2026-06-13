"""
Example 02 · 最小团队，单目标 —— 第一次让规划器干活
================================================================================

上一课我们只是把世界建出来。这一课迈出关键一步：给一个 **goal**，
让规划器自动把它"倒推"成每个机器人一棵的行为树，并真正跑起来。

为什么是 **2 个机器人**而不是 1 个？
--------------------------------------------------------------------------------
MRBTP 是"多机器人"框架，它的任务分配机制（每个机器人各自 *认领* 一份子任务）
**最少需要 2 个机器人**才能正常工作——用 1 个机器人会发现行为树一直空转。
所以"最小可用团队"就是 2 个：一个去拿钥匙开门，另一个去搬球。这也正好引出
下一课的主题——**协作**。

本课目标仍然最朴素：把绿球搬进 room-1。但因为门是锁的，必须有人先开门。

你会学到：
  1. `goal` 怎么写（符号谓词的集合）。
  2. 一份 `composite_library` 如何按"一个机器人一份工作"来分配宏动作。
  3. `plan_behavior_trees()` → `execute()` 的完整主线。

运行方式：

    python examples/walkthrough/02_single_goal.py

注意：执行带随机性（两个机器人偶尔会在门口"互相让路"卡住），单次成功率约
70%。本课内置了"自动重试"循环，所以你基本总能看到成功。正式 CI 自检请用
会自动重试的 `python -m app.verify`。
"""
from __future__ import annotations

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import random

from app.scenario import Scenario
from app.planner import plan_behavior_trees
from app.executor import execute


def build_scenario() -> Scenario:
    """把绿球搬进 room-1：一人开门，一人搬球。"""
    return Scenario(
        name="single-goal",
        env_id="MiniGrid-DoorKey-8x8-v0",
        num_agent=2,
        balls=[("green", 0)],                       # room-0 放一个绿球
        goal=frozenset({"IsInRoom(ball-0,room-1)"}),  # 终极目标：球进 room-1
        # 一个机器人一份"宏动作库"。列表长度 = 机器人数。
        # 宏 = 一串按顺序展开的原子动作；'self' 在规划时会绑定到具体机器人。
        composite_library=[
            # —— 给 agent-0 的工作：拿钥匙 + 开门 ——
            {
                "GetKeyAndOpenDoor": [
                    "GoToInRoom(self,key-0,room-0)",
                    "PickUp(self,key-0)",
                    "GoToInRoom(self,door-0,room-0)",
                    "Toggle(self,door-0)",
                ],
            },
            # —— 给 agent-1 的工作：把球从 room-0 搬到 room-1 ——
            {
                "MoveBallToRoom1": [
                    "GoToInRoom(self,ball-0,room-0)",
                    "PickUp(self,ball-0)",
                    "GoBtwRoom(self,room-0,room-1)",
                    "PutInRoom(self,ball-0,room-1)",
                ],
            },
        ],
        seed=0,
    )


def run_once(seed: int) -> tuple[bool, int]:
    """规划 + 执行一次，返回 (是否成功, 步数)。"""
    scenario = build_scenario()
    env = scenario.build_env(render=False)

    # optimal=True 用 MAOBTP（代价感知、支持宏动作）。
    plan = plan_behavior_trees(
        env, scenario, optimal=True, use_composite_actions=True,
    )

    # seed 放在执行前：planner 会消耗掉不定量的随机数，所以只有在这里
    # 重新播种，GoBtwRoom 的随机游走（以及步数）才可复现。
    random.seed(seed)
    result = execute(env, plan, share_belief=True, max_steps=300)
    return result.success, result.steps


def main() -> None:
    scenario = build_scenario()
    print(f"目标 goal = {set(scenario.goal)}")
    print(f"团队规模 = {scenario.num_agent} 个机器人\n")

    # —— 自动重试：单次约 70% 成功，多试几次基本必中 ——
    attempts = 5
    for i in range(attempts):
        seed = 6 + i
        print(f"--- 第 {i + 1}/{attempts} 次尝试 (seed={seed}) ---")
        success, steps = run_once(seed)
        if success:
            print("\n" + "=" * 60)
            print(f"✅ 成功！团队用 {steps} 步把绿球搬进了 room-1"
                  f"（第 {i + 1} 次尝试）。")
            print("=" * 60)
            break
        else:
            print(f"   这次没成（{steps} 步到上限），换个 seed 再试……\n")
    else:
        print("\n⚠️ 连续几次都没成——这是执行器的固有随机性，再运行一次脚本即可。")

    print(
        "\n小结：你没有写任何'先拿钥匙再开门'的 if-else，只声明了一个目标谓词 +\n"
        "一份按机器人切分的宏动作库，规划器就自动给每个机器人倒推出了行为树。\n"
        "这就是 BTP 的核心思想：**声明目标，而非编排流程**。\n"
        "下一课我们正式看'两个机器人如何分工协作'。"
    )


if __name__ == "__main__":
    main()
