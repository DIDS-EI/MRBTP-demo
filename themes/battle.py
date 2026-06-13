"""battle —— 冷色军事主题（战场场景）。

蓝方基地、红方基地、中央据点用冷色调；掩体深灰、补给绿。同一引擎换一身皮。
"""
from __future__ import annotations

from themes.base import Theme

BATTLE_THEME = Theme(
    name="battle",
    background=(10, 12, 9),
    grid_line=(45, 50, 40),
    wall=(68, 76, 86),          # 据点外墙
    door_closed=(180, 130, 40),
    door_open=(120, 180, 90),
    # 按 _battle_map 的 DFS 列优先编号铺色（务必与 battlefield.ROOM_ALIASES 对齐）：
    #   room-0 开阔交火区 / room-1 蓝方基地 / room-2 红方基地 / room-3 中央据点
    room_palette=[
        (20, 24, 20),   # room-0 中立开阔地
        (16, 30, 46),   # room-1 蓝方基地
        (42, 20, 20),   # room-2 红方基地
        (42, 36, 16),   # room-3 中央据点 暖黄
    ],
    object_colors={
        "red": (248, 81, 73), "green": (63, 185, 80), "blue": (88, 166, 255),
        "purple": (188, 140, 255), "yellow": (210, 153, 34), "grey": (139, 148, 158),
    },
    agent_palette=[
        (88, 166, 255),   # 侦察 蓝
        (57, 197, 207),   # 支援 青
        (210, 153, 34),   # 突击 橙
    ],
    label=(220, 230, 240),
    # 掩体 / 补给图标配色（仅渲染器读）。
    decor_colors={
        "cover": (68, 76, 86),        # 深灰掩体（与墙同色，视觉上是障碍）
        "supply": (63, 185, 80),      # 补给绿
    },
)
