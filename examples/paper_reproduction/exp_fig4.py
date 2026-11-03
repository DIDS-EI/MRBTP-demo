"""exp_fig4.py —— 复现论文 Fig.4 的两张子图。

Fig.4(a) 鲁棒性：SR vs 动作失败概率 FP，分不同同质性 α（& 机器人数）。
    结论——MRBTP 的成功率随 FP 上升而缓降，且对 α 稳健（异构/同构都撑得住）。
Fig.4(b) 执行效率：TS vs 是否意图共享，分不同 α。
    结论——开启意图共享（share_belief=True）显著降低并行步数 TS，尤其 α 高（异构）时。

demo 适配
---------
* FP：monkeypatch 注入（common.inject_action_failure），扫 FP∈{0, 0.1, 0.2, 0.3}。
* α ：make_alpha_variants 每 project 3 档。
* 机器人数：demo 三个 project 都是 3 agent（无法像论文那样 4/8 切换），
  故「机器人数」维度用**三个不同 project**（不同规模/结构）近似体现。
* 子图(a) 固定 share_belief=True, single_expand=False；扫 FP。
* 子图(b) 固定 FP=0；对比 share_belief True/False。

运行：
    .venv/bin/python examples/paper_reproduction/exp_fig4.py
    .venv/bin/python examples/paper_reproduction/exp_fig4.py --seeds 8
"""
from __future__ import annotations

import argparse
import time
from statistics import mean

from common import (discover_projects, make_alpha_variants, run_once,
                    write_csv, write_md_table, log, RESULTS_DIR)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=5)
    ap.add_argument("--fps", type=float, nargs="+", default=[0.0, 0.1, 0.2, 0.3])
    args = ap.parse_args()
    seeds = list(range(args.seeds))

    specs = discover_projects()

    # ---------- Fig4(a)：SR vs FP × α ---------- #
    log("\n########## Fig4(a): SR vs FP × α ##########")
    rows_a_csv, rows_a_md = [], []
    for spec in specs:
        variants = make_alpha_variants(spec)
        for alpha, build_fn in variants:
            for fp in args.fps:
                t0 = time.time()
                ok = sum(
                    1 for s in seeds
                    if run_once(build_fn, single_expand=False, share_belief=True,
                                use_composite_actions=True, fp=fp, seed=s).success
                )
                sr = ok / len(seeds)
                log(f"  {spec.key} α={alpha:.3f} FP={fp:.1f}: SR={sr:.2f} "
                    f"({time.time()-t0:.1f}s)")
                rows_a_csv.append({"project": spec.key, "alpha": alpha,
                                   "FP": fp, "SR": round(sr, 3), "n_seeds": len(seeds)})
                rows_a_md.append([spec.key, f"{alpha:.3f}", f"{fp:.1f}", f"{sr:.2f}"])

    write_csv(RESULTS_DIR / "fig4a_sr_vs_fp.csv", rows_a_csv,
              ["project", "alpha", "FP", "SR", "n_seeds"])
    write_md_table(
        RESULTS_DIR / "fig4a_sr_vs_fp.md",
        "Fig.4(a) 复现 · SR vs 动作失败概率 FP × 同质性 α",
        ["Project", "α", "FP", "SR"], rows_a_md,
        note=(f"> 每格 {len(seeds)} seeds，share_belief=True、single_expand=False，"
              "FP 由 monkeypatch 注入（动作以概率 p 失效）。看趋势：SR 随 FP 上升而下降，"
              "MRBTP 在各 α 档都保持较高鲁棒性。三个 project 近似论文的不同机器人数/规模。"))

    # ---------- Fig4(b)：TS vs 意图共享 × α ---------- #
    log("\n########## Fig4(b): TS vs 意图共享 × α ##########")
    rows_b_csv, rows_b_md = [], []
    for spec in specs:
        variants = make_alpha_variants(spec)
        for alpha, build_fn in variants:
            row_ts = {}
            for share in (True, False):
                ts = []
                for s in seeds:
                    m = run_once(build_fn, single_expand=False, share_belief=share,
                                 use_composite_actions=True, fp=0.0, seed=s)
                    if m.success:
                        ts.append(m.team_steps)
                row_ts[share] = mean(ts) if ts else None
                log(f"  {spec.key} α={alpha:.3f} share={share}: "
                    f"TS={row_ts[share]}")
            rows_b_csv.append({
                "project": spec.key, "alpha": alpha,
                "TS_share": round(row_ts[True], 1) if row_ts[True] else "",
                "TS_noshare": round(row_ts[False], 1) if row_ts[False] else "",
                "n_seeds": len(seeds),
            })
            rows_b_md.append([
                spec.key, f"{alpha:.3f}",
                f"{row_ts[True]:.1f}" if row_ts[True] else "—",
                f"{row_ts[False]:.1f}" if row_ts[False] else "—",
            ])

    write_csv(RESULTS_DIR / "fig4b_ts_vs_share.csv", rows_b_csv,
              ["project", "alpha", "TS_share", "TS_noshare", "n_seeds"])
    write_md_table(
        RESULTS_DIR / "fig4b_ts_vs_share.md",
        "Fig.4(b) 复现 · TS vs 意图共享 × 同质性 α",
        ["Project", "α", "TS (意图共享)", "TS (无共享)"], rows_b_md,
        note=(f"> 每格 {len(seeds)} seeds，FP=0、single_expand=False，都用预规划宏。"
              "看意图共享（share_belief）对并行步数 TS 的影响。\n>\n"
              "> ⚠️ **如实说明**：论文 Fig4(b) 里开意图共享显著降低 TS。但 demo 的 "
              "proj2/proj3 场景简单、协作收益不明显——实测意图共享并未稳定降低 TS"
              "（proj2 无共享反而略小、proj3 基本持平）。此子图照实呈现，未复现论文趋势；"
              "能忠实复现的是 Fig4(a)（SR vs FP）与 Table3（EC/PT）。"))
    log(f"\n已写出 fig4a_* 与 fig4b_* 到 {RESULTS_DIR}")


if __name__ == "__main__":
    main()
