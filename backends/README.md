# backends/ — 仿真后端（每个一个文件夹，自包含「逻辑+渲染+物体」）

想加新仿真器？**复制一个文件夹照着改**，实现 `core/interfaces.py` 的
`SimBackend`（+ 配套 `Renderer`）即可。规划器 / executor 不认具体后端。

- `minigrid/` — 现有 MiniGrid，P0 归位到这里（一等后端，与 pygame 平等）
- `pygame/`   — 全新 pygame 后端（P1 起逐步填充）

> 设计文档：docs/PLUGGABLE_BACKEND_DESIGN.html §4 接口契约 / §8 目录结构
