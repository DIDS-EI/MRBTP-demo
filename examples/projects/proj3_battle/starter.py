"""
proj3 · 战场补给：三人协同的运·占·筑（挑战）—— 你的练习
================================================================================
骨架已搭好，填掉所有 `TODO` 后运行：

    python examples/projects/proj3_battle/starter.py            # 弹出窗口可视化
    python examples/projects/proj3_battle/starter.py --headless  # 无头模式

完整说明见 README.md；卡住了对照 solution/solve.py。

────────────────────────────────────────────────────────────────────────────
场景：战场补给地图 `battle`（开阔交火区上散布三个据点，闸口都**没锁**），并接入
**battlefield 专属行为库**——在共享网格原语之上，叠加一整套战术语义节点：

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

    * agent-0「运输兵」：写一段宏，经开阔区中转**跨两跳**运弹药。
    * agent-1「突击兵」：写一段宏，把 进据点→侦察→压制→占领 这条三步战术链
      打包起来，一举「确保据点安全(IsSecured)」。
    * agent-2「工兵」  ：不写宏，目标 IsFortified 会被自动回链成 GoTo→Fortify。

> 关键体会①：那条战术链 Scout→Suppress→Secure 不是凭空写死的——它由谓词
> 依赖串起来（Secure←IsThreatCleared←Suppress←IsScouted←Scout）。你在宏里
> 按顺序列出三步，宏规划器会校验这条依赖链确实成立。
> 关键体会②：为什么突击兵也得配宏？目标是「运弹 ∧ 占领 ∧ 构筑」三者合取，
> 其中 IsSecured 是 depth-3 的深链。若让所有 agent 在合取目标下自由回链这条
> 深链，三条子链的中间态会相互交织成笛卡尔积、节点爆炸（实测 >20s 超时）。
> 把它收进一段 0-cost 宏，回链深度压到 1，规划立刻从 20s+ 降到 ~1s。这跟
> 运输兵用宏收起搬运链是同一招。
────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _run import run_scenario
from app.scenario import Scenario
# 直接复用成品场景 `battle` 的独立地图 + 据点中文别名 + 掩体元数据。
from scenes import battlefield as battle


def build_scenario() -> Scenario:
    return Scenario(
        name="proj3-battle",
        env_id=battle._battle_map.ENV_ID,

        # TODO(1): 这个任务要几个机器人？（运弹 + 占领 + 构筑 = 3）
        num_agent=...,

        # TODO(2): 放两个球——弹药箱(绿)在蓝方基地 room-1，指挥旗锚点(红)在中央据点 room-3。
        #   顺序决定编号：先写的是 ball-0，后写的是 ball-1。
        balls=...,

        # TODO(3): 三个浅目标，各驱动一类战术活：
        #   1) 弹药运抵中央据点    IsInRoom(ball-0,room-3) —— 共享原语，跨 2 跳
        #   2) 中央据点确保安全    IsSecured(room-3)       —— 专属三步链 Scout→Suppress→Secure
        #   3) 蓝方基地构筑工事    IsFortified(room-1)     —— 新增专属 Fortify
        goal=frozenset({
            ...,
        }),

        # TODO(4): 三人各一份宏库（长度必须 == num_agent）。
        composite_library=[
            # —— agent-0「运输兵」：捡弹药 → 跨第 1 跳(1→0) → 跨第 2 跳(0→3) → 放进 room-3 ——
            # TODO(4a): 注意 GoBtwRoom 要写**两段相邻**的，不能一步从 room-1 跨到 room-3！
            #   （蓝方基地和中央据点不相邻，必须经开阔区 room-0 中转。）
            {...},
            # —— agent-1「突击兵」：把三步战术链打包成一段可复用战术 ——
            # TODO(4b): 写一段宏 "AssaultAndSecure"，依次列出 4 步：
            #   1) GoBtwRoom(self,room-0,room-3)  经开阔区进中央据点
            #   2) Scout(self,room-3)             侦察
            #   3) Suppress(self,room-3)          压制清场（须先 IsScouted）
            #   4) Secure(self,room-3)            占领（须先 IsThreatCleared）
            {...},
            # —— agent-2「工兵」：留空 {}，让规划器自动回链 GoTo→Fortify 构筑工事 ——
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
