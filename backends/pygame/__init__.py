"""backends/pygame/ —— Pygame 后端。

路线 A：当前只实现渲染器 PygameGridRenderer（render.py），把现有 minigrid
逻辑的世界状态画成 PNG/GIF。未来若走路线 B，可在此补 env/grid/objects/agent/physics。
"""
from backends.pygame.render import PygameGridRenderer

__all__ = ["PygameGridRenderer"]
