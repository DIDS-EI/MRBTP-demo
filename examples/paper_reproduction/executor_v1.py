"""旧版（v1）符号执行器 —— 用于复现 2026-08-30 之前产出的全部鲁棒性结果。

================================ 为什么保留 ================================
`results/robustness_atomic_fig.*`、`results/robustness_pipeline_fig.*`、
`results/robustness_two_domains.html` 这几份产物都是用**这个版本**的执行器跑出来的。
主执行器（`exp_robustness_atomic.symbolic_execute`）后来改成了「快照决策 + tick 末
统一提交」的同步语义，数值会变（room/package 12R FP=0.5 最大差 92 个百分点），
因此旧结果无法用新执行器重现。把 v1 独立保留，旧结果就仍然是**可复现、可验证**的，
而不是一堆无法回溯的静态数字。

================================ 语义差异 ================================
v1（本文件）采用**异步顺序推进**语义：

  1. 状态在 agent 循环体内**立即生效**。同一个 tick 里排在后面的 agent 能看到前面
     agent 刚造成的状态变化，因此一条串行依赖链可以被多个 agent 在一个 tick 内接力
     走完。等价于把「一个 tick」解释成「一轮调度机会」而非「一个同步时间片」。
  2. 执行守卫用**回链图节点的前提** `cond_set ⊆ state`，而不是动作自身的 `act.pre`。
     图节点前提编码的是「某条特定顺序路径上的完整中间状态」，因此隐含了规划器给出的
     执行顺序约束。

v2（`exp_robustness_atomic.symbolic_execute`）采用**同步并行**语义：
tick 开始拍状态快照 → 所有 agent 基于同一快照独立决策 → 效果在 tick 末统一提交；
守卫只检查 `act.pre`。

两者对「团队步数」的定义不同：
  - v1 的 team_steps 是「调度轮数」，一轮内可跨越多层依赖
  - v2 的 team_steps 是「同步时间片数」，一片内只能推进一层依赖

因此 v1 的 TS 在深依赖任务上会小于依赖深度，v2 则恒等于依赖深度。
两种口径各自自洽，选哪个取决于论文想表达的「一步」是什么意思。

================================ 使用方式 ================================
    from executor_v1 import symbolic_execute_v1

    ok, ts, rs = symbolic_execute_v1(
        planner.planned_agent_list, start, goal,
        action_fail_p=0.3, max_steps=3, rng=random.Random(42),
    )

复现旧结果：
    ./.venv/bin/python examples/paper_reproduction/replay_v1.py
"""

from __future__ import annotations

import random
from typing import List, Optional, Tuple

# 规则提取逻辑两版共用，直接复用主模块的实现
from exp_robustness_atomic import _collect_condition_action_pairs


__all__ = ["symbolic_execute_v1"]


def symbolic_execute_v1(
    planned_agents: List,
    start_state: frozenset,
    goal: frozenset,
    *,
    action_fail_p: float = 0.0,
    max_steps: int = 5,
    rng: Optional[random.Random] = None,
) -> Tuple[bool, int, int]:
    """v1 异步顺序推进执行器（与 2026-08-30 之前的产出逐位一致）。

    每个 tick 内按 agent 序号依次决策与提交，状态立即生效；守卫使用回链图节点前提。

    Returns: (success, team_steps, total_robot_steps)
        team_steps        —— 调度轮数（v1 口径的 TS）
        total_robot_steps —— 所有 agent 成功动作次数之和（RS）
    """
    rng = rng or random
    state = set(start_state)
    num_agent = len(planned_agents)

    rules_per_agent = [_collect_condition_action_pairs(pa) for pa in planned_agents]

    team_steps = 0
    robot_steps = 0
    for _ in range(max_steps):
        if goal <= state:
            return True, team_steps, robot_steps
        team_steps += 1
        progressed = False

        for i in range(num_agent):
            # 守卫：回链图节点的完整前提（v1 语义，隐含规划器给出的顺序约束）
            best = None
            for cond_set, add_set, name, act in rules_per_agent[i]:
                if not (cond_set <= state):
                    continue
                useful_goal = (add_set & goal) - state
                useful_mid = add_set - state
                if not useful_goal and not useful_mid:
                    continue
                best = act
                if useful_goal:
                    break
            if best is None:
                continue

            # action_fail_p：尝试但失败，状态不变
            if rng.random() < action_fail_p:
                continue

            # STRIPS 转移，**立即生效**（v1 语义）
            new_state = (state | best.add) - best.del_set
            if new_state != state:
                state = new_state
                robot_steps += 1
                progressed = True

        # 死锁：一整个 tick 无人能推进，且无失败随机性 → 计划无法达成
        if not progressed and action_fail_p == 0.0:
            break

    return (goal <= state), team_steps, robot_steps
