"""
proj4 · VirtualHome 家电协同：异构三人各干各的（中等）—— 你的练习
================================================================================
骨架已搭好，填掉所有 `TODO` 后运行：

    python examples/projects/proj4_vh_appliances/starter.py
    python examples/projects/proj4_vh_appliances/starter.py --headless

完整说明见 README.md；卡住了对照 solution/solve.py。

────────────────────────────────────────────────────────────────────────────
这一题不再是网格世界：`backend="virtualhome"` 走纯符号后端，
`behavior_lib="virtualhome"` 用 standalone 域，`symbolic_task` 直接描述
「有哪些物体 / 每个机器人会哪些动作 / 初始谓词 / 目标谓词」。

    初始：IsClose(fridge)、IsSwitchedOff(tv)
    目标：IsOpen(fridge)  ∧  IsSwitchedOn(tv)

三个机器人能力**不同**（异构 action_space）：

    agent-0 开门工   Walk / Open / Close
    agent-1 电器工   Walk / SwitchOn / SwitchOff
    agent-2 搬运工   Walk / RightGrab / RightPut / RightPutIn

> 注意：`Walk(self,obj)` 的 del 会清掉所有其它 `IsNear(self,*)`，而
> `check_conflict` 禁止一个前提集合里同时出现两个 `IsNear`。本题两个目标各自
> 只依赖一个位置，所以都能被回链出来；更长的多跳链要写成宏（见 proj5）。
────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _run import run_scenario
from app.scenario import Scenario

OBJECTS = ["milk", "fridge", "kitchentable", "tv"]
INIT_STATE = ["IsClose(fridge)", "IsSwitchedOff(tv)"]


def build_scenario() -> Scenario:
    task = {
        "id": "proj4-vh-appliances",
        "objects": OBJECTS,

        # TODO(2): 三份异构动作名单，一人一份（长度必须 == num_agent）。
        #   agent-0: Walk / Open / Close
        #   agent-1: Walk / SwitchOn / SwitchOff
        #   agent-2: Walk / RightGrab / RightPut / RightPutIn
        "action_space": ...,

        "init_state": INIT_STATE,

        # TODO(3): 两个目标谓词（字符串列表）。
        #   1) 冰箱被打开          IsOpen(fridge)
        #   2) 电视被打开          IsSwitchedOn(tv)
        "goal": ...,
    }

    return Scenario(
        name="proj4-vh-appliances",
        env_id="symbolic://virtualhome",

        # TODO(1): 这个任务要几个机器人？（开门 + 电器 + 搬运 = 3）
        num_agent=...,

        balls=[],                       # 符号世界没有网格物体
        goal=frozenset(task["goal"]),
        composite_library=[],           # 本题不写宏，全交给规划器自动回链

        # TODO(4): 后端与行为库都指向新接入的 VirtualHome 域。
        backend=...,
        behavior_lib=...,

        symbolic_task=task,
    )


def main() -> None:
    run_scenario(
        build_scenario,
        theme="home",                 # 符号后端不用配色，参数保留只为接口一致
        success_msg="成功！开门工打开冰箱、电器工打开电视（搬运工待命）",
        headless="--headless" in sys.argv,
        record_gif="--gif" in sys.argv,
        attempts=1,                   # 符号执行是确定的，不需要重试
        max_steps=60,
    )


if __name__ == "__main__":
    main()
