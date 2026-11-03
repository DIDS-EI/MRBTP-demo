#!/usr/bin/env python3
"""从 CSV 生成论文版式的 3×3 鲁棒性图（PDF + PNG），带 mean ± std 阴影带。

============================== 设计依据 ==============================
版式对齐论文原图 `images/exp-robust-combined.pdf`（AAAI'25 MRBTP camera-ready）：
  - 顶部带边框的横向图例，蓝圆 / 橙方 / 绿星三种 marker
  - Times New Roman Bold 正文 + STIXGeneral 斜体数学符号（α）
  - 浅灰网格、无顶右边框、y 轴 0→100 步进 20
原图为 1×2（4/8 Robots）且**不含方差**；本脚本扩展为 3 领域 × 3 队伍规模的 3×3 网格，
并补上 ±1 标准差的同色半透明阴影带。

数据来源：`results/robustness_v1_all.csv`（v1 执行器口径），不硬编码任何数值。

运行：
    cd /Users/yishuaicai/mywork/mrbtp-demo
    ./.venv/bin/python examples/paper_reproduction/plot_robustness_grid.py
"""

from __future__ import annotations

import csv
import logging
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")           # 无显示环境，必须在 pyplot 之前设置
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402

# mathtext 在渲染 \pm 之类的数学符号时，会去 DejaVu 的符号字体里找 bold 变体，
# 而该字体只有 regular，于是刷出 "findfont: Failed to find font weight bold"。
# 这是 matplotlib 内部 fallback 的正常行为，不影响输出字形，静音即可。
logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)

RESULTS_DIR = Path(__file__).resolve().parent / "results"
CSV_PATH = RESULTS_DIR / "robustness_v1_all.csv"

# ----------------------------- 版式常量 -----------------------------
# 对齐论文原图配色（matplotlib tab10 的前三色，与参考 PDF 取样一致）
COLORS = {0.1: "#1f77b4", 0.3: "#ff7f0e", 0.5: "#2ca02c"}
MARKERS = {0.1: "o", 0.3: "s", 0.5: "*"}
MARKER_SIZES = {0.1: 7.0, 0.3: 6.5, 0.5: 11.0}   # 星形视觉偏小，需放大
FPS = [0.1, 0.3, 0.5]

BAND_ALPHA = 0.20       # 阴影带不透明度
LINE_WIDTH = 2.2
GRID_COLOR = "#d9d9d9"

DOMAIN_ORDER = ["flat", "room_package", "pipeline"]
DOMAIN_TITLES = {
    "flat": "Domain A  ·  flat",
    "room_package": "Domain B  ·  room / package",
    "pipeline": "Domain C  ·  pipeline",
}
AGENT_GROUPS = [4, 8, 12]


def setup_style() -> None:
    """还原参考 PDF 的字体与坐标轴风格。"""
    plt.rcParams.update({
        "font.family": "serif",
        "font.serif": ["Times New Roman", "DejaVu Serif"],
        "font.weight": "bold",
        "axes.labelweight": "bold",
        "axes.titleweight": "bold",
        # 数学符号（α）：参考 PDF 内嵌的是 STIXGeneral-BoldItalic。
        # 用 custom 字集精确指定槽位。注意必须把 cal/sf/tt 也一起覆盖，
        # 否则未覆盖的槽位会回落到默认字集并刷出
        # "findfont: Failed to find font weight bold" 警告。
        "mathtext.fontset": "custom",
        "mathtext.it": "STIXGeneral:italic:bold",
        "mathtext.rm": "STIXGeneral:bold",
        "mathtext.bf": "STIXGeneral:bold",
        "mathtext.cal": "STIXGeneral:italic:bold",
        "mathtext.sf": "STIXGeneral:bold",
        "mathtext.tt": "STIXGeneral:bold",
        "mathtext.default": "it",
        "axes.linewidth": 1.3,
        "axes.edgecolor": "#333333",
        "xtick.major.width": 1.2,
        "ytick.major.width": 1.2,
        "xtick.labelsize": 15,
        "ytick.labelsize": 15,
        "axes.grid": True,
        "grid.color": GRID_COLOR,
        "grid.linewidth": 0.9,
        "grid.alpha": 1.0,
        "pdf.fonttype": 42,     # TrueType 内嵌，避免出版方拒稿
        "ps.fonttype": 42,
        # 不用 bbox_inches="tight"：它会在保存时重排布局，使 subplots_adjust 后
        # 用 get_position() 定位的行标题发生偏移。改为在 subplots_adjust 里
        # 显式留足边距。
        "savefig.bbox": None,
    })


