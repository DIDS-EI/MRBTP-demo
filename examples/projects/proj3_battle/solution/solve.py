"""
proj3 · 战场补给：三人协同的运·占·筑（挑战）—— 参考答案
================================================================================
这是 starter.py 的一份可运行参考实现。建议先独立完成 starter.py 的 TODO。

场景：战场补给地图 `battle`（星型拓扑，三据点各只通开阔区，闸口都**没锁**），
并接入 **battlefield 专属行为库**——在共享网格原语之上，叠加一整套战术语义节点：

    谓词(Condition)              动作(Action)
    ────────────────────         ────────────────────
    IsScouted(room)   [新增]      Scout(self,room)        侦察（进据点即可）
    IsThreatCleared(room)        Suppress(self,room)     压制清场（须先 IsScouted）
    IsSecured(room)              Secure(self,room)       占领（须先 IsThreatCleared）
    IsFortified(room) [新增]      Fortify(self,room)      构筑工事（独立，进据点即可）

其中 **Scout → Suppress → Secure** 串成一条真正的**三步战术链**：要让据点
「确保安全(IsSecured)」，规划器必须依次回链出 侦察→压制→占领。

> 这套 cond/act 和 proj2 家务域的（清洁/整理/归置）**完全不同**——两个项目各挂
> 各的 domain 库，这正是「proj2 和 proj3 的 behavior lib 各不相同」的实现。

地图是**星型**拓扑（据点彼此不相邻，必须经开阔区 room-0 中转）：

    room-1 蓝方基地 ─door-0─┐
    room-2 红方基地 ─door-1─┤ room-0 开阔交火区
    room-3 中央据点 ─door-2─┘

任务（3 个浅目标，驱动三人各干一类**不同**的战术活）：

    1. IsInRoom(ball-0,room-3) —— 把弹药箱(绿,蓝方基地)运抵中央据点（跨 2 跳）
    2. IsSecured(room-3)       —— 确保中央据点安全（侦察→压制→占领 三步链）
    3. IsFortified(room-1)     —— 在蓝方基地构筑工事（独立任务）

异构三人分工（每人宏库 + 触发的专属动作都不一样）：

    * agent-0「运输兵」：宏 DeliverAmmoToOutpost，经开阔区中转跨两跳运弹药。
    * agent-1「突击兵」：宏 AssaultAndSecure，把 进据点→侦察→压制→占领 这条
      三步战术链打包成一段可复用战术，一举「确保据点安全(IsSecured)」。
    * agent-2「工兵」  ：无宏，规划器自动回链 GoTo→Fortify 在蓝方基地构筑工事。

> 为何突击兵也要配宏？目标是「弹药运抵 ∧ 据点占领 ∧ 工事构筑」三者合取，
> 而 IsSecured 需 Scout→Suppress→Secure 三步回链。若把这条 depth-3 的深链
> 摊给所有 agent 在多目标合取下自由回链，三条子链（搬运 / 战术 / 构筑）的中间
> 态会相互交织成笛卡尔积，节点数爆炸（实测 >20s 超时）。把战术链收进一段
> 0-cost 宏（入口 pre 仅 IsOpen(door-2)，一步产出 IsSecured），回链深度被压到
> 1，交织积随即坍缩——规划从 20s+ 超时降到 ~1s 秒收敛。这与运输兵用
> DeliverAmmoToOutpost 收起搬运链是同一套思路。

运行：
    python examples/projects/proj3_battle/solution/solve.py            # 弹出窗口可视化
    python examples/projects/proj3_battle/solution/solve.py --headless  # 无头模式
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from _run import run_scenario
from app.scenario import Scenario
from scenes import battlefield as battle


def build_scenario() -> Scenario:
    return Scenario(
        name="proj3-battle",
        env_id=battle._battle_map.ENV_ID,
        num_agent=3,
        # ball-0(绿)=弹药箱在蓝方基地 room-1；ball-1(红)=指挥旗锚点在中央据点 room-3。
        balls=[("green", 1), ("red", 3)],
        # 三个浅目标，分别驱动「运送 / 占领(三步链) / 构筑」三类活。
        goal=frozenset({
            "IsInRoom(ball-0,room-3)",   # 弹药 → 中央据点（共享原语，跨 2 跳）
            "IsSecured(room-3)",          # 占领中央据点（Scout→Suppress→Secure 三步链）
            "IsFortified(room-1)",        # 在蓝方基地构筑工事（独立专属动作）
        }),
        composite_library=[
            # —— agent-0「运输兵」：跨开阔区中转两跳运弹药（一段可复用宏）——
            # 蓝方基地与中央据点不相邻，必须经开阔区 room-0 中转，写两段 GoBtwRoom。
            {"DeliverAmmoToOutpost": [
                "GoToInRoom(self,ball-0,room-1)",
                "PickUp(self,ball-0)",
                "GoBtwRoom(self,room-1,room-0)",   # 第 1 跳：蓝方基地→开阔区
                "GoBtwRoom(self,room-0,room-3)",   # 第 2 跳：开阔区→中央据点
                "PutInRoom(self,ball-0,room-3)",
            ]},
            # —— agent-1「突击兵」：把三步战术链打包成一段可复用战术 ——
            # 经开阔区进中央据点 → 侦察 → 压制 → 占领。位置无关的 GoBtwRoom 让
            # 宏入口只需 IsOpen(door-2)（闸口已开，落在初始状态里），整条链一举
            # 产出 IsSecured(room-3)，把深目标压成 0-cost 单步、避免合取爆炸。
            {"AssaultAndSecure": [
                "GoBtwRoom(self,room-0,room-3)",   # 经开阔区进中央据点
                "Scout(self,room-3)",              # 侦察
                "Suppress(self,room-3)",           # 压制清场（须先 IsScouted）
                "Secure(self,room-3)",             # 占领（须先 IsThreatCleared）
            ]},
            # —— agent-2「工兵」：无宏，规划器自动回链 GoTo→Fortify 构筑工事 ——
            {},
        ],
        behavior_lib="battlefield",    # 启用战场专属库（叠加在网格原语之上）
        unlock_all_doors=True,
        room_aliases=battle.ROOM_ALIASES,
        decor=battle.DECOR,
        seed=0,
    )


def main() -> None:
    headless = "--headless" in sys.argv
    record_gif = "--gif" in sys.argv
    run_scenario(
        build_scenario,
        theme=battle.THEME,
        success_msg="成功！运输兵运抵弹药、突击兵侦察压制占领据点、工兵构筑工事",
        headless=headless,
        record_gif=record_gif,
        gif_path="app/output/projects/proj3_battle.gif",
        max_steps=600,
    )


if __name__ == "__main__":
    main()
