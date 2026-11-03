"""exp_robustness_v2.py —— 鲁棒性实验（分离「可行性」与「抗失败性」）。

为什么要分两个指标
==================
朴素做法是只报一条 ``SR vs α`` 曲线。但这条曲线其实混了两种完全不同的效应：

1. **可行性（feasibility）** —— α 太低时，每个动作只有极少数机器人掌握，
   团队可能压根凑不齐完成任务所需的能力组合。此时**即使动作永不失败**也做不完。
2. **抗失败性（robustness）** —— 在计划本身可行的前提下，动作以概率 FP 失败时，
   冗余能力能否让队友接替、在步数预算内补回来。

论文主张的是第 2 点，但朴素 SR 曲线在低 α 段主要由第 1 点驱动。
实测可以确认这一点：把 FP 设为 0（完全无失败），SR 仍随 α 从 0% 爬到 100%
—— 说明那段爬升与"鲁棒性"无关。

因此本脚本报告两条曲线：

    Feasibility(α) = SR(α, FP=0)                 能力覆盖是否足够
    Robustness(α)  = SR(α, FP) / SR(α, FP=0)     条件成功率 = 纯抗失败性

后者是**条件概率**：在"这套能力分配本来能完成任务"的前提下，遭遇失败仍成功的比例。
这样 α 对鲁棒性的贡献就被干净地隔离出来了。

执行器自检
==========
``selftest`` 用**理论最少团队步数**给执行器做断言（纯并行领域应为 1 步、
长度 D 的单链应为 D 步）。这是发现"同 tick 接力"之类同步语义 bug 的关键手段
—— 那类 bug 不会让 SR 曲线看起来异常，只能靠理论值断言抓出来。
"""
from __future__ import annotations

import random
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from statistics import mean, pstdev
from typing import Dict, List, Optional, Tuple

_HERE = Path(__file__).resolve()
_REPO = _HERE.parents[2]
for p in (str(_REPO), str(_HERE.parent)):
    if p not in sys.path:
        sys.path.insert(0, p)

from core.envs.gridenv.minigrid.planning_action import PlanningAction  # noqa: E402
from core.btp.multi_robot_optimal import MAOBTP  # noqa: E402

import domains  # noqa: E402
from exp_robustness_atomic import (  # noqa: E402
    generate_agents_actions,
    symbolic_execute,
)

RESULTS_DIR = _HERE.parent / "results"
RESULTS_DIR.mkdir(exist_ok=True)


# --------------------------------------------------------------------------- #
# 能力分配
# --------------------------------------------------------------------------- #
def assign_action_model(
    pool: List[PlanningAction], num_agent: int, alpha: float
) -> List[List[PlanningAction]]:
    """按同质性系数 α 把动作池随机分配给各机器人（逐字节移植参考实验口径）。"""
    idx_lists = generate_agents_actions(len(pool), num_agent, alpha)
    return [
        [
            PlanningAction(
                name=pool[j].name,
                pre=set(pool[j].pre),
                add=set(pool[j].add),
                del_set=set(pool[j].del_set),
                cost=pool[j].cost,
            )
            for j in idx_lists[i]
        ]
        for i in range(num_agent)
    ]


def plan_once(pool, start, goal, num_agent: int, alpha: float, seed: int):
    """一个 seed 决定一套能力分配，规划一次。返回 (planner, 用时)。"""
    random.seed(seed)
    action_lists = assign_action_model(pool, num_agent, alpha)
    t0 = time.time()
    planner = MAOBTP(verbose=False, start=start, env=None)
    planner.bfs_planning(goal, action_lists=action_lists, single_expand=False)
    return planner, time.time() - t0