def alpha_label(a: float, denom: int = 6) -> str:
    """把 α 值渲染成分数标签，分母固定为 denom（不约分）。

    注意：**不要用 Fraction**。Fraction 会自动约分（2/6 → 1/3），若再取其
    numerator 拼回 "/6" 就会得到错误的 2/6 → 1/6。直接用 round(a*denom) 做分子。
    """
    k = round(a * denom)
    if k == 0:
        return "0"
    if k == denom:
        return "1"
    return f"{k}/{denom}"


def load_curves(csv_path: Path):
    """读 CSV → {(domain, num_agent, fp): (alphas, means%, stds%)}，外加领域元信息。"""
    if not csv_path.exists():
        sys.exit(f"找不到数据文件: {csv_path}\n"
                 f"请先运行 exp_robustness_v1_all.py 生成。")

    bucket = defaultdict(list)
    meta = {}
    with open(csv_path, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            dom = r["domain"]
            meta[dom] = (int(r["depth"]), int(r["width"]))
            key = (dom, int(r["num_agent"]), float(r["action_fail_p"]))
            bucket[key].append((
                float(r["alpha"]),
                float(r["SR_mean"]) * 100.0,
                float(r["SR_std"]) * 100.0,
            ))

    curves = {}
    for key, pts in bucket.items():
        pts.sort(key=lambda t: t[0])
        curves[key] = (
            [p[0] for p in pts],
            [p[1] for p in pts],
            [p[2] for p in pts],
        )
    return curves, meta


def draw_panel(ax, curves, domain, num_agent, *, show_ylabel, show_xlabel,
               scale: float = 1.0):
    """画一个子图：三条 FP 曲线 + 同色 ±1σ 阴影带。scale 用于窄版等比缩小。"""
    xs_ref = None
    for fp in FPS:
        key = (domain, num_agent, fp)
        if key not in curves:
            continue
        alphas, means, stds = curves[key]
        xs = list(range(len(alphas)))       # 等距刻度，与参考图一致
        xs_ref = (xs, alphas)

        # 阴影带裁剪到 [0, 100]，否则会溢出坐标轴造成视觉误导
        lo = [max(0.0, m - s) for m, s in zip(means, stds)]
        hi = [min(100.0, m + s) for m, s in zip(means, stds)]
        ax.fill_between(xs, lo, hi, color=COLORS[fp], alpha=BAND_ALPHA,
                        linewidth=0, zorder=2)

        ax.plot(xs, means,
                color=COLORS[fp], marker=MARKERS[fp],
                markersize=MARKER_SIZES[fp] * scale,
                linewidth=LINE_WIDTH * scale,
                markeredgewidth=0, zorder=3, clip_on=False)

    if xs_ref is None:
        return

    xs, alphas = xs_ref
    ax.set_xticks(xs)
    ax.set_xticklabels([alpha_label(a) for a in alphas])
    ax.tick_params(axis="both", labelsize=15 * scale)
    ax.set_xlim(-0.25, len(xs) - 0.75)
    ax.set_ylim(-3, 103)
    ax.set_yticks([0, 20, 40, 60, 80, 100])
    ax.set_axisbelow(True)                       # 网格压在曲线之下
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)

    ax.set_title(f"{num_agent} Robots", fontsize=17 * scale, pad=7 * scale)
    if show_ylabel:
        ax.set_ylabel("Success Rate (%)", fontsize=16 * scale, labelpad=5)
    if show_xlabel:
        ax.set_xlabel(r"Homogeneity $\alpha$", fontsize=16 * scale, labelpad=4)


