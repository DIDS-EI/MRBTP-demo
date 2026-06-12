"""
Example 03 · 两个机器人如何分工 —— 看清"每人一棵树"
================================================================================

第 02 课我们已经让 2 个机器人合作搬了一个球，但没细看"它们各自在干嘛"。
这一课把执行过程**逐步打印**出来，让你亲眼看到：

  · 规划器为 **每个机器人各生成一棵行为树**；
  · 每一步，每个机器人各自 tick 自己的树、选一个原子动作；
  · 两个机器人的工作是**自动分配**的——一个忙着开门，另一个忙着搬球。

你会学到：
  1. `plan.bt_list` 里就是"一人一棵"的行为树列表。
  2. 用 `on_step` 回调钩住执行循环，打印每个机器人每一步选了什么动作。
  3. 直观理解"多机器人 = 多棵并行 tick 的行为树"。

运行方式：

    python examples/03_two_robots.py
"""
from __future__ import annotations

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import random

from mrbtp_demo.scenario import Scenario
from mrbtp_demo.planner import plan_behavior_trees
from mrbtp_demo.executor import execute


def build_scenario() -> Scenario:
    return Scenario(
        name="two-robots",
        env_id="MiniGrid-DoorKey-8x8-v0",
        num_agent=2,
        balls=[("green", 0)],
        goal=frozenset({"IsInRoom(ball-0,room-1)"}),
        composite_library=[
            {"GetKeyAndOpenDoor": [
                "GoToInRoom(self,key-0,room-0)", "PickUp(self,key-0)",
                "GoToInRoom(self,door-0,room-0)", "Toggle(self,door-0)"]},
            {"MoveBallToRoom1": [
                "GoToInRoom(self,ball-0,room-0)", "PickUp(self,ball-0)",
                "GoBtwRoom(self,room-0,room-1)", "PutInRoom(self,ball-0,room-1)"]},
        ],
        seed=0,
    )


def run_and_trace(seed: int) -> bool:
    """规划、执行，并逐步打印两个机器人各自选的动作。"""
    scenario = build_scenario()
    env = scenario.build_env(render=False)

    plan = plan_behavior_trees(
        env, scenario, optimal=True, use_composite_actions=True,
    )
    # plan.bt_list 就是"一个机器人一棵"的行为树。
    print(f"规划得到 {len(plan.bt_list)} 棵行为树（每个机器人一棵）。\n")

    # ------------------------------------------------------------------ #
    # on_step 回调：执行器每走完一步就调用它一次，把这一步的"快照"交给我们。
    # record.ticks[i] 是第 i 个机器人这一步的 tick 结果。
    # 我们只打印动作不是 'done'（空转）的那些步，让输出聚焦在"真正在动"的时刻。
    # ------------------------------------------------------------------ #
    def on_step(record, _env):
        moves = [
            f"agent-{t.agent_id}={t.action_name}"
            for t in record.ticks
            if t.action_name not in ("done", "None")
        ]
        if moves:
            print(f"  step {record.step:3d} | " + "  ".join(moves))

    random.seed(seed)
    result = execute(
        env, plan, share_belief=True, max_steps=300, on_step=on_step,
    )
    return result.success


def main() -> None:
    print("=" * 60)
    print("观察两个机器人如何在同一个世界里并行行动、自动分工")
    print("=" * 60 + "\n")

    for i in range(5):
        seed = 6 + i
        print(f"########## 尝试 {i + 1}/5 (seed={seed}) ##########")
        if run_and_trace(seed):
            print("\n✅ 成功——回看上面的步骤流水：你会发现两个机器人各管各的，")
            print("   一个围着钥匙/门转，另一个围着球转，最后球进了 room-1。")
            break
        print("   （这次卡住了，换 seed 重试）\n")
    else:
        print("\n⚠️ 连续没成，再运行一次脚本即可（执行器固有随机性）。")

    print(
        "\n关键点：两个机器人**没有中心调度器**在发号施令。每个机器人独立 tick\n"
        "自己的行为树、各自认领一份子任务。它们能配合，靠的是下一课要讲的\n"
        "'共享信念空间'。试着把 03 和 04 对照着读。"
    )


if __name__ == "__main__":
    main()