# --------------------------------------------------------------------------- #
# 执行器自检：用理论最少步数断言
# --------------------------------------------------------------------------- #
def selftest(verbose: bool = True) -> bool:
    """断言执行器的同步语义正确。

    检验点：
        · flat(W)  —— 机器人数 ≥ W 时，团队步数必须 == 1（纯并行）
        · chain(D) —— 无论多少机器人，团队步数必须 == D（纯串行）

    这两条断言能同时抓出两类 bug：
        · 同 tick 内状态立即生效（会让 chain 的步数 < D）
        · 用计划图节点前提当执行守卫（会让 flat 的步数 > 1）
    """
    cases = [
        ("flat(5)", domains.build_flat(5), 8, 1),
        ("flat(5)", domains.build_flat(5), 12, 1),
        ("chain(5)", domains.build_chain(5), 8, 5),
        ("chain(5)", domains.build_chain(5), 12, 5),
        ("pipeline(3,5)", domains.build_pipeline(3, 5), 12, 5),
    ]
    ok_all = True
    if verbose:
        print("执行器自检（理论最少团队步数）", flush=True)
    for tag, (pool, start, goal, meta), num_agent, expected in cases:
        steps = []
        for seed in range(5):
            planner, _ = plan_once(pool, start, goal, num_agent, 1.0, seed)
            ok, ts, _rs = symbolic_execute(
                planner.planned_agent_list, start, goal,
                action_fail_p=0.0, max_steps=expected + 10,
                rng=random.Random(seed * 7 + 1),
            )
            if ok:
                steps.append(ts)
        got = mean(steps) if steps else float("nan")
        passed = bool(steps) and abs(got - expected) < 1e-9
        ok_all &= passed
        if verbose:
            mark = "PASS" if passed else "FAIL"
            print(f"  [{mark}] {tag:<14} {num_agent:>2} robots: "
                  f"期望 {expected} 步, 实测 {got:.2f} 步", flush=True)
    if verbose:
        print(f"自检结果：{'全部通过' if ok_all else '存在失败项'}\n", flush=True)
    return ok_all


# --------------------------------------------------------------------------- #
# 单个 seed 的两个指标
# --------------------------------------------------------------------------- #
@dataclass
class SeedStat:
    feasible: bool          # FP=0 时能否完成（该分配是否可行）
    sr_raw: float           # 有失败时的成功率（rollout 平均）
    team_steps: float       # FP=0 时的团队步数
    planning_time: float
    expanded_num: int


def run_seed(
    *,
    domain: Tuple,
    num_agent: int,
    alpha: float,
    action_fail_p: float,
    seed: int,
    rollouts: int,
    max_steps: int,
) -> SeedStat:
    """一个 seed：规划一次，先判可行性（FP=0），再跑带失败的 rollout。"""
    pool, start, goal, _meta = domain
    planner, pt = plan_once(pool, start, goal, num_agent, alpha, seed)
    planned = planner.planned_agent_list

    # ---- 可行性：FP=0 跑一次（无随机性，结果确定）------------------------
    feasible, ts0, _ = symbolic_execute(
        planned, start, goal, action_fail_p=0.0,
        max_steps=max_steps, rng=random.Random(0),
    )

    # ---- 带失败的 rollout ------------------------------------------------
    n_succ = 0
    for r in range(rollouts):
        ok, _ts, _rs = symbolic_execute(
            planned, start, goal, action_fail_p=action_fail_p,
            max_steps=max_steps, rng=random.Random(seed * 100_003 + r * 131 + 7),
        )
        if ok:
            n_succ += 1

    return SeedStat(
        feasible=feasible,
        sr_raw=n_succ / rollouts,
        team_steps=ts0 if feasible else float("nan"),
        planning_time=pt,
        expanded_num=getattr(planner, "record_expanded_num", 0),
    )


# --------------------------------------------------------------------------- #
# 扫描一个 (领域, 队伍规模) 组合
# --------------------------------------------------------------------------- #
@dataclass
class Cell:
    feas_mean: float        # 可行率（%）
    feas_std: float
    cond_mean: float        # 条件成功率 = 纯鲁棒性（%）
    cond_std: float
    raw_mean: float         # 未分离的原始 SR（%），供对照
    team_steps: float


