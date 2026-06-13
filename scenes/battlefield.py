"""battlefield —— 战场补给场景（纯数据声明，3 据点独立地图版）。

一支补给小队在开阔战场上把弹药运进据点并确保其安全。底座换成了本场景**专属**
的 ``_battle_map``（不再和 home 共用 ``_rooms4``）：开阔交火区上散布三个据点——
蓝方基地 / 红方基地 / 中央据点，用闸口（门）连通，掩体障碍点缀其间。完全对齐
``docs/PLUGGABLE_BACKEND_DESIGN.html`` §7 的设计图。

据点编号 ↔ 语义（DFS 列优先扫描决定，详见 ``_battle_map`` 顶部说明）：

    room-0 = 开阔交火区   room-1 = 蓝方基地
    room-2 = 红方基地     room-3 = 中央据点

任务（goal）—— 刻意只设一个「短跳」目标，保证每次跑 demo 都在一秒内规划完：

    * 把弹药箱（ball-0，在蓝方基地 room-1）运进中央据点 room-3，并确保据点安全。

闸口都不上锁，对应「假设任何单位都能通过闸口」的设定：据点仍由门*对象*分隔
（房间识别 DFS 把门当墙），但无需先去取通行卡。

掩体怎么进画面（解耦点，同家庭服务的家具）
------------------------------------------
掩体 / 障碍**不进网格几何**，而是作为下面的 ``DECOR`` 场景元数据：``build_env``
把它挂到 env 的 ``scene_decor`` 上，**只有渲染器**读它来画。一期不影响寻路与
规划，规划内核零改动。

配色主题：``battle``（蓝方基地冷蓝 / 红方基地暗红 / 中央据点暖黄 / 开阔区中性）。
"""
from __future__ import annotations

# Importing _battle_map registers the MRBTP-BattleMap-v0 gym id used below.
from scenes import _battle_map
from app.scenario import Scenario, CompositeLibrary, _fit_library_to_agents

NAME = "battle"
THEME = "battle"

#: 据点编号 → 中文语义别名。仅渲染层 / 文档使用；规划器内部只认 room-i。
#: 编号顺序由 ``_battle_map`` 的列优先 DFS 决定（开阔区抢到 room-0），不是直觉
#: 顺序——这正是「内核只认编号，人类靠别名读懂」解耦的活教材。
ROOM_ALIASES = {
    0: "开阔交火区",
    1: "蓝方基地",
    2: "红方基地",
    3: "中央据点",
}

#: 掩体 / 装饰元数据（**不进网格几何**，只有渲染器读）。字段同家庭服务 DECOR：
#:   kind  —— "cover" 画成实心障碍块；"supply" 画补给标记
#:   cell  —— 占据的格子 (x, y)
#:   size  —— 跨几格 (w, h)
#:   label —— 标签
#: 坐标参照 _battle_map：开阔交火区 room-0 是环绕三据点的大连通域，掩体摆在其中。
DECOR = [
    # 开阔交火区里的掩体障碍（纯视觉，一期不影响寻路）
    {"kind": "cover", "cell": (9, 2), "size": (1, 3), "label": "掩体"},
    {"kind": "cover", "cell": (10, 9), "size": (1, 3), "label": "掩体"},
    {"kind": "cover", "cell": (9, 11), "size": (3, 1), "label": "掩体"},
    {"kind": "cover", "cell": (16, 2), "size": (2, 1), "label": "掩体"},
    # 补给标记（视觉提示，真正可运送的弹药是 ball-0）
    {"kind": "supply", "cell": (15, 11), "size": (1, 1), "label": "补给点"},
]


def make(num_agent: int = 2) -> Scenario:
    """造一个「战场补给」场景实例（3 据点独立地图、无锁、含专属语义 + 掩体元数据）。

    这一版接入了 *battlefield* 专属行为库（``core/envs/domains/battlefield``）：
    在共享网格原语之上新增了一组战术语义节点——

        * 谓词 ``IsThreatCleared(<room>)`` / ``IsSecured(<room>)``
        * 动作 ``Suppress(self,<room>)`` / ``Secure(self,<room>)``

    其中 ``Secure`` 的前置依赖 ``IsThreatCleared``，这给战场域一个真正的**两步
    战术规划**：要据点「确保安全」，规划器必须先回链出「压制清场」再「占领」。

    目标（goal）同时包含「运送」和「占领」，驱动共享原语与专属动作协同：

        * 把弹药箱（ball-0）运进中央据点 room-3  —— 复用 GoTo/PickUp/PutInRoom
        * 确保中央据点 room-3 安全               —— 触发 Suppress→Secure 两步链

    宏库把「运弹药」编成可复用子树；占领目标交给规划器自动回链。
    """
    composite_library: CompositeLibrary = [
        {
            # 弹药箱（ball-0）从蓝方基地 room-1 运进中央据点 room-3。
            # 注意：蓝方基地与中央据点**不直接相邻**——它们各自只通过一道门连到
            # 开阔交火区 room-0。所以跨房搬运必须经 room-0 中转，宏里写两段
            # GoBtwRoom（room-1→room-0→room-3），否则 room-1→room-3 没有对应的
            # 行动模型（GoBtwRoom 只为「共享一道门的相邻房间对」生成动作）。
            "DeliverAmmoToOutpost": [
                "GoToInRoom(self,ball-0,room-1)",
                "PickUp(self,ball-0)",
                "GoBtwRoom(self,room-1,room-0)",
                "GoBtwRoom(self,room-0,room-3)",
                "PutInRoom(self,ball-0,room-3)",
            ],
        },
    ]
    composite_library = _fit_library_to_agents(composite_library, num_agent)

    return Scenario(
        name=NAME,
        env_id=_battle_map.ENV_ID,
        num_agent=num_agent,
        balls=[
            ("green", 1),    # 弹药箱，在蓝方基地 room-1
            ("red", 3),      # 指挥旗（锚点），在中央据点 room-3
        ],
        goal=frozenset(
            {
                "IsInRoom(ball-0,room-3)",   # 弹药 → 中央据点（共享原语）
                "IsSecured(room-3)",          # 据点占领（专属 Suppress→Secure 两步）
            }
        ),
        composite_library=composite_library,
        behavior_lib="battlefield",    # 启用战场专属行为库（叠加在网格原语之上）
        unlock_all_doors=True,
        room_aliases=ROOM_ALIASES,
        decor=DECOR,
    )
