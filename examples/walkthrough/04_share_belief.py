"""
Example 04 · 共享信念空间 —— 多机器人协作的"通信开关"
================================================================================

这是整套 demo 最有"研究味"的一课，对应论文的核心卖点：
**共享信念空间（shared belief space）**。

一句话解释这个开关：
  · `share_belief=True` （默认）
      一个机器人认领某项任务后，会把"我即将让这些条件变为真"广播给队友。
      于是队友会 (a) 不重复做同一件事，(b) 愿意等待——比如"门马上会被打开"。
      → 团队像一支配合默契的队伍。

  · `share_belief=False` （消融实验）
      每个机器人都活在自己的世界里，只根据**真实环境状态**推理，完全不知道
      队友打算干什么。→ 容易重复劳动、互相干等、在门口 deadlock。

本课演示**做消融实验的方法**：把同一任务在 开/关 两种模式下各跑 N 次，
统计成功率与平均步数。

运行方式：

    python examples/walkthrough/04_share_belief.py

⚠️ 关于"差异有多大"：这个最小 demo 任务较简单，单看几次统计差异可能不明显，
甚至偶尔反直觉（执行随机性所致）。**通信的价值在任务越复杂、机器人越多时越
突出**——想看更明显的差距，把下面 `SCENARIO`/`NUM_AGENT`/`TRIALS` 调大
（如 warehouse + 4 机器人 + 20 次），但那会跑得久很多。这里默认用快的 smoke
配置，先让你掌握"怎么做、怎么读"。
"""
from __future__ import annotations

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import contextlib
import random

from app.scenario import smoke_scenario, warehouse_scenario
from app.planner import plan_behavior_trees
from app.executor import execute


# ---- 可调旋钮：想看更明显的差异就把这些调大（但会更慢）-------------------- #
SCENARIO = smoke_scenario      # 换成 warehouse_scenario 看更复杂的协作
NUM_AGENT = 2                  # warehouse 建议 4
TRIALS = 8                     # 每种模式跑几次；调大统计更稳
MAX_STEPS = 250                # warehouse 建议 400


def run_once(share_belief: bool, seed: int) -> tuple[bool, int]:
    """在指定信念模式下规划+执行一次（静音库内打印），返回 (成功?, 步数)。"""
    scenario = SCENARIO(num_agent=NUM_AGENT)
    with open(os.devnull, "w") as dn, contextlib.redirect_stdout(dn):
        env = scenario.build_env(render=False)
        plan = plan_behavior_trees(
            env, scenario, optimal=True, use_composite_actions=True,
        )
        random.seed(seed)
        result = execute(
            env, plan, share_belief=share_belief, max_steps=MAX_STEPS,
        )
    return result.success, result.steps


def benchmark(share_belief: bool) -> tuple[int, float]:
    """对一种模式跑 TRIALS 次，打印每次结果，返回 (成功次数, 成功时平均步数)。"""
    label = "共享信念 ON " if share_belief else "共享信念 OFF"
    wins, total_steps = 0, 0
    print(f"\n【{label}】跑 {TRIALS} 次：")
    for i in range(TRIALS):
        ok, steps = run_once(share_belief, seed=10 + i)
        wins += int(ok)
        if ok:
            total_steps += steps
        print(f"  第 {i + 1} 次: {'✅' if ok else '❌'}  步数={steps}")
    avg = (total_steps / wins) if wins else float("nan")
    print(f"  → 成功率 {wins}/{TRIALS} = {wins / TRIALS * 100:.0f}%；"
          f"成功时平均 {avg:.1f} 步")
    return wins, avg


def main() -> None:
    print("=" * 60)
    print("消融实验：共享信念空间 对多机器人协作的影响")
    print(f"场景={SCENARIO.__name__}  机器人={NUM_AGENT}  每模式跑={TRIALS} 次")
    print("=" * 60)

    win_on, avg_on = benchmark(share_belief=True)
    win_off, avg_off = benchmark(share_belief=False)

    print("\n" + "=" * 60)
    print("对比小结：")
    print(f"  共享信念 ON : 成功 {win_on}/{TRIALS}，平均 {avg_on:.1f} 步")
    print(f"  共享信念 OFF: 成功 {win_off}/{TRIALS}，平均 {avg_off:.1f} 步")
    print("=" * 60)
    print(
        "\n怎么读这组数据：\n"
        "  · 理论预期：开启共享信念时，团队协调更好——成功率更高、步数更省，\n"
        "    因为没人重复劳动、该等的会等。\n"
        "  · 在这个简单 smoke 任务上差距可能很小（甚至被随机性盖过）。这不是\n"
        "    bug——通信的收益要在'任务更难、机器人更多、容易撞车'时才放大。\n"
        "  · 动手验证：把文件顶部 SCENARIO 改成 warehouse_scenario、NUM_AGENT=4、\n"
        "    TRIALS=20，再跑一次（会慢不少），差距通常会清楚很多。\n"
        "\n这正是 `run.py --no-share-belief` 想让你观察的现象，这里用统计量化了它。"
    )


if __name__ == "__main__":
    main()
