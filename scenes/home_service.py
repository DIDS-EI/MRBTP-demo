"""home_service —— 家庭服务场景（纯数据声明，5 区独立地图版）。

一队居家服务机器人在一套「四居室 + 室外花园」里把散落的物品归位。底座换成了
本场景**专属**的 ``_home_map``（不再和 battle 共用 ``_rooms4``）：一栋悬浮在花园
里的房子，室内 2×2 切成厨房 / 客厅 / 卧室 / 卫生间，室外一圈是花园——完全对齐
``docs/PLUGGABLE_BACKEND_DESIGN.html`` §6 的设计图。

房间编号 ↔ 语义（DFS 列优先扫描决定，详见 ``_home_map`` 顶部说明）：

    room-0 = 室外花园   room-1 = 厨房   room-2 = 卧室
    room-3 = 客厅       room-4 = 卫生间

> 规划器全程只认 ``room-i``；下面的 ``ROOM_ALIASES`` 只供渲染标注与文档可读性，
> 是「规划内核与表现层解耦」最直观的例子。

任务（goal）—— 刻意只设一个「短跳」目标，保证每次跑 demo 都在一秒内规划完：

    * 把杯子（ball-0，散落在厨房 room-1）送进相邻的客厅 room-3 沙发旁的收纳篮
      （ball-1），并把收纳篮擦干净。

门都不上锁，对应「假设任何机器人都能开门」的设定：房间仍由门*对象*隔开（房间
识别 DFS 把门当墙），但没人需要先去取钥匙。

家具怎么进画面（重要的解耦点）
------------------------------
冰箱 / 灶台 / 沙发 / 电视 / 床 等家具**不进网格几何**，而是作为下面的 ``DECOR``
场景元数据：``build_env`` 把它挂到 env 的 ``scene_decor`` 属性上，**只有渲染器**
读它来画图标。规划器永远看不到家具——它们既不是墙也不是可拿物，内核零改动。

配色主题：``home``（厨房暖橙 / 客厅蓝 / 卧室紫 / 卫生间青 / 花园绿）。
"""
from __future__ import annotations

# Importing _home_map registers the MRBTP-HomeMap-v0 gym id used below.
from scenes import _home_map
from app.scenario import Scenario, CompositeLibrary, _fit_library_to_agents

# CLI 上用的场景名，以及推荐搭配的配色主题（供入口默认选择，可被 --theme 覆盖）。
NAME = "home"
THEME = "home"

#: 房间编号 → 中文语义别名。仅渲染层 / 文档使用；规划器内部只认 room-i。
#: 编号顺序由 ``_home_map`` 的列优先 DFS 决定（见该模块顶部说明），不是直觉的
#: 行优先顺序——这正是「内核只认编号，人类靠别名读懂」解耦的活教材。
ROOM_ALIASES = {
    0: "室外花园",
    1: "厨房",
    2: "卧室",
    3: "客厅",
    4: "卫生间",
}

#: 家具 / 装饰元数据（**不进网格几何**，只有渲染器读）。每项描述一个图标：
#:   kind  —— 渲染器据此选画法（"furniture" 画圆角矩形+标签）
#:   cell  —— 占据的格子 (x, y)（左上角对齐）
#:   size  —— 跨几格 (w, h)，默认 (1,1)
#:   label —— 画在图标上的中文名
#:   color —— 可选，主题里没有就用 furniture 默认色
#: 坐标对照 _home_map：房子外墙左上角 (3,2)、宽12高10；室内十字内墙 x=9 / y=6。
DECOR = [
    # ── 厨房 room-1（左上：x∈4..8, y∈3..5）──
    {"kind": "furniture", "cell": (4, 3), "size": (2, 1), "label": "冰箱"},
    {"kind": "furniture", "cell": (7, 5), "size": (2, 1), "label": "灶台"},
    # ── 客厅 room-3（右上：x∈10..13, y∈3..5）──
    {"kind": "furniture", "cell": (10, 5), "size": (2, 1), "label": "沙发"},
    {"kind": "furniture", "cell": (13, 3), "size": (1, 1), "label": "电视"},
    # ── 卧室 room-2（左下：x∈4..8, y∈7..10）──
    {"kind": "furniture", "cell": (4, 9), "size": (2, 2), "label": "床"},
    # ── 卫生间 room-4（右下：x∈10..13, y∈7..10）──
    {"kind": "furniture", "cell": (12, 9), "size": (1, 1), "label": "浴缸"},
    # ── 室外花园 room-0：点缀两棵树 ──
    {"kind": "plant", "cell": (1, 1), "size": (1, 1), "label": "树"},
    {"kind": "plant", "cell": (16, 12), "size": (1, 1), "label": "树"},
]


def make(num_agent: int = 2) -> Scenario:
    """造一个「家庭服务」场景实例（5 区独立地图、无锁、含专属语义 + 家具元数据）。

    这一版接入了 *home_service* 专属行为库（``core/envs/domains/home_service``）：
    在共享的网格原语（GoTo/PickUp/Put…）之上，新增了两类家庭语义节点——

        * 谓词 ``IsClean(<obj>)`` / ``IsTidy(<room>)``
        * 动作 ``Wipe(self,<obj>)`` / ``Tidy(self,<room>)``

    目标（goal）刻意设计成既要「搬运」又要「清洁」，从而同时驱动**共享原语**和
    **专属动作**，证明两套库能在同一棵行为树里协同：

        * 把杯子（ball-0）从厨房 room-1 搬到客厅 room-3 收纳篮（ball-1）旁
          —— 复用 GoTo/PickUp/PutNear
        * 把收纳篮（ball-1）擦干净  —— 触发专属 Wipe（回链出 GoTo→Wipe）

    宏库仍把「搬杯子」这件多步活儿编成一段可复用子树；清洁目标则交给规划器自动
    回链，无需写死宏。
    """
    composite_library: CompositeLibrary = [
        {
            # 杯子（ball-0）从厨房 room-1 搬到客厅 room-3 的收纳篮（ball-1）旁。
            "TidyCupToBasket": [
                "GoToInRoom(self,ball-0,room-1)",
                "PickUp(self,ball-0)",
                "GoBtwRoom(self,room-1,room-3)",
                "PutNearInRoom(self,ball-0,ball-1,room-3)",
            ],
        },
    ]
    composite_library = _fit_library_to_agents(composite_library, num_agent)

    return Scenario(
        name=NAME,
        env_id=_home_map.ENV_ID,
        num_agent=num_agent,
        balls=[
            ("green", 1),    # 杯子，散落在厨房 room-1
            ("red", 3),      # 收纳篮（锚点），在客厅 room-3
        ],
        goal=frozenset(
            {
                "IsNear(ball-0,ball-1)",   # 杯子 → 收纳篮旁（共享原语）
                "IsClean(ball-1)",          # 收纳篮擦干净（专属 Wipe）
            }
        ),
        composite_library=composite_library,
        behavior_lib="home_service",   # 启用家庭服务专属行为库（叠加在网格原语之上）
        unlock_all_doors=True,
        room_aliases=ROOM_ALIASES,
        decor=DECOR,
    )
