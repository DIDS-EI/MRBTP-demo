"""_home_map —— 家庭服务专属网格地图（5 个语义区，对齐设计文档）。

为什么单独建这张图
------------------
``home`` 场景原先和 ``battle`` 共用 ``_rooms4`` 的线性四房间，两张图长得一模
一样、只换了配色。按 ``docs/PLUGGABLE_BACKEND_DESIGN.html`` §6 的设计，家庭服务
应当是一张**有家居语义**的独立地图：一栋「悬浮」在花园里的房子，室内 2×2 切成
厨房 / 客厅 / 卧室 / 卫生间，室外一圈是花园。

    ┌─────────────────────────────┐
    │  室外 · 花园                 │   ← 房子四周一圈可走的室外地带
    │   ┌───────────┬───────────┐  │
    │   │ 厨房       │ 客厅       │  │   ← 上排：厨房 | 客厅
    │   ├─────┬─────┼─────┬─────┤  │
    │   │ 卧室       │ 卫生间     │  │   ← 下排：卧室 | 卫生间
    │   └───────────┴───────────┘  │
    │        （左侧外门通花园）       │
    └─────────────────────────────┘

布局原则（与规划内核解耦）
--------------------------
1. **房间塑形**只靠 ``Wall`` + ``Door``：房间识别 DFS（``assign_cells_to_rooms``）
   把门*对象*当墙，于是天然切出 5 个房间（4 个室内 + 1 个室外花园）。门不上锁。
2. **家具 / 装饰**不进网格几何，而是作为「场景元数据」（见 ``home_service.py``
   的 ``DECOR``）交给渲染器画——规划器永远看不到它们，内核零改动。
3. **锚点物**（杯子 / 收纳篮）由场景用 ``balls=[(color, room)]`` 声明，走现有
   Ball 机制，可被 ``IsNear`` / ``IsInRoom`` 引用。

房间编号怎么定下来（重要的教学点）
----------------------------------
DFS 按「**列优先**扫描，遇到的第一个未访问可走格」给房间编号。本布局是房子悬浮
在花园里，最外圈的花园在第 1 列就被扫到，所以——

    room-0 = 室外花园（最外圈，最先被扫到）
    room-1 = 厨房（左上）     room-2 = 卧室（左下）
    room-3 = 客厅（右上）     room-4 = 卫生间（右下）

> 注意：列优先 DFS 决定了「左列先于右列、上排先于下排」，所以编号顺序天然是
> 花园→厨房→卧室→客厅→卫生间，**而非**文档图里那种「行优先」的直觉顺序。这
> 正是「规划器只认 room-i、人类靠别名表读懂语义」解耦的最好例证——见
> ``home_service.py`` 的 ``ROOM_ALIASES``。规划器全程不关心编号对应哪个房间。
"""
from __future__ import annotations

import gymnasium as gym
from minigrid.core.grid import Grid
from minigrid.core.mission import MissionSpace
from minigrid.core.world_object import Door, Wall
from minigrid.minigrid_env import MiniGridEnv

#: gym id —— home 场景的 ``Scenario.env_id`` 用它。
ENV_ID = "MRBTP-HomeMap-v0"

#: 画布尺寸。18x14：房子悬浮在花园里，4 个室内房间各有家具摆放余量，规划仍在
#: 一秒内完成（规划成本取决于 goal 数 × 搬运跳数 × 房间大小，而非房间数量）。
DEFAULT_WIDTH = 18
DEFAULT_HEIGHT = 14

# ── 几何常量（渲染器、别名表、场景都从这里引用，杜绝散落的魔法数字）──
#: 房子外墙（wall_rect 的左上角 + 宽高）。房子之外、边界之内的可走格 = 花园。
_HOUSE_X, _HOUSE_Y, _HOUSE_W, _HOUSE_H = 3, 2, 12, 10
#: 室内十字内墙：竖墙列 _V_WALL，横墙行 _H_WALL，把室内劈成 2×2。
_V_WALL = 9    # 竖直内墙：分隔(厨房/卧室) 与 (客厅/卫生间)
_H_WALL = 6    # 水平内墙：分隔(厨房/客厅) 与 (卧室/卫生间)


class HomeMapEnv(MiniGridEnv):
    """五区家居地图：室外花园 + 室内 厨房/客厅/卧室/卫生间。

    布局是**固定**的（不随机），所以房间编号与门 id 跨次运行稳定——这对用
    ``balls=[(color, room)]`` 声明锚点、以及宏库里写死 ``room-i`` 至关重要。
    """

    def __init__(self, width: int = DEFAULT_WIDTH, height: int = DEFAULT_HEIGHT,
                 max_steps: int | None = None, **kwargs):
        if max_steps is None:
            max_steps = 8 * width * height
        mission_space = MissionSpace(mission_func=lambda: "tidy the home")
        super().__init__(
            mission_space=mission_space,
            width=width,
            height=height,
            max_steps=max_steps,
            see_through_walls=True,
            **kwargs,
        )

    def _gen_grid(self, width: int, height: int) -> None:
        self.grid = Grid(width, height)
        # 最外层边界墙：边界与房子外墙之间的可走环带 = 室外花园。
        self.grid.wall_rect(0, 0, width, height)

        hx, hy, hw, hh = _HOUSE_X, _HOUSE_Y, _HOUSE_W, _HOUSE_H
        # ── 1) 房子外墙：一圈把室内和花园隔开 ──
        self.grid.wall_rect(hx, hy, hw, hh)
        # 室内可走区间：x∈[hx+1, hx+hw-2], y∈[hy+1, hy+hh-2]
        in_x0, in_x1 = hx + 1, hx + hw - 2
        in_y0, in_y1 = hy + 1, hy + hh - 2

        # ── 2) 室内十字内墙：竖墙 + 横墙，切成 2×2 四间房 ──
        for y in range(in_y0, in_y1 + 1):
            self.grid.set(_V_WALL, y, Wall())
        for x in range(in_x0, in_x1 + 1):
            self.grid.set(x, _H_WALL, Wall())

        # ── 3) 四道室内门（黄）：把四间房两两连成一个环 ──
        self.put_obj(Door("yellow", is_locked=False), _V_WALL, _H_WALL - 2)  # 厨房↔客厅
        self.put_obj(Door("yellow", is_locked=False), _V_WALL, _H_WALL + 2)  # 卧室↔卫生间
        self.put_obj(Door("yellow", is_locked=False), in_x0 + 1, _H_WALL)    # 厨房↔卧室
        self.put_obj(Door("yellow", is_locked=False), in_x1 - 1, _H_WALL)    # 客厅↔卫生间

        # ── 4) 室外门（绿）：开在房子左墙上，厨房 ↔ 室外花园 ──
        self.put_obj(Door("green", is_locked=False), hx, in_y0 + 1)

        # 机器人从厨房起步，朝东（面向客厅）。
        self.agent_pos = (in_x0 + 1, in_y0)
        self.agent_dir = 0
        self.mission = "tidy the home"


# 导入即注册 gym id（场景模块 import 本模块时，id 就已就绪）。
if ENV_ID not in gym.registry:
    gym.register(id=ENV_ID, entry_point=__name__ + ":HomeMapEnv")
