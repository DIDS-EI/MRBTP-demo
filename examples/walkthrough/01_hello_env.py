"""
Example 01 · Hello, Environment —— 第一步：把世界建出来，看看它长什么样
================================================================================

这是整个教程的起点。目标只有一个：**不做任何规划，只把多机器人 MiniGrid
世界构造出来**，然后打印它的关键信息，让你对"机器人在一个什么样的世界里行动"
有直观认识。

你会学到：
  1. 怎样用 `Scenario` 描述一个世界（地图 + 物体 + 机器人数量）。
  2. `build_env()` 做了什么，返回的 env 里有什么。
  3. 什么是"符号化初始状态"（symbolic state）—— 规划器眼中的世界，
     是一堆形如 `IsHandEmpty(agent-0)` 的逻辑谓词，而不是像素。

运行方式（在仓库根目录、用项目 venv）：

    python examples/walkthrough/01_hello_env.py

提示：MiniGrid 的 DoorKey 地图永远是 **2 个房间**（room-0 / room-1），
中间一道上锁的门，room-0 里有钥匙。记住这点，后面写 goal 时就不会写出
不存在的 room-2。
"""
from __future__ import annotations

# MiniGrid 底层会尝试创建一个 pygame 窗口；在无显示器/无头环境下，
# 把 SDL 指向 dummy 驱动，避免它真的去开窗口而报错。
import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from minigrid.core.world_object import Ball

from app.scenario import Scenario


def main() -> None:
    # ------------------------------------------------------------------ #
    # 1) 用 Scenario 描述"我想要一个什么样的世界"
    # ------------------------------------------------------------------ #
    # Scenario 是一个纯数据对象（dataclass），它把一道题的所有设定集中在一处：
    #   - env_id    : 用哪张 MiniGrid 地图
    #   - num_agent : 放几个机器人
    #   - balls     : 往房间里丢哪些球，格式是 (颜色, 房间号) 的列表
    #   - goal      : 团队要共同满足的符号目标（本例先留空，下一课再讲）
    scenario = Scenario(
        name="hello",
        env_id="MiniGrid-DoorKey-8x8-v0",
        num_agent=2,
        balls=[("green", 0)],          # 在 room-0 放一个绿球
        goal=frozenset(),              # 本课不规划，goal 先空着
        seed=0,
    )

    print("=" * 60)
    print(f"场景名         : {scenario.name}")
    print(f"地图           : {scenario.env_id}")
    print(f"机器人数量     : {scenario.num_agent}")
    print(f"放置的球       : {scenario.balls}")
    print("=" * 60)

    # ------------------------------------------------------------------ #
    # 2) 把场景"实例化"成一个真正可交互的环境
    # ------------------------------------------------------------------ #
    # build_env 内部做了三件事：
    #   a. gym.make 出底层 MiniGrid 地图；
    #   b. 包成多机器人版 MiniGridToMAGridEnv；
    #   c. reset 两次（第一次铺房间，放完球后再 reset 一次重新索引世界）。
    # render=False 表示无头运行，不弹窗口。
    env = scenario.build_env(render=False)

    print(f"\nenv 类型       : {type(env).__name__}")
    print(f"机器人对象数量 : {len(env.agents)}")
    for i, agent in enumerate(env.agents):
        pos = tuple(int(v) for v in agent.position)
        print(f"  agent-{i}: 位置={pos} 朝向={agent.direction}")

    # ------------------------------------------------------------------ #
    # 3) 看看规划器眼中的世界 —— 符号化初始状态
    # ------------------------------------------------------------------ #
    # 规划器不看像素，它看的是一组"逻辑谓词"。要先建动作模型，再取初始状态。
    # （这两步在后面的课里都由 plan_behavior_trees 自动替你做，这里手动调用
    #   只是为了让你亲眼看见中间结果。）
    env.create_action_model()
    init_state = env.get_initial_state()

    print(f"\n初始状态共有 {len(init_state)} 条谓词，其中前 10 条：")
    for literal in sorted(init_state)[:10]:
        print(f"  · {literal}")

    print(
        "\n读懂这些谓词：\n"
        "  IsHandEmpty(agent-0)      —— 0 号机器人手是空的\n"
        "  IsInRoom(agent-0,room-1)  —— 0 号机器人此刻在 room-1\n"
        "  CanGoTo(key-0)            —— 钥匙可达\n"
        "  IsClose(door-0)           —— 门是关着的\n"
        "这套谓词就是规划器和行为树共用的'语言'。下一课我们就给它一个 goal，"
        "看它如何自动倒推出一棵行为树。"
    )


if __name__ == "__main__":
    main()
