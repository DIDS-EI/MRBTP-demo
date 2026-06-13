"""
proj2 · 家庭整理：三人分工的搬·擦·扫（进阶）—— 你的练习
================================================================================
骨架已搭好，填掉所有 `TODO` 后运行：

    python examples/projects/proj2_home/starter.py            # 弹出窗口可视化
    python examples/projects/proj2_home/starter.py --headless  # 无头模式

完整说明见 README.md；卡住了对照 solution/solve.py。

────────────────────────────────────────────────────────────────────────────
场景：家庭服务地图 `home`（悬浮花园里的四居室，门都**没锁**），并接入
**home_service 专属行为库**——在共享网格原语（GoTo/PickUp/Put…）之上，叠加一
整套家务语义节点：

    谓词(Condition)            动作(Action)
    ──────────────────         ──────────────────
    IsNear(a,b)   [共享]        PutNearInRoom    [共享]
    IsClean(obj)               Wipe(self,obj)            擦干净（到物体旁即可）
    IsTidy(room)               Tidy(self,room)           整理房间（进房即可）
    IsSwept(room)   [新增]      Sweep(self,room)          扫地（进房即可）
    IsStocked(obj)  [新增]      Stock(self,obj)           归置入柜（须先拿在手上）

> 这套 cond/act 和 proj3 战场域的（侦察/压制/占领）**完全不同**——两个项目各挂
> 各的 domain 库，这正是「proj2 和 proj3 的 behavior lib 各不相同」的实现。

本题用到的房间相邻关系（共享 door-2，一跳可达）：

    room-1 厨房 ─door-2─ room-3 客厅

任务（3 个浅目标，驱动三人各干一类**不同**的活）：

    1. IsNear(ball-0,ball-1) —— 把杯子(绿,room-1)搬到客厅(room-3)收纳篮(红)旁
    2. IsClean(ball-1)       —— 把收纳篮擦干净
    3. IsSwept(room-1)       —— 把厨房扫干净

异构三人分工（每人宏库 + 触发的专属动作都不一样）：

    * agent-0「搬运工」：写一段宏，复用共享 GoTo/PickUp/PutNear 把杯子摆好。
    * agent-1「清洁工」：不写宏，目标里的 IsClean 会被规划器自动回链到 Wipe。
    * agent-2「整理工」：不写宏，目标里的 IsSwept 会被规划器自动回链到 Sweep。

> 关键体会：后两人没有写死宏，只要目标谓词存在，规划器就会**自动回链**到对应
> 的专属动作，并分派给能力匹配的 agent——这就是「共享原语 + 专属动作」的威力。
────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _run import run_scenario
from app.scenario import Scenario
from scenes import home_service as home


def build_scenario() -> Scenario:
    return Scenario(
        name="proj2-home",
        env_id=home._home_map.ENV_ID,

        # TODO(1): 这个任务要几个机器人？（搬运 + 清洁 + 整理 = 3）
        num_agent=...,

        # TODO(2): 放两个球——杯子(绿)在厨房 room-1，收纳篮(红)在客厅 room-3。
        #   顺序决定编号：先写的是 ball-0，后写的是 ball-1。
        balls=...,

        # TODO(3): 三个浅目标，各驱动一类活：
        #   1) 杯子挨着收纳篮      IsNear(ball-0,ball-1)   —— 共享原语 PutNear
        #   2) 收纳篮擦干净        IsClean(ball-1)         —— 专属 Wipe
        #   3) 厨房扫干净          IsSwept(room-1)         —— 新增专属 Sweep
        goal=frozenset({
            ...,
        }),

        # TODO(4): 三人各一份宏库（长度必须 == num_agent）。
        #   常用原子动作：
        #     GoToInRoom(self, 物体, 房间)   PickUp(self, 物体)
        #     GoBtwRoom(self, 起房, 终房)    PutNearInRoom(self, 物体, 锚点, 房间)
        composite_library=[
            # —— agent-0「搬运工」：去厨房捡杯子 → 跨一跳到客厅 → 摆到收纳篮旁 ——
            # TODO(4a): 写出 取 ball-0 → GoBtwRoom(room-1→room-3) → PutNear 的 4 步宏。
            {...},
            # —— agent-1「清洁工」：留空 {}，让规划器自动回链 GoTo→Wipe 擦收纳篮 ——
            {},
            # —— agent-2「整理工」：留空 {}，让规划器自动回链 GoTo→Sweep 扫厨房 ——
            {},
        ],

        behavior_lib="home_service",   # 启用家庭服务专属库（叠加在网格原语之上）
        unlock_all_doors=True,
        room_aliases=home.ROOM_ALIASES,
        decor=home.DECOR,
        seed=0,
    )


def main() -> None:
    headless = "--headless" in sys.argv
    record_gif = "--gif" in sys.argv
    run_scenario(
        build_scenario,
        theme=home.THEME,
        success_msg="成功！搬运工摆好杯子、清洁工擦净收纳篮、整理工扫净厨房",
        headless=headless,
        record_gif=record_gif,
        gif_path="app/output/projects/proj2_home.gif",
        max_steps=600,
    )


if __name__ == "__main__":
    main()
