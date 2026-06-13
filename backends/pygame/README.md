# backends/pygame/ — Pygame 渲染器（路线 A：只换皮）

这个后端走的是**路线 A（薄后端）**：规划 / 执行 / 网格物理 / 谓词动作全部
复用 MiniGrid 那一套（`core/envs/gridenv/minigrid/`），**这里只负责把世界画出来**。

所以本目录只有一个核心文件：

- `render.py` — `PygameGridRenderer`，实现 `core.interfaces.Renderer` 协议
  （`render(backend)` 画一帧 / `close()` 收尾合成 GIF）。
- `__init__.py` — 导出 `PygameGridRenderer`。

> 为什么不用 env.py / grid.py / objects.py / physics.py？
> 那是被否决的路线 B（厚后端，从零重写网格与物理，几千行高风险）。路线 A
> 复用现成逻辑，几百行、零风险，详见 `docs/PLUGGABLE_BACKEND_DESIGN.html`。

## 怎么用

经统一工厂构造，再挂到 executor 的 `on_step` 回调上即可（`app/run.py`
已接好）：

```bash
# 远程友好：headless 跑出动画 GIF（默认 save_gif）
python -m app.run --renderer pygame --theme home

# 换主题 + 只存 PNG 帧
python -m app.run --renderer pygame --theme battle --render-mode save_frames
```

工厂调用（等价于上面 CLI 内部做的事）：

```python
from core.interfaces import make_renderer
r = make_renderer("pygame", theme="home", mode="save_gif",
                  out_dir="app/output/pygame", fps=6.0)
# 每步： r.render(env)
# 收尾： gif_path = r.close()
```

## 它向 env 要什么（鸭子接口，MiniGrid env 已满足）

| 接口 | 用途 |
|------|------|
| `env.width` / `env.height` | 网格尺寸 |
| `env.grid.get(i, j)` | cell：`.type` / `.color` / `.is_open` |
| `env.get_room_index((i, j))` | 房间编号 → 房间底色（缺失自动回退背景色） |
| `env.agents[i].position` / `.direction` | agent 位姿（direction 0..3） |
| `env.agents[i].carrying` | 持有物（画在 agent 身上） |

换主题改 `themes/`（`home` 暖色家居 / `battle` 冷色军事），改画法改 `render.py`。
