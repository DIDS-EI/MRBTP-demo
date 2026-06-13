"""backends/ —— 可插拔仿真后端集合。

每个子目录是一个自包含后端。路线 A（当前）：pygame 仅提供渲染器，
逻辑复用 core 里的 minigrid 内核。详见 docs/PLUGGABLE_BACKEND_DESIGN.html。
"""
