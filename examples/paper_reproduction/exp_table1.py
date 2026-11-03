"""exp_table1.py —— 复现论文 Table 1：BT-Expansion (baseline) vs MRBTP。

论文 Table 1（warehouse，4 robots，500 trials）比较两种方法在不同同质性 α 下的
SR / TS / RS —— 结论：MRBTP 在成功率、并行步数（TS）、总步数（RS）上都优于
BT-Expansion baseline，且随 α 变化保持稳定。

demo 适配（如实报告口径）
------------------------
* **方法维度**：demo 里没有两套独立求解器；用意图共享开关 ``share_belief`` 区分——
  两种配置都用预规划宏（use_composite=True）、都 cross-tree 全扩展（single_expand=False）：
    - ``share_belief=False``（baseline ≈ BT-Expansion）：各 agent 不共享意图，各自为战。
    - ``share_belief=True`` （MRBTP）：意图共享，协作接管子目标。
* **α 维度**：用 ``make_alpha_variants`` 在每个 project 上构造 3 档 α。
* **指标**：SR（多 seed 成功率）、TS（成功回合并行步数均值）、RS（各 agent 步数之和均值）。

⚠️ 诚实说明：在 mrbtp-demo 的 proj2/proj3 这两个网格场景里，任务相对简单、协作收益
  不明显——实测两种配置 SR 都 100%，TS/RS 也无稳定差异（proj2 无共享反而略小、
  proj3 基本持平）。因此本表**未能复现**论文「MRBTP 的 TS/RS 显著低于 baseline」的
  执行效率趋势；这是 demo 场景规模所限，不是方法本身的问题。能忠实复现论文趋势的是
  **Table3（EC/PT）与 Fig4(a)（SR vs FP）**，见对应脚本。此表照实呈现、不修饰。

运行：
    .venv/bin/python examples/paper_reproduction/exp_table1.py
    .venv/bin/python examples/paper_reproduction/exp_table1.py --seeds 8   # 每格 8 个 seed
"""
from __future__ import annotations

import argparse
import time
from statistics import mean

import common
from common import (discover_projects, make_alpha_variants, run_once,
                    write_csv, write_md_table, log, RESULTS_DIR)


def run_cell(build_fn, *, share_belief: bool, seeds):
    """一格：baseline/MRBTP × 一个 α 档，多 seed 跑，返回 (SR, TS_mean, RS_mean)。"""
    ok = 0
    ts, rs = [], []
    for s in seeds:
        m = run_once(build_fn, single_expand=False, share_belief=share_belief,
                     use_composite_actions=True, fp=0.0, seed=s)
        if m.success:
            ok += 1
            ts.append(m.team_steps)
            rs.append(m.robot_steps)
    sr = ok / len(seeds)
    return sr, (mean(ts) if ts else None), (mean(rs) if rs else None)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=5, help="每格执行 seed 数")
    args = ap.parse_args()
    seeds = list(range(args.seeds))

    specs = discover_projects()
    rows_csv = []
    rows_md = []

    for spec in specs:
        variants = make_alpha_variants(spec)
        log(f"\n=== {spec.title} (原始 α={spec.alpha:.3f}) ===")
        for alpha, build_fn in variants:
            for method, share in [("BT-Expansion", False), ("MRBTP", True)]:
                t0 = time.time()
                sr, ts, rs = run_cell(build_fn, share_belief=share, seeds=seeds)
                log(f"  α={alpha:.3f} {method:<12} "
                    f"SR={sr:.2f} TS={ts} RS={rs} ({time.time()-t0:.1f}s)")
                rows_csv.append({
                    "project": spec.key, "alpha": alpha, "method": method,
                    "SR": round(sr, 3),
                    "TS": round(ts, 1) if ts is not None else "",
                    "RS": round(rs, 1) if rs is not None else "",
                    "n_seeds": len(seeds),
                })
                rows_md.append([
                    spec.key, f"{alpha:.3f}", method, f"{sr:.2f}",
                    f"{ts:.1f}" if ts is not None else "—",
                    f"{rs:.1f}" if rs is not None else "—",
                ])

    write_csv(RESULTS_DIR / "table1_baseline_vs_mrbtp.csv", rows_csv,
              ["project", "alpha", "method", "SR", "TS", "RS", "n_seeds"])
    write_md_table(
        RESULTS_DIR / "table1_baseline_vs_mrbtp.md",
        "Table 1 复现 · BT-Expansion (baseline) vs MRBTP",
        ["Project", "α", "Method", "SR", "TS", "RS"],
        rows_md,
        note=(f"> 每格 {len(seeds)} seeds，都用预规划宏（`use_composite_actions=True`）、"
              "cross-tree 全扩展（`single_expand=False`）。"
              "BT-Expansion=无意图共享（`share_belief=False`，各自为战），"
              "MRBTP=意图共享（`share_belief=True`）。TS/RS 为成功回合均值。\n>\n"
              "> ⚠️ **如实说明**：论文 Table1 用 warehouse/4-robot/500-trial 的真实 MRBTP，"
              "MRBTP 的 SR≥baseline、TS/RS≤baseline。但在 demo 的 proj2/proj3 网格场景里"
              "任务简单、协作收益不明显——两配置 SR 都 100%、TS/RS 无稳定优势（proj2 无共享"
              "反而略小），故本表**未复现**论文的执行效率趋势。能忠实复现论文趋势的是 "
              "**Table3（EC/PT）与 Fig4(a)（SR vs FP）**。此表照实呈现、不修饰。"))
    log(f"\n已写出 {RESULTS_DIR/'table1_baseline_vs_mrbtp.csv'} 与 .md")


if __name__ == "__main__":
    main()
