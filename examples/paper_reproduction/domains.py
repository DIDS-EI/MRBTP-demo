"""domains.py —— 符号任务领域库（供鲁棒性实验共用）。

每个领域都是纯 STRIPS 符号定义，返回 ``(action_pool, start, goal, meta)``：

- ``action_pool``：``PlanningAction`` 列表，即"动作类池"，随后按同质性系数 α
  随机分配给各机器人；
- ``start`` / ``goal``：frozenset 字面量集合；
- ``meta``：领域元信息，含 ``depth``（依赖深度）、``width``（依赖宽度）与
  ``min_steps``（理论最少团队步数）—— 后者用于**执行器自检**，见
  ``selftest_min_steps``。

领域的设计原则是让「依赖图形状」成为唯一变量，从而检验方法是否依赖特定任务结构：

=================  ======  ======  ==================================
领域                深度    宽度    说明
=================  ======  ======  ==================================
flat                1       W      W 个互不依赖的一步动作，纯并行
room_package        2       N-1     先开门再搬运，两段式（原参考实验）
pipeline            L       K      K 条产线各 L 道工序，串行链
chain               D       1       单条 D 步链，纯串行（并行退化）
=================  ======  ======  ==================================
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from core.envs.gridenv.minigrid.planning_action import PlanningAction  # noqa: E402


@dataclass
class DomainMeta:
    """领域元信息。"""

    name: str
    label: str          # 图例/表头用的短标签
    depth: int          # 依赖深度（决定理论最少步数）
    width: int          # 依赖宽度（决定可并行的分支数）
    min_steps: int      # 机器人足够多时的理论最少团队步数
    note: str = ""


Domain = Tuple[List[PlanningAction], frozenset, frozenset, DomainMeta]


# --------------------------------------------------------------------------- #
# flat：深度 1 / 宽度 W —— 纯并行，无任何依赖
# --------------------------------------------------------------------------- #
def build_flat(width: int = 5) -> Domain:
    """W 个互不依赖的一步动作。机器人足够多时一步即可全部完成。"""
    pool: List[PlanningAction] = []
    start = set()
    for i in range(width):
        start.add(f"AtSrc(pkg-{i})")
        pool.append(
            PlanningAction(
                name=f"Deliver(pkg-{i})",
                pre={f"AtSrc(pkg-{i})"},
                add={f"AtDst(pkg-{i})"},
                del_set={f"AtSrc(pkg-{i})"},
                cost=1,
            )
        )
    goal = frozenset(f"AtDst(pkg-{i})" for i in range(width))
    meta = DomainMeta(
        name="flat",
        label=f"flat (d=1, w={width})",
        depth=1,
        width=width,
        min_steps=1,
        note="纯并行：无依赖，只考察能力覆盖与冗余",
    )
    return pool, frozenset(start), goal, meta


# --------------------------------------------------------------------------- #
# room_package：深度 2 / 宽度 N-1 —— 原参考实验领域
# --------------------------------------------------------------------------- #
def build_room_package(num_rooms: int = 5) -> Domain:
    """先开门、再把包裹搬到镜像房间。逐字节忠实参考实验的动作模型。

    注意 N 为奇数时中间那个包裹起点=终点，是退化动作（开局已达成），
    因此有效宽度为 ``num_rooms - 1``。
    """
    pool: List[PlanningAction] = []

    for i in range(num_rooms):
        pool.append(
            PlanningAction(
                name=f"OpenRoom(room-{i})",
                pre={f"IsClose(room-{i})"},
                add={f"IsOpen(room-{i})"},
                del_set={f"IsClose(room-{i})"},
                cost=1,
            )
        )
    for i in range(num_rooms):
        src, dst = i, num_rooms - 1 - i
        pool.append(
            PlanningAction(
                name=f"MovePackage(package-{i})",
                pre={
                    f"IsOpen(room-{src})",
                    f"IsOpen(room-{dst})",
                    f"IsInRoom(package-{i},room-{src})",
                },
                add={f"IsInRoom(package-{i},room-{dst})"},
                del_set={f"IsInRoom(package-{i},room-{src})"},
                cost=1,
            )
        )

    start = set()
    for i in range(num_rooms):
        start.add(f"IsClose(room-{i})")
        start.add(f"IsInRoom(package-{i},room-{i})")
    goal = frozenset(
        f"IsInRoom(package-{i},room-{num_rooms - 1 - i})" for i in range(num_rooms)
    )

    meta = DomainMeta(
        name="room_package",
        label=f"room/package (d=2, w={num_rooms - 1})",
        depth=2,
        width=num_rooms - 1,
        min_steps=2,
        note="两段式：开门 → 搬运；搬运要求两端房间同时打开，约束耦合",
    )
    return pool, frozenset(start), goal, meta


# --------------------------------------------------------------------------- #
# pipeline：深度 L / 宽度 K —— K 条产线各 L 道工序
# --------------------------------------------------------------------------- #
def build_pipeline(num_items: int = 3, num_stages: int = 5) -> Domain:
    """K 个工件各需依次通过 L 道工序，工序间严格串行。"""
    pool: List[PlanningAction] = []
    start = set()
    for k in range(num_items):
        start.add(f"AtStage(item-{k},s0)")
        for l in range(num_stages):
            pool.append(
                PlanningAction(
                    name=f"Process(item-{k},s{l})",
                    pre={f"AtStage(item-{k},s{l})"},
                    add={f"AtStage(item-{k},s{l + 1})"},
                    del_set={f"AtStage(item-{k},s{l})"},
                    cost=1,
                )
            )
    goal = frozenset(f"AtStage(item-{k},s{num_stages})" for k in range(num_items))
    meta = DomainMeta(
        name="pipeline",
        label=f"pipeline (d={num_stages}, w={num_items})",
        depth=num_stages,
        width=num_items,
        min_steps=num_stages,
        note="串行链：工序必须依序完成，深度构成时间下界",
    )
    return pool, frozenset(start), goal, meta


# --------------------------------------------------------------------------- #
# chain：深度 D / 宽度 1 —— 纯串行，并行退化
# --------------------------------------------------------------------------- #
def build_chain(depth: int = 5) -> Domain:
    """单条 D 步链。同一时刻只有一个动作可执行，增加机器人不缩短用时。"""
    pool: List[PlanningAction] = []
    for l in range(depth):
        pool.append(
            PlanningAction(
                name=f"Process(item,s{l})",
                pre={f"AtStage(item,s{l})"},
                add={f"AtStage(item,s{l + 1})"},
                del_set={f"AtStage(item,s{l})"},
                cost=1,
            )
        )
    meta = DomainMeta(
        name="chain",
        label=f"chain (d={depth}, w=1)",
        depth=depth,
        width=1,
        min_steps=depth,
        note="并行退化对照：宽度 1，队伍规模不影响用时",
    )
    return pool, frozenset({"AtStage(item,s0)"}), frozenset(
        {f"AtStage(item,s{depth})"}
    ), meta


# --------------------------------------------------------------------------- #
# 注册表
# --------------------------------------------------------------------------- #
DOMAIN_BUILDERS: Dict[str, callable] = {
    "flat": build_flat,
    "room_package": build_room_package,
    "pipeline": build_pipeline,
    "chain": build_chain,
}


def build(name: str, **kwargs) -> Domain:
    """按名字构造领域。"""
    if name not in DOMAIN_BUILDERS:
        raise KeyError(f"unknown domain {name!r}; "
                       f"available: {sorted(DOMAIN_BUILDERS)}")
    return DOMAIN_BUILDERS[name](**kwargs)
