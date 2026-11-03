"""v1 口径统一鲁棒性实验：3 领域 × 4/8/12 Robots = 9 组曲线。

============================== 与其他脚本的关系 ==============================
本脚本是 v1 口径（异步顺序推进执行器）的**统一入口**，把三个结构正交的领域
放进同一套实验与落盘流程，产出 3×3 九子图所需的完整数据。

  - 执行器：`executor_v1.symbolic_execute_v1`（一个 tick 内各 agent 按序决策并
    立即提交状态，"一步"= 一轮调度机会）
  - 对照：`exp_robustness_v2.py` 是 v2 同步并行口径（"一步"= 一个同步时间片），
    两者数值不可混用

已验证：本脚本产出的 room/package 与 pipeline 数据与此前单独跑出的
`robustness_atomic_fig.csv` / `robustness_pipeline_fig.csv` 逐位一致
（见 `replay_v1.py`）。flat 领域为本次新增补齐。

================================ 三个领域 ================================
按「依赖深度 × 依赖宽度」构造结构正交的三档：

  flat          深度 1 / 宽度 5   —— 5 个互不依赖的一步动作，纯并行、零依赖
  room_package  深度 2 / 宽度 4   —— 开门 → 搬运，四组独立镜像配对
  pipeline      深度 5 / 宽度 3   —— 3 个工件各需顺序经过 5 道工序，窄而深

步数预算 `max_steps` 按各领域「刚好能体现区分度」单独标定（见 DOMAIN_SPECS）：
预算给太宽，失败重试总能补回来，三条 FP 曲线会全顶到 100%，看不出鲁棒性差异。

================================ 统计结构 ================================
每格（领域 × 规模 × α × FP）：
  - 10 个 seed，每个 seed 决定一套随机动作分配（`generate_agents_actions`）并规划一次
  - 每个 seed 下跑 20 次执行 rollout（只有失败随机性变化，规划复用）→ 该 seed 的成功率
  - 上报 10 个 seed 成功率的均值 ± 标准差

误差带语义：**换一套动作分配，成功率会波动多少**。

运行：
    cd /Users/yishuaicai/mywork/mrbtp-demo
    SDL_VIDEODRIVER=dummy ./.venv/bin/python examples/paper_reproduction/exp_robustness_v1_all.py
"""

from __future__ import annotations

import random
import sys
import time
from fractions import Fraction
from pathlib import Path
from statistics import mean, pstdev
from typing import Dict, List, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from core.btp.multi_robot_optimal import MAOBTP                        # noqa: E402
from core.envs.gridenv.minigrid.planning_action import PlanningAction  # noqa: E402

from executor_v1 import symbolic_execute_v1                            # noqa: E402
from exp_robustness_atomic import (                                    # noqa: E402
    build_atomic_action_pool,
    build_goal,
    build_start,
    generate_agents_actions,
)

RESULTS_DIR = Path(__file__).resolve().parent / "results"
RESULTS_DIR.mkdir(exist_ok=True)


# ============================ 领域构造 ============================

def build_flat(width: int = 5):
    """深度 1 / 宽度 W：W 个互不依赖的一步动作（纯并行、零依赖）。"""
    pool, start = [], set()
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
    goal = frozenset({f"AtDst(pkg-{i})" for i in range(width)})
    return pool, frozenset(start), goal


def build_room_package(num_rooms: int = 5):
    """深度 2 / 宽度 4：开门 → 搬运，原子动作逐字节忠实参考实验。"""
    return (
        build_atomic_action_pool(num_rooms),
        build_start(num_rooms),
        build_goal(num_rooms),
    )


