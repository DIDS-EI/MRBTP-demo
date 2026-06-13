"""
proj2 · 家庭整理：三人分工的搬·擦·扫（进阶）—— 参考答案
================================================================================
这是 starter.py 的一份可运行参考实现。建议先独立完成 starter.py 的 TODO。

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

任务（3 个浅目标，驱动三人各干一类**不同**的活）：

    1. IsNear(ball-0,ball-1) —— 把杯子(绿,room-1)搬到客厅(room-3)收纳篮(红)旁
    2. IsClean(ball-1)       —— 把收纳篮擦干净
    3. IsSwept(room-1)       —— 把厨房扫干净

异构三人分工（每人宏库 + 触发的专属动作都不一样）：

    * agent-0「搬运工」：宏 TidyCupToBasket，复用共享 GoTo/PickUp/PutNear。
    * agent-1「清洁工」：无宏，规划器自动回链 GoTo→Wipe 去擦收纳篮。
    * agent-2「整理工」：无宏，规划器自动回链 GoTo→Sweep 去扫厨房。

后两人没有写死宏，目标交给规划器**自动回链**到不同的专属动作——证明「共享原语
+ 专属动作」能在同一支团队里按目标自动分派给不同的人。

运行：
    python examples/projects/proj2_home/solution/solve.py            # 弹出窗口可视化
    python examples/projects/proj2_home/solution/solve.py --headless  # 无头模式
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from _run import run_scenario
from app.scenario import Scenario
from scenes import home_service as home


def build_scenario() -> Scenario:
    return Scenario(
        name="proj2-home",
        env_id=home._home_map.ENV_ID,
        num_agent=3,
        # ball-0(绿)=杯子在厨房 room-1；ball-1(红)=收纳篮锚点在客厅 room-3。
        balls=[("green", 1), ("red", 3)],
        # 三个浅目标，分别驱动「搬运 / 清洁 / 整理」三类活。
        goal=frozenset({
            "IsNear(ball-0,ball-1)",   # 杯子 → 收纳篮旁（共享原语 PutNear）
            "IsClean(ball-1)",          # 收纳篮擦干净（专属 Wipe）
            "IsSwept(room-1)",          # 厨房扫干净（新增专属 Sweep）
        }),
        composite_library=[
            # —— agent-0「搬运工」：把杯子搬到收纳篮旁（一段可复用宏）——
            {"TidyCupToBasket": [
                "GoToInRoom(self,ball-0,room-1)",
                "PickUp(self,ball-0)",
                "GoBtwRoom(self,room-1,room-3)",   # 厨房→客厅，共享 door-2，一跳
                "PutNearInRoom(self,ball-0,ball-1,room-3)",
            ]},
            # —— agent-1「清洁工」：走到收纳篮(客厅 room-3)旁，擦干净 ——
            {"WipeBasket": [
                "GoToInRoom(self,ball-1,room-3)",
                "Wipe(self,ball-1)",
            ]},
            # —— agent-2「整理工」：进厨房 room-1，扫地 ——
            {"SweepKitchen": [
                "GoBtwRoom(self,room-0,room-1)",   # 出生在开阔区 room-0，跨 door-0 进厨房
                "Sweep(self,room-1)",
            ]},
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
