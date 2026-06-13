"""core.agents —— 决策层（上层「产 goal」抽象）。

MRBTP 的完整流水线是四段：**决策 → 规划 → 执行 → 渲染**。

    决策(GoalProvider)  ->  规划(planner)  ->  执行(executor)  ->  渲染(Renderer)
      产 goal 谓词集         goal->每 agent 行为树    跑 BT(模拟/仿真)     可选画面

在这次重构前，``goal`` 是写死在 ``Scenario`` 里的一个 ``frozenset``，规划器直接
吃掉它——上层没有任何插入点，无法做「LLM 看世界 → 产生 goal → 规划器产 act」。

本包补齐**决策层抽象** :class:`GoalProvider`：给定当前世界状态，产出团队要共同
满足的符号 goal。两个内置实现：

    * :class:`StaticGoalProvider` —— 原样返回 scenario 里写死的 goal（保持现状
      行为，零行为变化，作为默认）。
    * :class:`LLMGoalProvider`    —— 预留壳，对接 planning_llm_server：把世界状态
      喂给多机器人 LLM agent，让它产出 goal。当前默认回退到 static goal，并留好
      ``_query_llm`` 钩子。

规划器 / executor 完全不感知 GoalProvider 的存在——它们只接收最终的 goal 集合，
所以决策层可独立替换、独立测试。
"""
from core.agents.goal_provider import (
    GoalProvider,
    StaticGoalProvider,
    LLMGoalProvider,
    make_goal_provider,
)

__all__ = [
    "GoalProvider",
    "StaticGoalProvider",
    "LLMGoalProvider",
    "make_goal_provider",
]