def build_pipeline(num_items: int = 3, num_stages: int = 5):
    """深度 L / 宽度 K：K 个工件各需顺序经过 L 道工序。"""
    pool, start = [], set()
    for k in range(num_items):
        start.add(f"AtStage(item-{k},s0)")
        for l in range(num_stages):
            pool.append(
                PlanningAction(
                    name=f"Process(item-{k},s{l})",
                    pre={f"AtStage(item-{k},s{l})"},
                    add={f"AtStage(item-{k},s{l+1})"},
                    del_set={f"AtStage(item-{k},s{l})"},
                    cost=1,
                )
            )
    goal = frozenset({f"AtStage(item-{k},s{num_stages})" for k in range(num_items)})
    return pool, frozenset(start), goal


# key -> (中文名, 英文名, depth, width, max_steps, builder)
# max_steps 按各领域「曲线有区分度」单独标定，见模块 docstring。
DOMAIN_SPECS = [
    ("flat",         "flat",         "flat",         1, 5, 2, build_flat),
    ("room_package", "room/package", "room/package", 2, 4, 3, build_room_package),
    ("pipeline",     "pipeline",     "pipeline",     5, 3, 7, build_pipeline),
]

ALPHAS = [k / 6 for k in range(7)]          # α = 0, 1/6, ..., 1
FPS = [0.1, 0.3, 0.5]                       # 三条曲线
AGENT_GROUPS = [4, 8, 12]                   # 三列子图
SEEDS = list(range(10))                     # 10 套随机动作分配
ROLLOUTS = 20                               # 每套分配跑 20 次执行


def alpha_labels(alphas, denom: int = 6) -> List[str]:
    """把 α 值转成分数标签。统一分母，避免不同子图同一 α 显示成不同分数。"""
    out = []
    for a in alphas:
        fr = Fraction(round(a * denom), denom)
        if fr == 0:
            out.append("0")
        elif fr == 1:
            out.append("1")
        else:
            out.append(f"{fr.numerator}/{denom}")
    return out


def assign(pool, num_agent: int, alpha: float):
    """按同质性系数 α 随机分配动作类（移植自参考实验 generate_agents_actions）。"""
    idx = generate_agents_actions(len(pool), num_agent, alpha)
    return [
        [
            PlanningAction(
                name=pool[j].name,
                pre=set(pool[j].pre),
                add=set(pool[j].add),
                del_set=set(pool[j].del_set),
                cost=pool[j].cost,
            )
            for j in idx[i]
        ]
        for i in range(num_agent)
    ]


def run_cell(pool, start, goal, num_agent, alpha, fp, max_steps):
    """跑一格，返回 (SR_mean, SR_std, TS, PT, EC)。"""
    srs, tss, pts, ecs = [], [], [], []
    for s in SEEDS:
        random.seed(s)
        action_lists = assign(pool, num_agent, alpha)

        t0 = time.time()
        planner = MAOBTP(verbose=False, start=start, env=None)
        planner.bfs_planning(goal, action_lists=action_lists, single_expand=False)
        pts.append(time.time() - t0)
        ecs.append(getattr(planner, "record_expanded_num", 0))

        ok_count = 0
        for r in range(ROLLOUTS):
            rng = random.Random(s * 100003 + r * 131 + 7)
            ok, ts, _rs = symbolic_execute_v1(
                planner.planned_agent_list, start, goal,
                action_fail_p=fp, max_steps=max_steps, rng=rng,
            )
            if ok:
                ok_count += 1
            tss.append(ts)
        srs.append(ok_count / ROLLOUTS)

    return (
        mean(srs),
        pstdev(srs) if len(srs) > 1 else 0.0,
        mean(tss) if tss else float("nan"),
        mean(pts),
        mean(ecs),
    )


