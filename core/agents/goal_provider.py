"""GoalProvider 协议与内置实现。

见 :mod:`core.agents` 的包文档了解它在四段流水线里的位置。
"""
from __future__ import annotations

from typing import Any, Optional, Protocol, runtime_checkable

from core.utils.tools import print_colored


@runtime_checkable
class GoalProvider(Protocol):
    """决策层契约：给定世界状态，产出团队要共同满足的符号 goal。

    规划器只依赖这个协议的产物（一个谓词 ``frozenset``），看不到 goal 是
    人写死的、搜索出来的、还是 LLM 产生的。
    """

    def propose_goal(self, world_state: Any) -> frozenset:
        """返回团队要满足的目标谓词集合。

        Args:
            world_state: 当前世界。最常见是一个已 build 好的 SimBackend
                （MiniGrid env），也可以是任意后端定义的状态对象。决策器可
                从中读取初始谓词、物体列表、房间结构等来决定 goal。

        Returns:
            一个目标谓词 ``frozenset``，如 ``{"IsInRoom(ball-0,room-1)"}``。
        """
        ...


class StaticGoalProvider:
    """最简单的决策器：原样返回 scenario 里写死的 goal。

    这是**默认**实现，保证重构后行为与重构前逐字节一致——goal 还是那个 goal，
    只是现在经由决策层这道缝传出来，于是上层有了统一的替换点。
    """

    def __init__(self, goal: frozenset):
        self._goal = frozenset(goal)

    def propose_goal(self, world_state: Any) -> frozenset:
        return self._goal


class LLMGoalProvider:
    """预留：把世界状态交给多机器人 LLM agent，由它产出 goal。

    这是用户远期诉求「上层接入多机器人 LLM agent」的落点。真正接入时，把
    :meth:`_query_llm` 实现成对 planning_llm_server 的调用（混元 / Qwen），
    把世界状态序列化成 prompt，解析返回的 goal 谓词。

    为了让流水线在 LLM 未接入时也能跑，构造时可传一个 ``fallback_goal``：
    LLM 调用失败 / 未实现时回退到它（通常就是 scenario 写死的 goal）。
    """

    def __init__(
        self,
        fallback_goal: frozenset,
        *,
        server_url: Optional[str] = None,
        model: str = "hunyuan",
    ):
        self._fallback = frozenset(fallback_goal)
        self.server_url = server_url
        self.model = model

    def propose_goal(self, world_state: Any) -> frozenset:
        try:
            goal = self._query_llm(world_state)
            if goal:
                return frozenset(goal)
        except NotImplementedError:
            print_colored(
                "[LLMGoalProvider] LLM 后端未接入，回退到 static goal。",
                "yellow",
            )
        except Exception as exc:  # noqa: BLE001 - 决策失败不该拖垮整条流水线
            print_colored(
                f"[LLMGoalProvider] LLM 产 goal 失败（{type(exc).__name__}: {exc}），"
                f"回退到 static goal。",
                "yellow",
            )
        return self._fallback

    def _query_llm(self, world_state: Any) -> frozenset:
        """对接 planning_llm_server 的钩子（待实现）。

        建议实现步骤：
            1. 从 ``world_state`` 抽取可读的世界描述（物体、房间、初始谓词）。
            2. 组 prompt，POST 到 ``self.server_url``（feature/game_claw_v0.1
               那套混元 / Qwen 调用），可带「深度思考」开关。
            3. 解析返回，校验每个谓词都能被当前行为库识别，再返回 frozenset。
        """
        raise NotImplementedError(
            "LLMGoalProvider._query_llm 待接入 planning_llm_server。"
        )


def make_goal_provider(scenario: Any, *, kind: str = "static", **kwargs) -> GoalProvider:
    """按类型构造决策器。

    Args:
        scenario: 提供 ``goal`` 字段（作为 static goal / LLM 回退 goal）。
        kind:     ``"static"``（默认）或 ``"llm"``。
        **kwargs: 透传给具体决策器（如 LLM 的 server_url / model）。

    Returns:
        一个满足 :class:`GoalProvider` 协议的实例。

    Raises:
        ValueError: 未知 kind。
    """
    key = (kind or "static").strip().lower()
    if key == "static":
        return StaticGoalProvider(scenario.goal)
    if key == "llm":
        return LLMGoalProvider(scenario.goal, **kwargs)
    raise ValueError(f"未知 GoalProvider 类型 '{kind}'，支持：'static' / 'llm'。")