def build_figure(curves, meta, *, figsize, scale=1.0):
    """构建 3×3 图。scale 用于窄版整体缩小字号与 marker。"""
    n_rows, n_cols = len(DOMAIN_ORDER), len(AGENT_GROUPS)
    fig, axes = plt.subplots(n_rows, n_cols, figsize=figsize)

    for i, domain in enumerate(DOMAIN_ORDER):
        for j, num_agent in enumerate(AGENT_GROUPS):
            draw_panel(
                axes[i][j], curves, domain, num_agent,
                show_ylabel=(j == 0),
                # 每行都标 x 轴：三行是彼此独立的领域，各自独立读图
                show_xlabel=True,
                scale=scale,
            )

    # 顶部带边框的横向图例（对齐参考图）
    handles = [
        Line2D([0], [0], color=COLORS[fp], marker=MARKERS[fp],
               markersize=MARKER_SIZES[fp] * scale, linewidth=LINE_WIDTH * scale,
               markeredgewidth=0, label=f"FP = {fp}")
        for fp in FPS
    ]
    handles.append(
        matplotlib.patches.Patch(facecolor="#7f7f7f", alpha=BAND_ALPHA,
                                 linewidth=0,
                                 # 数字用 \mathrm 强制正体，否则 mathtext.default=it
                                 # 会把 "1" 也渲染成斜体
                                 label=r"$\pm\mathrm{1}$ std")
    )
    leg = fig.legend(
        handles=handles, loc="upper center", bbox_to_anchor=(0.5, 0.995),
        ncol=len(handles), frameon=True, fancybox=False,
        edgecolor="#999999", framealpha=1.0,
        fontsize=17 * scale, handlelength=2.4,
        columnspacing=2.4 * scale, borderpad=0.55,
    )
    leg.get_frame().set_linewidth(1.1)

    # top 留白要同时容纳图例与首行行标题，否则首行标题会被图例压住
    fig.subplots_adjust(left=0.075, right=0.985, top=0.872, bottom=0.055,
                        hspace=0.62, wspace=0.24)

    # 行标题必须在 subplots_adjust 之后画：它依赖子图的最终位置坐标
    for i, domain in enumerate(DOMAIN_ORDER):
        depth, width = meta.get(domain, (None, None))
        label = DOMAIN_TITLES[domain]
        if depth is not None:
            label += f"      (depth {depth} / width {width})"
        row_axes = axes[i]
        x_center = (
            row_axes[0].get_position().x0 + row_axes[-1].get_position().x1
        ) / 2.0
        y_top = row_axes[0].get_position().y1
        fig.text(
            x_center, y_top + 0.028, label,
            fontsize=18 * scale, fontweight="bold", va="bottom", ha="center",
        )
    return fig


def main() -> int:
    setup_style()
    curves, meta = load_curves(CSV_PATH)

    # 宽版（单栏跨页 / 幻灯片）与窄版（双栏论文单栏宽约 3.4in × 3 列）
    variants = [
        ("exp_robust_grid_3x3",        (15.6, 12.4), 1.00),
        ("exp_robust_grid_3x3_narrow", (10.4,  9.2), 0.74),
    ]
    for stem, figsize, scale in variants:
        fig = build_figure(curves, meta, figsize=figsize, scale=scale)
        pdf_path = RESULTS_DIR / f"{stem}.pdf"
        png_path = RESULTS_DIR / f"{stem}.png"
        fig.savefig(pdf_path)
        fig.savefig(png_path, dpi=200)
        plt.close(fig)
        print(f"落盘: {pdf_path}")
        print(f"落盘: {png_path}")

    # 打印实际绘制的数值，便于人工核对图与数据是否一致
    print("\n绘制数据核对（SR% mean±std）:")
    for domain in DOMAIN_ORDER:
        print(f"  [{domain}]")
        for num_agent in AGENT_GROUPS:
            for fp in FPS:
                key = (domain, num_agent, fp)
                if key not in curves:
                    continue
                _a, m, s = curves[key]
                print(f"    {num_agent:>2}R FP={fp}: "
                      + " ".join(f"{x:.1f}±{y:.1f}" for x, y in zip(m, s)))
    return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
