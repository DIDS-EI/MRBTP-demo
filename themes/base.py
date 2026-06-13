"""主题基类 —— 一个 Theme 就是「世界元素 → RGB 颜色」的一组映射。

渲染器拿到 Theme 后，对每个房间 / 物体 / agent 问它「该用什么颜色」。
新增一套配色 = 复制 home.py 改几个值，不碰任何渲染或逻辑代码。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple

RGB = Tuple[int, int, int]


@dataclass
class Theme:
    """一套配色方案（纯数据）。"""

    name: str

    # 画布与网格
    background: RGB = (13, 17, 23)        # 画布底色
    grid_line: RGB = (48, 54, 61)         # 网格线
    wall: RGB = (68, 76, 86)              # 墙
    door_closed: RGB = (210, 153, 34)     # 关着的门
    door_open: RGB = (63, 185, 80)        # 开着的门

    # 房间底色：按房间编号循环取用
    room_palette: List[RGB] = field(default_factory=lambda: [
        (22, 27, 34), (26, 34, 48), (36, 26, 46), (22, 38, 43),
    ])

    # 物体颜色：按 minigrid 的 color 名取；缺省回退到 object_fallback
    object_colors: Dict[str, RGB] = field(default_factory=lambda: {
        "red": (248, 81, 73), "green": (63, 185, 80), "blue": (88, 166, 255),
        "purple": (188, 140, 255), "yellow": (210, 153, 34), "grey": (139, 148, 158),
    })
    object_fallback: RGB = (200, 200, 200)

    # agent 配色：按 agent 编号循环取用（不同机器人不同颜色）
    agent_palette: List[RGB] = field(default_factory=lambda: [
        (88, 166, 255), (247, 120, 186), (210, 153, 34), (63, 185, 80),
    ])

    # 文字 / 标注
    label: RGB = (230, 237, 243)

    # 家具 / 掩体等「装饰元数据」(scene_decor) 的图标配色：按 decor 项的 ``kind``
    # 取色（"furniture" / "plant" / "cover" / "supply" / ...）。缺省回退到
    # ``decor_fallback``。仅渲染器读取——规划内核完全不知道装饰的存在。
    decor_colors: Dict[str, RGB] = field(default_factory=dict)
    decor_fallback: RGB = (120, 110, 95)

    def room_color(self, room_index: int) -> RGB:
        if room_index < 0 or not self.room_palette:
            return self.background
        return self.room_palette[room_index % len(self.room_palette)]

    def agent_color(self, agent_id: int) -> RGB:
        if not self.agent_palette:
            return (255, 0, 0)
        return self.agent_palette[agent_id % len(self.agent_palette)]

    def object_color(self, color_name: str) -> RGB:
        return self.object_colors.get(color_name, self.object_fallback)

    def decor_color(self, kind: str) -> RGB:
        return self.decor_colors.get(kind, self.decor_fallback)
