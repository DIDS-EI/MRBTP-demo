"""exp_table2.py —— 复现论文 Table 2：意图共享的通信开销 Comm（及 TS/RS）。

论文 Table 2 对比三种配置（Subtree / Subtree+IS / Atomic+IS）在有/无 LLM 反馈下的
并行步数 TS、总步数 RS、通信次数 Comm —— 核心结论：意图共享带来通信开销 Comm，
且配置越"原子化/协作弱"广播越频繁。

demo 适配（如实报告口径）
------------------------
demo 无 LLM、无纯原子可执行 baseline，故聚焦本表最可靠复现的维度——**意图共享的通信开销**：
  * **Subtree**    ：预规划宏 + cross-tree 全扩展，但**不**意图共享
                     （share_belief=False）→ executor 关闭广播 → **Comm=0**
  * **Subtree IS** ：预规划宏 + cross-tree 全扩展 + 意图共享
                     （share_belief=True）→ agent 接下宏任务时广播子目标 → **Comm>0**
两配置都 use_composite=True、single_expand=False。跨 3 档 α 观察 Comm 随异构度变化。
指标：TS / RS / Comm（Comm 由 monkeypatch 计数广播次数）。FP=0，多 seed 取成功回合均值。

⚠️ 诚实说明：Comm 维度能忠实复现论文口径（有无意图共享 → 有无广播）；但 TS/RS 的
  "意图共享更省步"趋势在 demo 简单场景里不显著（见 Table1 说明）。此表照实呈现。"""
from __future__ import annotations

import argparse
import time
from statistics import mean

from common import (discover_projects, make_alpha_variants, run_once,
                    write_csv, write_md_table, log, RESULTS_DIR)


CONFIGS = [
    # (标签, share_belief)  —— 都 use_composite=True, single_expand=False
    ("Subtree",    False),
    ("Subtree IS", True),
]


def run_cell(build_fn, *, share, seeds):
    ts, rs, comm = [], [], []
    ok = 0
    for s in seeds:
        m = run_once(build_fn, single_expand=False, share_belief=share,
                     use_composite_actions=True, fp=0.0, seed=s)
        if m.success:
            ok += 1
            ts.append(m.team_steps)
            rs.append(m.robot_steps)
            comm.append(m.comm)
    return (ok / len(seeds),
            mean(ts) if ts else None,
            mean(rs) if rs else None,
            mean(comm) if comm else None)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=5)
    args = ap.parse_args()
    seeds = list(range(args.seeds))

    specs = discover_projects()
    rows_csv, rows_md = [], []

    for spec in specs:
        variants = make_alpha_variants(spec)
        log(f"\n=== {spec.title} (原始 α={spec.alpha:.3f}) ===")
        for alpha, build_fn in variants:
            for label, share in CONFIGS:
                t0 = time.time()
                sr, ts, rs, comm = run_cell(build_fn, share=share, seeds=seeds)
                log(f"  α={alpha:.3f} {label:<11} SR={sr:.2f} TS={ts} RS={rs} "
                    f"Comm={comm} ({time.time()-t0:.1f}s)")
                rows_csv.append({
                    "project": spec.key, "alpha": alpha, "config": label,
                    "SR": round(sr, 3),
                    "TS": round(ts, 1) if ts is not None else "",
                    "RS": round(rs, 1) if rs is not None else "",
                    "Comm": round(comm, 1) if comm is not None else "",
                    "n_seeds": len(seeds),
                })
                rows_md.append([
                    spec.key, f"{alpha:.3f}", label, f"{sr:.2f}",
                    f"{ts:.1f}" if ts is not None else "—",
                    f"{rs:.1f}" if rs is not None else "—",
                    f"{comm:.1f}" if comm is not None else "—",
                ])

    write_csv(RESULTS_DIR / "table2_subtree_is_comm.csv", rows_csv,
              ["project", "alpha", "config", "SR", "TS", "RS", "Comm", "n_seeds"])
    write_md_table(
        RESULTS_DIR / "table2_subtree_is_comm.md",
        "Table 2 复现 · 意图共享的通信开销 Comm（及 TS / RS）",
        ["Project", "α", "Config", "SR", "TS", "RS", "Comm"], rows_md,
        note=(f"> 每格 {len(seeds)} seeds，FP=0，两配置都用预规划宏（use_composite=True）、"
              "cross-tree 全扩展（single_expand=False），TS/RS/Comm 为成功回合均值。\n>\n"
              "> **Subtree**=不意图共享 → executor 关闭广播 → **Comm=0**；"
              "**Subtree IS**=意图共享 → agent 接下宏任务时广播子目标 → **Comm>0**。"
              "这是本表最可靠复现论文的维度（有无意图共享 → 有无通信开销）。\n>\n"
              "> ⚠️ TS/RS 的「意图共享更省步」趋势在 demo 简单场景不显著（见 Table1 说明）；"
              "demo 无 LLM，故未复现论文的 F/NF（反馈迭代）维度。此表照实呈现。"))
    log(f"\n已写出 table2_* 到 {RESULTS_DIR}")


if __name__ == "__main__":
    main()