def main():
    print("=" * 80, flush=True)
    print("v1 口径统一鲁棒性实验 —— 3 领域 × 4/8/12 Robots（9 组曲线）", flush=True)
    print(f"执行器: symbolic_execute_v1（异步顺序推进，'一步'= 一轮调度机会）", flush=True)
    print(f"统计: {len(SEEDS)} seed × {ROLLOUTS} rollout, α {len(ALPHAS)} 档, "
          f"FP {FPS}", flush=True)
    print("=" * 80, flush=True)

    rows = []      # (domain, depth, width, num_agent, alpha, fp, sr, sd, ts, pt, ec)
    curves: Dict[Tuple[str, int, float], Tuple[List[float], List[float]]] = {}
    ts_table: Dict[Tuple[str, int], float] = {}   # (domain, num_agent) -> TS @ α=1,FP=0.1

    for key, cn, _en, depth, width, max_steps, builder in DOMAIN_SPECS:
        pool, start, goal = builder()
        print(f"\n{'─' * 80}", flush=True)
        print(f"领域 {cn}  深度={depth} 宽度={width}  "
              f"动作类={len(pool)}  max_steps={max_steps}", flush=True)
        print("─" * 80, flush=True)

        for num_agent in AGENT_GROUPS:
            print(f"  --- {num_agent} Robots ---", flush=True)
            for fp in FPS:
                m_series, s_series = [], []
                for alpha in ALPHAS:
                    sr, sd, ts, pt, ec = run_cell(
                        pool, start, goal, num_agent, alpha, fp, max_steps
                    )
                    rows.append((key, depth, width, num_agent, alpha, fp,
                                 sr, sd, ts, pt, ec))
                    m_series.append(sr * 100)
                    s_series.append(sd * 100)
                    if abs(alpha - 1.0) < 1e-9 and abs(fp - 0.1) < 1e-9:
                        ts_table[(key, num_agent)] = ts
                curves[(key, num_agent, fp)] = (m_series, s_series)
                print(f"    FP={fp}: SR% "
                      + " ".join(f"{v:5.1f}±{e:<4.1f}"
                                 for v, e in zip(m_series, s_series)),
                      flush=True)

    # ------------------------------ 落盘 CSV ------------------------------
    csv_path = RESULTS_DIR / "robustness_v1_all.csv"
    with open(csv_path, "w", encoding="utf-8") as f:
        f.write("domain,depth,width,num_agent,alpha,action_fail_p,"
                "SR_mean,SR_std,TS,PT,EC\n")
        for (key, depth, width, na, alpha, fp, sr, sd, ts, pt, ec) in rows:
            f.write(f"{key},{depth},{width},{na},{alpha:.4f},{fp},"
                    f"{sr:.4f},{sd:.4f},{ts:.4f},{pt:.4f},{ec:.2f}\n")

    # ------------------------------- 落盘 MD -------------------------------
    hdr = alpha_labels(ALPHAS)
    md_path = RESULTS_DIR / "robustness_v1_all.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# 鲁棒性：3 领域 × 4/8/12 Robots（v1 口径）\n\n")
        f.write("**执行器口径：v1（异步顺序推进）** —— 一个 tick 内各 agent 按序决策"
                "并立即提交状态，「一步」表示一轮调度机会，一轮内可跨越多层依赖；"
                "执行守卫使用回链图节点的完整前提。\n\n")
        f.write("另有 v2 同步并行口径（tick 快照 + 末端统一提交，「一步」= 一个同步"
                "时间片）见 `robustness_v2.md`。**两种口径对「一步」的定义不同，"
                "数值不可混用。**\n\n")
        f.write(f"统计结构：{len(SEEDS)} 个 seed（每个决定一套随机动作分配并规划一次）"
                f"× {ROLLOUTS} 次执行 rollout，上报 seed 间成功率的均值 ± 标准差。\n\n")

        f.write("## 领域结构\n\n")
        f.write("| 领域 | 依赖深度 | 依赖宽度 | 动作类数 | max_steps | 说明 |\n")
        f.write("|------|---------|---------|---------|-----------|------|\n")
        desc = {
            "flat": "5 个互不依赖的一步动作，纯并行、零依赖",
            "room_package": "开门 → 搬运，四组独立镜像配对",
            "pipeline": "3 个工件各需顺序经过 5 道工序，窄而深",
        }
        for key, cn, _en, depth, width, ms, builder in DOMAIN_SPECS:
            pool, _s, _g = builder()
            f.write(f"| {cn} | {depth} | {width} | {len(pool)} | {ms} "
                    f"| {desc[key]} |\n")
        f.write("\n")

        f.write("## SR (%) mean ± std\n\n")
        for key, cn, _en, depth, width, _ms, _b in DOMAIN_SPECS:
            f.write(f"### {cn}（深度 {depth} / 宽度 {width}）\n\n")
            for num_agent in AGENT_GROUPS:
                f.write(f"**{num_agent} Robots**\n\n")
                f.write("| FP | " + " | ".join(f"α={h}" for h in hdr) + " |\n")
                f.write("|----|" + "|".join(["------"] * len(hdr)) + "|\n")
                for fp in FPS:
                    ms_, ss_ = curves[(key, num_agent, fp)]
                    f.write(f"| {fp} | "
                            + " | ".join(f"{m:.1f}±{s:.1f}"
                                         for m, s in zip(ms_, ss_))
                            + " |\n")
                f.write("\n")

        f.write("## 并行收益：TS（团队步数，α=1 / FP=0.1）\n\n")
        f.write("| 领域 | " + " | ".join(f"{n} Robots" for n in AGENT_GROUPS) + " |\n")
        f.write("|------|" + "|".join(["----------"] * len(AGENT_GROUPS)) + "|\n")
        for key, cn, _en, depth, width, _ms, _b in DOMAIN_SPECS:
            f.write(f"| {cn} (d={depth},w={width}) | "
                    + " | ".join(f"{ts_table[(key, n)]:.2f}"
                                 for n in AGENT_GROUPS) + " |\n")
        f.write("\n")

        # 冗余净增益：同一 (领域, 规模, FP) 下 α 从 0 到 1 的 SR 提升
        f.write("## 冗余净增益：α 从 0 到 1 的 SR 提升（百分点）\n\n")
        for fp in FPS:
            f.write(f"**FP = {fp}**\n\n")
            f.write("| 领域 | " + " | ".join(f"{n} Robots"
                                             for n in AGENT_GROUPS) + " |\n")
            f.write("|------|" + "|".join(["----------"] * len(AGENT_GROUPS)) + "|\n")
            for key, cn, _en, depth, width, _ms, _b in DOMAIN_SPECS:
                cells = []
                for n in AGENT_GROUPS:
                    m_, _s = curves[(key, n, fp)]
                    cells.append(f"{m_[-1] - m_[0]:+.1f}")
                f.write(f"| {cn} (d={depth},w={width}) | " + " | ".join(cells) + " |\n")
            f.write("\n")

        f.write("**读法**：\n")
        f.write("- **SR 随 α 单调上升**：同质性越高 → 每个动作被越多机器人掌握 → "
                "能力冗余越大 → 单个动作失败时有队友兜底。\n")
        f.write("- **FP 越大整条曲线越低**：动作失败概率升高压低成功率。\n")
        f.write("- **队伍越大整体越高、饱和越早**：冗余更充分，较小的 α 就能覆盖全部能力。\n")
        f.write("- **误差带最宽处集中在爬升段**：中等 α 时不同的随机分配有的凑齐了关键能力、"
                "有的没凑齐，seed 间差异最大；两端（α=0 全都缺冗余、α=1 全都齐备）反而稳定。\n")
        f.write("- **4 Robots 曲线呈阶梯状**：`generate_agents_actions` 里 "
                "`num_agents_to_assign = ceil(α × num_agent)`，4 个 agent 时 7 档 α 只映射出 "
                "1,1,2,2,3,4,4 共 4 个不同的分配强度，相邻档位取整后相同。这是参考实验分配"
                "算法本身的离散化，不是统计误差。\n")

    print(f"\n落盘：{csv_path}", flush=True)
    print(f"落盘：{md_path}", flush=True)
    print("ALL DONE", flush=True)


if __name__ == "__main__":
    main()
