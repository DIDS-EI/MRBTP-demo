"""themes/ — 渲染主题（配色，与逻辑无关）。

每个主题是一个 Theme 实例：把「房间编号 / 物体类型 / agent 编号」映射到 RGB 颜色。
渲染器（backends/pygame/render.py）只认 Theme 这个数据契约，看不到任务是什么。

用法::

    from themes import get_theme
    theme = get_theme("home")        # 或 "battle"
    rgb   = theme.room_color(0)      # 房间 0 的底色
"""
from __future__ import annotations

from themes.base import Theme
from themes.home import HOME_THEME
from themes.battle import BATTLE_THEME

_THEMES = {
    "home": HOME_THEME,
    "battle": BATTLE_THEME,
    "default": HOME_THEME,
}


def get_theme(name: str = "default") -> Theme:
    """按名字取主题；未知名字回退到 default（home）。"""
    return _THEMES.get(name, _THEMES["default"])


__all__ = ["Theme", "get_theme", "HOME_THEME", "BATTLE_THEME"]
