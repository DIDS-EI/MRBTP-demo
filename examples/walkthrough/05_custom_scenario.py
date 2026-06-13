"""
Example 05 · 从零拼一个自己的场景 —— 真正开始"创作"
================================================================================

前面几课都在用现成的 warehouse / smoke。这一课教你**从零手写一个 Scenario**，
这是你以后设计任何新任务的基本功。

一个 Scenario 就是回答 4 个问题：
  1. 在哪张地图？        → env_id
  2. 放几个机器人？      → num_agent
  3. 往房间里丢什么？    → balls = [(颜色, 房间号), ...]
  4. 团队的目标是什么？  → goal（一组谓词）
  （外加可选的第 5 问：给机器人哪些多步宏动作？→ composite_library）

本课设计一个新任务：**把两个球都集中到 room-1**——绿球和紫球都从 room-0
搬过去。需要一人开门、两人各搬一个球，所以用 3 个机器人。

运行方式：

    python examples/walkthrough/05_custom_scenario.py

⚠️ 三条最容易踩的坑（务必记住）：
  · DoorKey 地图只有 **room-0 / room-1 两个房间**，写 room-2 会直接报错。
  · 球的 id 按 balls 列表顺序自动编号：第 1 个是 ball-0，第 2 个是 ball-1……
  · composite_library 的长度必须等于 num_agent（一人一份；可以是空 dict）。
"""
from __future__ import annotations

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import random

from app.scenario import Scenario
from app.planner import plan_behavior_trees
from app.executor import execute


def build_my_scenario() -> Scenario:
    """我的新任务：把 room-0 的绿球和紫球都搬进 room-1。"""
    return Scenario(
        name="collect-two-balls",
        env_id="MiniGrid-DoorKey-8x8-v0",   # 8x8 小地图，跑得快、好调试
        num_agent=3,
        # 往 room-0 丢两个球；它们会被自动编号成 ball-0(绿) / ball-1(紫)。
        balls=[
            ("green", 0),    # → ball-0
            ("purple", 0),   # → ball-1
        ],
        # 目标：两个球最终都在 room-1。注意目标只关心"结果状态"，
        # 不关心"谁去搬、怎么搬"——那是规划器的事。
        goal=frozenset({
            "IsInRoom(ball-0,room-1)",
            "IsInRoom(ball-1,room-1)",
        }),
        # 一人一份宏动作库（3 份）：开门的、搬绿球的、搬紫球的。
        composite_library=[
            # agent-0：拿钥匙开门
            {"GetKeyAndOpenDoor": [
                "GoToInRoom(self,key-0,room-0)",
                "PickUp(self,key-0)",
                "GoToInRoom(self,door-0,room-0)",
                "Toggle(self,door-0)",
            ]},
            # agent-1：搬 ball-0（绿）
            {"MoveBall0": [
                "GoToInRoom(self,ball-0,room-0)",
                "PickUp(self,ball-0)",
                "GoBtwRoom(self,room-0,room-1)",
                "PutInRoom(self,ball-0,room-1)",
            ]},
            # agent-2：搬 ball-1（紫）
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
    scenario = build_my_scenario()
    print("=" * 60)
    print(f"我的自定义场景: {scenario.name}")
    print(f"  地图     : {scenario.env_id}")
    print(f"  机器人   : {scenario.num_agent} 个")
    print(f"  球       : {scenario.balls}")
    print(f"  目标     : {set(scenario.goal)}")
    print("=" * 60)

    # 8x8 地图 + 3 机器人通常很快，给适度重试兜住随机性。
    for i in range(6):
        seed = 20 + i
        print(f"\n--- 尝试 {i + 1}/6 (seed={seed}) ---")
        scenario = build_my_scenario()
        env = scenario.build_env(render=False)
        plan = plan_behavior_trees(
            env, scenario, optimal=True, use_composite_actions=True,
        )
        random.seed(seed)
        result = execute(env, plan, share_belief=True, max_steps=400)
        if result.success:
            print(f"\n✅ 成功！3 个机器人用 {result.steps} 步把两个球都集中到了 room-1。")
            break
        print(f"   没成（{result.steps} 步），重试……")
    else:
        print("\n⚠️ 多次没成——重新运行一次脚本即可（执行有随机性）。")

    print(
        "\n现在你已经能独立设计任务了。试着改改这个文件：\n"
        "  · 加第三个球 ('yellow', 0)，目标里再加一条 IsInRoom(ball-2,room-1)，\n"
        "    并补一个机器人 + 一份搬运宏；\n"
        "  · 或者换个目标谓词，比如用 IsNear(ball-0,ball-1) 让两球'挨在一起'。\n"
        "改完直接 python 跑，看规划器还能不能自动搞定。这正是 projects/ 里\n"
        "那些小项目要你练的事。"
    )


if __name__ == "__main__":
    main()
