"""
Example 06 · 把行为树看出来 / 存下来 —— 打开"黑盒"
================================================================================

前面我们一直把规划器当黑盒：给 goal，拿回一棵能跑的树。这一课把树本身
**打印 + 存盘**，让你真正看见"规划器倒推出了什么结构"。

你会学到：
  1. 从 `plan.bt_list` 取出某个机器人的行为树。
  2. 用 BTML 文本形式打印树结构（缩进 = 父子层级）。
  3. 用 `plan_behavior_trees(..., save_dir=...)` 把每棵树存成
     `robot-i.bt`（文本）和 `robot-i.svg`（图），方便在浏览器/编辑器里看。

运行方式：

    python examples/walkthrough/06_inspect_tree.py

跑完后去 examples/walkthrough/output/ 看生成的 .bt 和 .svg 文件。
"""
from __future__ import annotations

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from pathlib import Path

from app.scenario import smoke_scenario
from app.planner import plan_behavior_trees


OUTPUT_DIR = Path(os.environ.get("MRBTP_EXAMPLE_OUT", "")) if os.environ.get(
    "MRBTP_EXAMPLE_OUT"
) else Path(__file__).resolve().parent / "output"


def main() -> None:
    # 用最简单的 smoke 场景（2 机器人），树小、好看清楚。
    scenario = smoke_scenario(num_agent=2)
    env = scenario.build_env(render=False)

    # save_dir 一给，planner 就会把每棵树存成 .bt + .svg（外加宏子树图）。
    plan = plan_behavior_trees(
        env, scenario, optimal=True, use_composite_actions=True,
        save_dir=str(OUTPUT_DIR),
    )

    print("=" * 60)
    print(f"规划出 {len(plan.bt_list)} 棵行为树，已存到：{OUTPUT_DIR}")
    print("=" * 60)

    # ------------------------------------------------------------------ #
    # 打印每棵树的文本结构（BTML）。缩进层级 = 树的父子关系。
    # 你会看到典型的 fallback（选择）/ sequence（顺序）+ 一堆 condition / action。
    # ------------------------------------------------------------------ #
    for i, bt in enumerate(plan.bt_list):
        print(f"\n########## 机器人 agent-{i} 的行为树（前 30 行）##########")
        # BehaviorTree.print() 会把整棵树以缩进文本（BTML）打到 stdout。
        # 这里我们直接读 planner 已经存好的 robot-i.bt 文件，截取前 30 行展示，
        # 避免完整树太长刷屏（完整版在 output/robot-i.bt 里）。
        bt_file = OUTPUT_DIR / f"robot-{i}.bt"
        if bt_file.exists():
            lines = bt_file.read_text(encoding="utf-8").splitlines()
            print("\n".join(lines[:30]))
            if len(lines) > 30:
                print(f"  ... （共 {len(lines)} 行，完整结构见 {bt_file.name}）")
        else:
            # 兜底：直接调用 BehaviorTree.print() 打印到屏幕。
            bt.print()

    # 列出实际生成的文件，方便去看。
    print("\n" + "=" * 60)
    print("output/ 下生成的文件：")
    for f in sorted(OUTPUT_DIR.glob("*")):
        print(f"  · {f.name}")
    print("=" * 60)
    print(
        "\n怎么读这棵树：\n"
        "  · fallback（?）节点：从左到右尝试子节点，有一个成功就成功——\n"
        "    通常形如'目标已满足? 否则去做能满足它的动作'。\n"
        "  · sequence（→）节点：子节点全部成功才成功，用来串起'前提→动作'。\n"
        "  · 叶子要么是 condition（判断世界状态），要么是 action（改变世界）。\n"
        "这棵树正是规划器从你的 goal 一层层倒推（back-chaining）出来的。\n"
        "把 .svg 拖进浏览器，结构会更直观。"
    )


if __name__ == "__main__":
    main()
