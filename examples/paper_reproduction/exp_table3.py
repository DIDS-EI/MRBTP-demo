"""exp_table3.py —— 复现论文 Table 3：预规划子树的 EC（扩展条件数）/ PT（规划时间）。

论文 Table 3 报告用预规划子树时的规划开销：扩展条件数 EC 与规划时间 PT，
随同质性 α 与是否 LLM 反馈变化 —— 结论：预规划子树显著减少 EC/PT。
（论文注明 LLM 平均响应 4.2s，此项 demo 无 LLM，不含在内。）

demo 适配
---------
* PT = plan.planning_time（回链搜索墙钟秒数，多次取中位数抗抖动）。
* EC = plan.expanded_num（规划器 record_expanded_num，即扩展条件数）。
* 对比维度：
    - **Subtree**（use_composite=True，预规划子树）：宏当 0-cost 单步，搜索快、EC/PT 小。
    - **Atomic**（use_composite=False，纯原子回链，无预规划）：grid 上搜索空间爆炸，
      通常打满规划器 20s 墙钟上限（``max_time_limit``）才 break，EC 冲到上万——
      **这正是论文里 Atomic 相对预规划子树的劣势体现**（EC/PT 远高）。
    - **α 档位**（make_alpha_variants，每 project 3 档）。
  规划确定性，与执行 seed 无关。Subtree 取多次中位数；Atomic 因必然超时只跑 1 次。
* 论文的「LLM 反馈 F/NF」维度 demo 无对应（无 LLM），此处省略。
  论文注明 LLM 平均响应 4.2s，demo 无 LLM，PT 只含回链搜索墙钟。

运行：
    .venv/bin/python examples/paper_reproduction/exp_table3.py
    .venv/bin/python examples/paper_reproduction/exp_table3.py --repeats 5
"""
from __future__ import annotations

import argparse
import time

from common import (discover_projects, make_alpha_variants, plan_only,
                    write_csv, write_md_table, log, RESULTS_DIR)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repeats", type=int, default=3, help="规划重复取中位数次数")
    args = ap.parse_args()

    specs = discover_projects()
    rows_csv, rows_md = [], []

    for spec in specs:
        variants = make_alpha_variants(spec)
        log(f"\n=== {spec.title} (原始 α={spec.alpha:.3f}) ===")
        for alpha, build_fn in variants:
            for label, use_comp in [("Subtree(预规划)", True),
                                    ("Atomic(无预规划)", False)]:
                # Atomic 必然打满 20s 墙钟上限，重复没意义 → 只跑 1 次
                reps = args.repeats if use_comp else 1
                t0 = time.time()
                pt, ec = plan_only(build_fn, single_expand=False,
                                   use_composite_actions=use_comp,
                                   repeats=reps)
                timed_out = (not use_comp) and pt >= 19.0
                pt_str = f"{pt:.3f}" + (" (timeout)" if timed_out else "")
                log(f"  α={alpha:.3f} {label:<16} PT={pt:.3f}s EC={ec}"
                    f"{' [TIMEOUT]' if timed_out else ''} "
                    f"({time.time()-t0:.1f}s wall)")
                rows_csv.append({
                    "project": spec.key, "alpha": alpha, "config": label,
                    "EC": ec, "PT_s": round(pt, 3),
                    "timeout": "yes" if timed_out else "no",
                })
                rows_md.append([spec.key, f"{alpha:.3f}", label,
                                str(ec), pt_str])

    write_csv(RESULTS_DIR / "table3_ec_pt.csv", rows_csv,
              ["project", "alpha", "config", "EC", "PT_s", "timeout"])
    write_md_table(
        RESULTS_DIR / "table3_ec_pt.md",
        "Table 3 复现 · 预规划子树的 EC（扩展条件数）/ PT（规划时间）",
        ["Project", "α", "Config", "EC", "PT (s)"], rows_md,
        note=(f"> Subtree 取 {args.repeats} 次规划中位数；Atomic 因必然超时只跑 1 次"
              "（规划确定性，与执行 seed 无关）。"
              "**Subtree**=用预规划宏（use_composite_actions=True），"
              "**Atomic**=不用宏、纯原子回链。看趋势：预规划子树的 EC/PT 远低于原子回链——"
              "Atomic 在 grid 上搜索爆炸，打满规划器 20s 墙钟上限（标 *timeout*）、"
              "EC 冲到上万。\n>\n"
              "> 论文 Table3 注明 LLM 平均响应 4.2s；demo 无 LLM，PT 仅含回链搜索时间，不含 LLM 调用。"))
    log(f"\n已写出 table3_* 到 {RESULTS_DIR}")


if __name__ == "__main__":
    main()
