"""home —— 暖色家居主题（家庭服务场景）。

厨房暖橙、客厅蓝、卧室紫、卫生间青；门用木色。复制本文件改值即可造新主题。
"""
from __future__ import annotations

from themes.base import Theme

HOME_THEME = Theme(
    name="home",
    background=(18, 14, 11),
    grid_line=(58, 45, 38),
    wall=(90, 61, 46),
    door_closed=(210, 153, 34),
    door_open=(120, 200, 120),
    # 按 _home_map 的 DFS 列优先编号铺色（务必与 home_service.ROOM_ALIASES 对齐）：
    #   room-0 室外花园 / room-1 厨房 / room-2 卧室 / room-3 客厅 / room-4 卫生间
    room_palette=[
        (14, 26, 18),   # room-0 室外花园 绿
        (42, 31, 26),   # room-1 厨房 暖橙
        (36, 26, 46),   # room-2 卧室 紫
        (26, 34, 48),   # room-3 客厅 冷蓝
        (22, 38, 43),   # room-4 卫生间 青
    ],
    object_colors={
        "red": (248, 81, 73), "green": (63, 185, 80), "blue": (88, 166, 255),
        "purple": (188, 140, 255), "yellow": (240, 200, 90), "grey": (139, 148, 158),
    },
    agent_palette=[
        (88, 166, 255),   # R0 蓝
        (247, 120, 186),  # R1 粉
        (240, 170, 70),   # R2 橙
    ],
    label=(240, 230, 215),
    # 家具 / 装饰图标配色（仅渲染器读，规划器无关）。
    decor_colors={
        "furniture": (110, 84, 58),   # 木色家具
        "plant": (60, 130, 70),       # 绿植
    },
)