def sweep(
    *,
    domain: Tuple,
    num_agent: int,
    alpha_list: List[float],
    fp: float,
    seeds: List[int],
    rollouts: int,
    max_steps: int,
) -> List[Cell]:
    """扫一条曲线（固定领域/规模/FP，横扫 α）。"""
    cells: List[Cell] = []
    for alpha in alpha_list:
        stats = [
            run_seed(domain=domain, num_agent=num_agent, alpha=alpha,
                     action_fail_p=fp, seed=s, rollouts=rollouts,
                     max_steps=max_steps)
            for s in seeds
        ]
        feas_vals = [1.0 if st.feasible else 0.0 for st in stats]
        raw_vals = [st.sr_raw for st in stats]
        # 条件成功率：只在可行的 seed 上统计
        cond_vals = [st.sr_raw for st in stats if st.feasible]
        ts_vals = [st.team_steps for st in stats
                   if st.team_steps == st.team_steps]

        cells.append(
            Cell(
                feas_mean=mean(feas_vals) * 100,
                feas_std=(pstdev(feas_vals) * 100 if len(feas_vals) > 1 else 0.0),
                cond_mean=(mean(cond_vals) * 100 if cond_vals else float("nan")),
                cond_std=(pstdev(cond_vals) * 100
                          if len(cond_vals) > 1 else 0.0),
                raw_mean=mean(raw_vals) * 100,
                team_steps=(mean(ts_vals) if ts_vals else float("nan")),
            )
        )
    return cells


# --------------------------------------------------------------------------- #
# 主实验
# --------------------------------------------------------------------------- #
def alpha_labels(alphas: List[float], denom: int = 6) -> List[str]:
    out = []
    for a in alphas:
        k = round(a * denom)
        out.append("0" if k == 0 else ("1" if k == denom else f"{k}/{denom}"))
    return out


