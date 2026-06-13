"""_battle_map —— 战场专属网格地图（3 个据点区，对齐设计文档 §7）。

为什么单独建这张图
------------------
``battle`` 场景原先和 ``home`` 共用 ``_rooms4`` 的线性四房间。按
``docs/PLUGGABLE_BACKEND_DESIGN.html`` §7 的设计，战场应当是一张**有战术语义**
的独立地图：开阔地形上散布三个据点区——蓝方基地、红方基地、中央据点，用门
（闸口）连通；掩体障碍点缀其间。

    ┌───────────────────────────────────┐
    │ ┌─────────┐                         │
    │ │蓝方基地  │      （开阔交火区）        │
    │ │room-?   │     ┌─────────┐         │
    │ └────┬────┘     │中央据点  │         │
    │                 │room-?   │         │
    │      ┌─────────┐└────┬────┘         │
    │      │红方基地  │                     │
    │      │room-?   │                     │
    │      └─────────┘                     │
    └───────────────────────────────────┘

布局原则（与规划内核解耦）—— 同 ``_home_map``
---------------------------------------------
1. **据点塑形**只靠 ``Wall`` + ``Door``：三个据点各用墙围出、留一道门连到开阔
   交火区。房间识别 DFS 把门当墙，于是切出「3 据点 + 1 开阔区」共 4 个连通域。
2. **掩体 / 装饰**不进网格几何，而是作为「场景元数据」（见 ``battlefield.py``
   的 ``DECOR``）交给渲染器画——规划器看不到它们，内核零改动。
   （注：设计文档把掩体描述为「可影响寻路的 wall-like 物体」，但一期为了不牵动
    规划与寻路，先把掩体定位成**纯视觉装饰**，与家庭服务的家具一致。）
3. **可运送物**（弹药箱 / 旗帜）由场景用 ``balls=[(color, room)]`` 声明。

据点编号怎么定下来
------------------
DFS 列优先扫描。开阔交火区在第 1 列就被扫到，所以它抢到 room-0；三个据点随后
按「左列先于右列、上排先于下排」编号（实测见 ``scripts/_probe_rooms.py``）：

    room-0 = 开阔交火区（环绕三据点的大连通域，最先被扫到）
    room-1 = 蓝方基地（左上）
    room-2 = 红方基地（左下）
    room-3 = 中央据点（右中）

> 同样地，规划器只认 room-i，``battlefield.py`` 的 ``ROOM_ALIASES`` 负责把编号
> 翻译成「开阔区 / 蓝方基地 / 红方基地 / 中央据点」给人看。
"""
from __future__ import annotations

import gymnasium as gym
from minigrid.core.grid import Grid
from minigrid.core.mission import MissionSpace
from minigrid.core.world_object import Door, Wall
from minigrid.minigrid_env import MiniGridEnv

#: gym id —— battle 场景的 ``Scenario.env_id`` 用它。
ENV_ID = "MRBTP-BattleMap-v0"

#: 画布尺寸。20x14 给三个据点 + 开阔交火区留出战术纵深，规划仍在一秒内完成。
DEFAULT_WIDTH = 20
DEFAULT_HEIGHT = 14

# ── 三个据点的外接矩形 (左上x, 左上y, 宽, 高)，以及各自那道门的位置 ──
# 蓝方基地：左上角。门开在右墙，朝开阔区。
_BLUE = (2, 2, 6, 5)
# 红方基地：左下角。门开在右墙，朝开阔区。
_RED = (2, 8, 6, 5)
# 中央据点：右侧居中。门开在左墙，朝开阔区。
_CENTER = (12, 5, 6, 5)


class BattleMapEnv(MiniGridEnv):
    """三据点战场地图：蓝方基地 / 红方基地 / 中央据点 + 环绕开阔交火区。

    布局是**固定**的（不随机），据点编号与门 id 跨次运行稳定——这对用
    ``balls=[(color, room)]`` 声明锚点、宏库写死 ``room-i`` 至关重要。
    """

    def __init__(self, width: int = DEFAULT_WIDTH, height: int = DEFAULT_HEIGHT,
                 max_steps: int | None = None, **kwargs):
        if max_steps is None:
            max_steps = 8 * width * height
        mission_space = MissionSpace(mission_func=lambda: "secure the objective")
        super().__init__(
            mission_space=mission_space,
            width=width,
            height=height,
            max_steps=max_steps,
            see_through_walls=True,
            **kwargs,
        )

    def _carve_stronghold(self, rect, door_side: str) -> tuple[int, int]:
        """围出一个据点：画外墙 + 在指定边开一道门。返回门坐标。"""
        x, y, w, h = rect
        self.grid.wall_rect(x, y, w, h)
        if door_side == "right":
            door = (x + w - 1, y + h // 2)
        elif door_side == "left":
            door = (x, y + h // 2)
        elif door_side == "top":
            door = (x + w // 2, y)
        else:  # bottom
            door = (x + w // 2, y + h - 1)
        self.put_obj(Door("yellow", is_locked=False), *door)
        return door

    def _gen_grid(self, width: int, height: int) -> None:
        self.grid = Grid(width, height)
        self.grid.wall_rect(0, 0, width, height)

        # 三个据点各围一圈墙 + 一道门，门都朝向中间的开阔交火区。
        self._carve_stronghold(_BLUE, "right")
        self._carve_stronghold(_RED, "right")
        self._carve_stronghold(_CENTER, "left")

        # 侦察兵从蓝方基地内起步，朝东（面向开阔区）。
        bx, by, bw, bh = _BLUE
        self.agent_pos = (bx + 1, by + 1)
        self.agent_dir = 0
        self.mission = "secure the objective"


def _wall():
    return Wall()


# 导入即注册 gym id（场景模块 import 本模块时，id 就已就绪）。
if ENV_ID not in gym.registry:
    gym.register(id=ENV_ID, entry_point=__name__ + ":BattleMapEnv")
