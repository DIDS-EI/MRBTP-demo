"""用 v1 执行器复现旧版鲁棒性结果，并逐位比对已落盘的 CSV。

验证目标：证明 `results/robustness_atomic_fig.csv` 和
`results/robustness_pipeline_fig.csv` 里的数字确实来自 v1 执行器，
且用当前代码库可以完整重跑出来。

运行：
    cd /Users/yishuaicai/mywork/mrbtp-demo
    SDL_VIDEODRIVER=dummy ./.venv/bin/python examples/paper_reproduction/replay_v1.py
"""

from __future__ import annotations

import csv
import random
import sys
from pathlib import Path
from statistics import mean, pstdev

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from core.btp.multi_robot_optimal import MAOBTP                      # noqa: E402
from core.envs.gridenv.minigrid.planning_action import PlanningAction  # noqa: E402

from executor_v1 import symbolic_execute_v1                          # noqa: E402
from exp_robustness_atomic import (                                  # noqa: E402
    build_atomic_action_pool,
    build_goal,
    build_start,
    generate_agents_actions,
)

RESULTS_DIR = Path(__file__).resolve().parent / "results"

# 旧实验的固定参数（与产出 CSV 时完全一致）
ALPHAS = [k / 6 for k in range(7)]
FPS = [0.1, 0.3, 0.5]
AGENT_GROUPS = [4, 8, 12]
SEEDS = list(range(10))
ROLLOUTS = 20


def assign(pool, num_agent, alpha):
    """按同质性系数 α 把动作类随机分配给各 agent（移植自参考实验）。"""
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


def build_pipeline(num_items: int, num_stages: int):
    """流水线领域：num_items 个工件各需顺序经过 num_stages 道工序。"""
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


def run_cell(pool, start, goal, num_agent, alpha, fp, max_steps):
    """跑一格：SEEDS 套动作分配 × ROLLOUTS 次执行，返回 (SR均值, SR标准差, TS, PT, EC)。"""
    import time

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


def load_csv(path: Path):
    """读旧 CSV 成 {(num_agent, alpha, fp): (SR_mean, SR_std, TS)}。"""
    out = {}
    with open(path, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            key = (
                int(r["num_agent"]),
                round(float(r["alpha"]), 4),
                float(r["action_fail_p"]),
            )
            out[key] = (
                float(r["SR_mean"]),
                float(r["SR_std"]),
                float(r["TS"]),
            )
    return out


def replay(tag, pool, start, goal, max_steps, csv_name):
    """重跑一个领域并与旧 CSV 逐格比对。"""
    csv_path = RESULTS_DIR / csv_name
    if not csv_path.exists():
        print(f"  [SKIP] {csv_path} 不存在", flush=True)
        return None

    old = load_csv(csv_path)
    print(f"\n{'=' * 76}", flush=True)
    print(f"复现 {tag}  (max_steps={max_steps})  对照 {csv_name}", flush=True)
    print("=" * 76, flush=True)

    mismatch, checked = 0, 0
    for num_agent in AGENT_GROUPS:
        for fp in FPS:
            new_vals, old_vals = [], []
            for alpha in ALPHAS:
                sr, sd, ts, _pt, _ec = run_cell(
                    pool, start, goal, num_agent, alpha, fp, max_steps
                )
                key = (num_agent, round(alpha, 4), fp)
                new_vals.append(sr * 100)
                checked += 1
                if key not in old:
                    print(f"    [WARN] CSV 缺 {key}")
                    mismatch += 1
                    continue
                o_sr, _o_sd, _o_ts = old[key]
                old_vals.append(o_sr * 100)
                # SR 容差 0.05pp（CSV 存到 4 位小数）
                if abs(sr - o_sr) > 5e-4:
                    print(f"    [DIFF] {key}: 重跑={sr*100:.1f} CSV={o_sr*100:.1f}")
                    mismatch += 1
            print(
                f"  {num_agent:>2}R FP={fp}: 重跑 "
                + " ".join(f"{v:5.1f}" for v in new_vals),
                flush=True,
            )
            if old_vals:
                print(
                    f"           CSV  " + " ".join(f"{v:5.1f}" for v in old_vals),
                    flush=True,
                )

    verdict = "逐位一致" if mismatch == 0 else f"{mismatch} 处不符"
    print(f"\n  → 比对 {checked} 格: {verdict}", flush=True)
    return mismatch


def main():
    print("v1 执行器复现验证", flush=True)
    print("目的：证明旧 CSV/HTML 里的数字可用当前代码库完整重跑出来。", flush=True)

    total = 0

    # 领域 1：room/package（N=5，max_steps=3）
    N = 5
    m = replay(
        "room/package N=5",
        build_atomic_action_pool(N), build_start(N), build_goal(N),
        max_steps=3,
        csv_name="robustness_atomic_fig.csv",
    )
    if m is not None:
        total += m

    # 领域 2：pipeline（K=3 工件 × L=5 工序，max_steps=7）
    pool, start, goal = build_pipeline(3, 5)
    m = replay(
        "pipeline K=3 L=5",
        pool, start, goal,
        max_steps=7,
        csv_name="robustness_pipeline_fig.csv",
    )
    if m is not None:
        total += m

    print(f"\n{'=' * 76}", flush=True)
    if total == 0:
        print("全部逐位一致 —— 旧结果可复现，v1 执行器已正确保留。", flush=True)
    else:
        print(f"共 {total} 处不符，需检查 v1 执行器或参数是否与产出时一致。", flush=True)
    print("=" * 76, flush=True)
    return 0 if total == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