def main():
    if not selftest():
        print("!! 执行器自检未通过，终止实验（数据不可信）", flush=True)
        sys.exit(1)

    # 三个结构正交的领域。max_steps 取「理论最少步数 + 2」，给失败留少量重试余量。
    domain_specs = [
        ("flat",         domains.build_flat(5),          3),
        ("room_package", domains.build_room_package(5),  4),
        ("pipeline",     domains.build_pipeline(3, 5),   7),
    ]
    agent_groups = [4, 8, 12]
    alpha_list = [k / 6 for k in range(7)]
    fp_list = [0.1, 0.3, 0.5]
    seeds = list(range(10))
    rollouts = 20

    print("=" * 78, flush=True)
    print("鲁棒性实验 v2 —— 分离「可行性」与「抗失败性」", flush=True)
    print(f"seeds={len(seeds)} rollouts/seed={rollouts} "
          f"α 档位={len(alpha_list)} FP={fp_list}", flush=True)
    print("=" * 78, flush=True)

    # results[(domain, num_agent, fp)] -> List[Cell]
    results: Dict[Tuple[str, int, float], List[Cell]] = {}
    metas: Dict[str, domains.DomainMeta] = {}
    rows = []

    for dname, domain, max_steps in domain_specs:
        pool, start, goal, meta = domain
        metas[dname] = meta
        print(f"\n### {meta.label} | 动作类={len(pool)} "
              f"min_steps={meta.min_steps} max_steps={max_steps}", flush=True)
        print(f"    {meta.note}", flush=True)
        for num_agent in agent_groups:
            print(f"  --- {num_agent} Robots ---", flush=True)
            for fp in fp_list:
                cells = sweep(domain=domain, num_agent=num_agent,
                              alpha_list=alpha_list, fp=fp, seeds=seeds,
                              rollouts=rollouts, max_steps=max_steps)
                results[(dname, num_agent, fp)] = cells
                for alpha, c in zip(alpha_list, cells):
                    rows.append((dname, num_agent, alpha, fp, c))
                feas = " ".join(f"{c.feas_mean:5.1f}" for c in cells)
                cond = " ".join(
                    (f"{c.cond_mean:5.1f}" if c.cond_mean == c.cond_mean else "  —  ")
                    for c in cells
                )
                print(f"    FP={fp} 可行率: {feas}", flush=True)
                print(f"    FP={fp} 鲁棒性: {cond}", flush=True)

    # ---- 落盘 CSV --------------------------------------------------------- #
    csv_path = RESULTS_DIR / "robustness_v2.csv"
    with open(csv_path, "w", encoding="utf-8") as f:
        f.write("domain,num_agent,alpha,action_fail_p,"
                "feasibility_mean,feasibility_std,"
                "robustness_mean,robustness_std,raw_sr_mean,team_steps\n")
        for dname, na, alpha, fp, c in rows:
            f.write(f"{dname},{na},{alpha:.4f},{fp},"
                    f"{c.feas_mean:.2f},{c.feas_std:.2f},"
                    f"{c.cond_mean:.2f},{c.cond_std:.2f},"
                    f"{c.raw_mean:.2f},{c.team_steps:.4f}\n")

    # ---- 落盘 MD ---------------------------------------------------------- #
    hdr = alpha_labels(alpha_list)
    md_path = RESULTS_DIR / "robustness_v2.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# 鲁棒性实验：可行性 vs 抗失败性\n\n")
        f.write("## 为什么分两个指标\n\n")
        f.write("朴素的 `SR vs α` 曲线混了两种效应：\n\n")
        f.write("- **可行性**：α 太低时团队凑不齐所需能力，**即使动作永不失败也做不完**；\n")
        f.write("- **抗失败性**：计划本身可行时，冗余能否补回失败的动作。\n\n")
        f.write("论文主张的是后者。实测把 FP 设为 0 时 SR 仍随 α 从 0% 爬到 100%，"
                "证明低 α 段的爬升与鲁棒性无关。因此这里报告：\n\n")
        f.write("```\nFeasibility(α) = SR(α, FP=0)\n"
                "Robustness(α)  = SR(α, FP) / SR(α, FP=0)   （条件成功率）\n```\n\n")
        f.write(f"seeds={len(seeds)}（每个 seed 一套随机能力分配）, "
                f"rollouts/seed={rollouts}。表中为均值 ± 标准差（%）。\n\n")

        f.write("## 领域结构\n\n")
        f.write("| 领域 | 依赖深度 | 依赖宽度 | 理论最少步数 | 说明 |\n")
        f.write("|------|----------|----------|--------------|------|\n")
        for dname, _domain, _ms in domain_specs:
            m = metas[dname]
            f.write(f"| {m.name} | {m.depth} | {m.width} | {m.min_steps} "
                    f"| {m.note} |\n")
        f.write("\n")

        for dname, _domain, max_steps in domain_specs:
            m = metas[dname]
            f.write(f"## {m.label}\n\n")
            f.write(f"`max_steps={max_steps}`（= 理论最少步数 {m.min_steps} + 2）\n\n")
            for num_agent in agent_groups:
                f.write(f"### {num_agent} Robots\n\n")
                f.write("| 指标 | FP | " + " | ".join(f"α={h}" for h in hdr) + " |\n")
                f.write("|------|----|" + "|".join(["------"] * len(hdr)) + "|\n")
                for fp in fp_list:
                    cells = results[(dname, num_agent, fp)]
                    f.write(f"| 可行率 | {fp} | "
                            + " | ".join(f"{c.feas_mean:.1f}±{c.feas_std:.1f}"
                                         for c in cells) + " |\n")
                for fp in fp_list:
                    cells = results[(dname, num_agent, fp)]
                    f.write(f"| 鲁棒性 | {fp} | "
                            + " | ".join(
                                (f"{c.cond_mean:.1f}±{c.cond_std:.1f}"
                                 if c.cond_mean == c.cond_mean else "—")
                                for c in cells) + " |\n")
                f.write("\n")

        f.write("## 读法\n\n")
        f.write("- **可行率**只反映能力覆盖，与 FP 无关（同一 α 下三行应基本一致，"
                "微小差异来自随机分配本身）。它随 α 上升说明冗余带来"
                "「凑齐所需能力」的收益。\n")
        f.write("- **鲁棒性**是条件成功率，已剔除不可行样本。它随 α 上升才真正说明"
                "「冗余能补回失败的动作」，这是论文主张的效应。\n")
        f.write("- 两条曲线的**分离程度**本身是有价值的结论：若某领域可行率早早饱和"
                "而鲁棒性仍在爬升，说明该领域的瓶颈是抗失败而非能力覆盖。\n")

    print("\n落盘：", csv_path, flush=True)
    print("落盘：", md_path, flush=True)
    print("ALL DONE", flush=True)


if __name__ == "__main__":
    main()
