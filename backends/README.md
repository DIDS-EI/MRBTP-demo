# backends/ — 仿真后端（每个一个文件夹，自包含「逻辑+渲染+物体」）

想加新仿真器？**复制一个文件夹照着改**，实现 `core/interfaces.py` 的
`SimBackend`（+ 配套 `Renderer`）即可。规划器 / executor 不认具体后端。

- `minigrid/`     — 现有 MiniGrid，P0 归位到这里（一等后端，与 pygame 平等）
- `pygame/`       — 全新 pygame 后端（P1 起逐步填充）
- `virtualhome/`  — **纯符号 VirtualHome 后端**（`SimBackend` 的一等实现）

### VirtualHome 符号后端

论文 Table 2/3/4 用的 Home Service / VirtualHome 域已作为注册域接入主 app：

* 域：`core/envs/domains/virtualhome/`（`DOMAIN_REGISTRY["virtualhome"]`，
  standalone，不叠加 MiniGrid 原语）；
* 后端：`backends/virtualhome/`（模块顶层 `register_backend("virtualhome", ...)`
  自动注册，世界只是谓词集合，不连 Unity、不开窗口）；
* 场景：`scenes/virtualhome.py`（`--scenario virtualhome`，自带 `symbolic_task`）。

```bash
.venv/bin/python -m app.run --scenario virtualhome --renderer none --agents 2
.venv/bin/python -m app.run --scenario virtualhome --backend virtualhome \
    --domain virtualhome --renderer none
.venv/bin/python -m backends.virtualhome.check   # 协议 + 链路 + 域等价性自检
```

配套练习（骨架 + TODO + 参考答案）：

```bash
.venv/bin/python examples/projects/proj4_vh_appliances/solution/solve.py   # ⭐⭐ 异构三人开家电
.venv/bin/python examples/projects/proj5_vh_subtrees/solution/solve.py     # ⭐⭐⭐⭐ 双线搬运 + 宏子树
```

两个练习都通过 `examples/projects/_run.py` 调本后端：符号世界没有位姿，
运行器会自动退化为纯终端 tick（`--gif` / 实时窗口忽略）。

后端没有位姿，所以额外提供 `tick_step()` 让 `app/executor.py` 整拍接管；
MiniGrid 后端仍走原来的 `set_focus_agent/agent_step/get_focus_agent` 路径。

> 设计文档：docs/PLUGGABLE_BACKEND_DESIGN.html §4 接口契约 / §8 目录结构
