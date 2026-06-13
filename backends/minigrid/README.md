# backends/minigrid/ — 占位（路线 A 下不落地）

**这个目录目前是空的，且按当前架构（路线 A）不会有实质内容。**

最初的设想（路线 B「厚后端」）是把 `core/envs/gridenv/minigrid/` 的 env
重写、对齐到 `SimBackend` 协议后搬到这里。但 P1 最终选了**路线 A（薄后端）**：

- 规划 / 执行 / 物理逻辑**原地复用** `core/envs/gridenv/minigrid/` 那套已验证
  的实现，一行不动；
- 真正可插拔的只有**渲染层**——见 `backends/pygame/`（实现 `Renderer` 协议，
  headless 跑出 GIF）。

也就是说，MiniGrid「后端」并没有被搬成一个独立的 `SimBackend` 实现，而是继续
当作内核直接用。换皮 = 换渲染器，不换 env。

> 如果将来要做真正的多后端（路线 B：从零写一个非 MiniGrid 的 grid/物理/谓词
> 实现并对齐 `SimBackend`），再在这里落地，并参照 `core/interfaces.py` 的
> `SimBackend` 协议 + `make_backend` 工厂。在那之前，本目录留作占位。
