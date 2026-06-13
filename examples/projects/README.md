# projects · 动手练习

跑完 `../walkthrough/` 的 6 课后，来这里做 **3 个循序渐进的小项目**，把学到的东西
真正用起来。每个项目都是「**骨架 + TODO 留白 + 参考答案**」的形式：

```
projN_xxx/
├── README.md          # 任务说明、知识点、要填的 TODO 清单
├── starter.py         # 给你的骨架，凡是 TODO 的地方就是要你填的
└── solution/
    └── solve.py       # 参考答案，自己折腾够了再来对照
```

**怎么用**：先读项目的 README，再打开 `starter.py` 填掉所有 `TODO`，
跑通后再看 `solution/solve.py` 对答案。每个项目的参考答案都已实测可跑。

## 底座：直接复用仓库成品场景的两张独立地图

三个项目**不再用旧的「四房间走廊」**，而是直接借用仓库自带的两个成品场景
（`scenes/home_service.py` 与 `scenes/battlefield.py`）的独立地图、房间中文别名
和家具 / 掩体元数据。这样练习窗口里看到的画面，和 `python -m app.run --scenario
home --renderer pygame` 跑出来的成品画面**完全一致**——有中文房间名、冰箱 / 沙发、
掩体障碍等。门都**没锁**（假设任何机器人都能开门，门只用来分隔房间）。

**home 地图**（proj1 / proj2 用）—— 一栋悬浮在花园里的四居室：

```
 room-0 室外花园 ─door-0─ room-1 厨房
                 ├─door-2─ room-3 客厅 ─door-4─ room-4 卫生间
                 └ room-1 厨房 ─door-1─ room-2 卧室 ─door-3─ room-4 卫生间
```

实测相邻房间对（共享一道门）：`(0,1) (1,2) (1,3) (2,4) (3,4)`。

**battle 地图**（proj3 用）—— 星型拓扑，三据点各只通中央开阔区：

```
 room-1 蓝方基地 ─door-0─┐
 room-2 红方基地 ─door-1─┤ room-0 开阔交火区
 room-3 中央据点 ─door-2─┘
```

实测相邻房间对：`(0,1) (0,2) (0,3)`——**据点彼此不相邻**，跨据点必须经开阔区
room-0 中转（proj3 的核心知识点）。

> **房间编号为什么不按直觉？** 编号由「房间识别 DFS（列优先扫描）」决定，不是
> 行优先顺序——这正是「规划内核只认 `room-i` 编号，人类靠中文别名读懂」解耦的
> 活教材。别名（厨房 / 蓝方基地…）只供渲染与文档，规划器永远只看编号。

## 三个项目

| 顺序 | 项目 | 难度 | 地图 | 学什么 | 新 API / 知识点 |
|---|---|---|---|---|---|
| 1 | `proj1_two_rooms` | ⭐ | home | 把球搬进相邻房间（花园→厨房，1 跳）| 写 `Scenario` + 一份搬运宏 |
| 2 | `proj2_home` | ⭐⭐ | home | 把杯子摆到收纳篮旁（厨房→客厅，1 跳）| 新谓词 `IsNear` + 动作 `PutNearInRoom` |
| 3 | `proj3_battle` | ⭐⭐⭐ | battle | 把弹药跨 2 道闸口送进中央据点 | 多跳移动：经开阔区中转，拆成相邻段的 `GoBtwRoom` |

逐个运行（先填完 starter 的 TODO）：

```bash
cd ~/mywork/mrbtp-demo
source .venv/bin/activate

python examples/projects/proj1_two_rooms/starter.py
python examples/projects/proj2_home/starter.py
python examples/projects/proj3_battle/starter.py
```

想直接看参考答案跑通的样子，把 `starter.py` 换成 `solution/solve.py` 即可。

## 可视化（看机器人在窗口里动起来）

`starter.py` 和 `solution/solve.py` 都支持三种运行方式：

```bash
python examples/projects/proj1_two_rooms/solution/solve.py            # 默认：弹出 pygame 窗口逐步播放
python examples/projects/proj1_two_rooms/solution/solve.py --gif       # 录制回放 GIF（无需显示器）
python examples/projects/proj1_two_rooms/solution/solve.py --headless  # 无头模式：只在终端打印
```

- **默认带窗口**：用仓库的 **pygame 增强渲染器**（`backends/pygame`）实时画每一步——
  带中文房间名、家具 / 掩体、按朝向画的 agent，和 `python -m app.run --renderer
  pygame` 的成品画面一致；终端同步打印每个机器人的行为树 tick 状态。任务成功后窗口
  停住，关掉窗口（或按 Esc）即退出。
  *（在 SSH / 容器 / 沙箱等拿不到本机窗口服务的环境里，会自动降级为纯终端打印——
  这时想看画面请改用 `--gif`。）*
- **`--gif`**：把整段回放录成一个 GIF（默认存到 `app/output/projects/<场景>.gif`），
  跑完打印文件路径。画面和实时窗口完全一致，**无显示器也能用**，最适合 SSH / CI /
  写教程截图。
- **`--headless`**：不开窗口、不存盘（自动启用 pygame 的 dummy 驱动），只在终端打印
  行为树 tick。
- 注意：`starter.py` 里还有 `TODO` 占位，**要先填完才能跑通**可视化。

> 这套可视化逻辑封装在 `examples/projects/_run.py` 里（规划 → 执行 → pygame 实时
> 窗口 / GIF 录制 → 保持窗口）。三个练习都调它，所以脚本本身只剩「定义 Scenario」这一件事。

> **无显示器也想看动画 GIF？** 用正式入口把帧存成 GIF：
> `python -m app.run --scenario home --renderer pygame`（GIF 落在 `output/pygame/`）。
> 练习用的 home / battle 就是这两个成品场景的同款地图。

## 通用规则（三个项目都适用，务必记住）

1. **机器人数 ≥ 2。** 这个 demo 的任务分配机制在单机器人下不工作；没活干的机器人给空宏库 `{}` 占位。
2. **`composite_library` 长度必须 == `num_agent`。** 一人一份。
3. **相邻关系看地图，别想当然。** home 是「花园居中、四室外接」，battle 是「开阔区居中、三据点外接」——都不是一条链。每张图的实测相邻对见上文「底座」一节。
4. **`GoBtwRoom` 只在相邻房间生效。** 跨多跳要拆成逐段相邻（见 proj3：经开阔区 room-0 中转）。
5. **每个项目只设一个短目标。** 规划开销随「目标数 × 跳数 × 房间大小」增长，多个独立搬运目标会组合爆炸到几十秒——别贪多。
6. **执行有随机性**（单次约 70% 成功）。每个 starter 都内置了自动重试，跑不通就再运行一次。

## 常用原子动作速查

| 动作 | 含义 |
|---|---|
| `GoToInRoom(self, 物体, 房间)` | 走到某房间里的某物体旁 |
| `PickUp(self, 物体)` | 捡起 |
| `GoBtwRoom(self, 起房, 终房)` | 跨到**相邻**房间 |
| `PutInRoom(self, 物体, 房间)` | 把手里的物体放进某房间（随便落地）|
| `PutNearInRoom(self, 物体, 锚点, 房间)` | 放到某锚点物体旁（proj2 用）|

> 想看这些 API 的完整列表和真实大场景用法，看 `../../app/TUTORIAL.html`
> 和 `../../app/scenario.py`（仓库自带的 warehouse / smoke / home / battle 场景）。
