# mrbtp-demo

> **M**ulti-**R**obot **B**ehavior-**T**ree **P**lanning on MiniGrid —
> 一个**最小、自包含**的多机器人行为树规划演示。
>
> 给若干机器人一个**符号化目标**（例如「把一个球搬进隔壁房间」），
> 规划器把它**回链（back-chaining）**成「每个机器人一棵行为树」，
> 执行器在共享的 2-D 栅格世界里逐拍（tick）运行这些树，
> 并可选地让机器人**共享一块信念空间（belief space）**来彼此协调，而不是互相挡道。

本仓库是完整 `mrbtp` 科研代码库的**精简提取版**：只保留 MiniGrid 这条规划/执行链路，
砍掉了 VirtualHome 三维仿真器、数值环境、LLM 客户端等未用到的部分。
精简后的规划库就放在 `core/` 下——**它就是上游 `mrbtp` 包本身，只是改了名**。
整个仓库只有几 MB，仅依赖几个轻量 pip 包即可跑起来。

仓库内容分三块：`core/` 是规划算法与行为树运行时，`app/` 是栅格世界的执行器与 CLI，
`examples/` 是渐进教程、动手练习和论文图表复现。全部示例都跑在共享的 2-D 栅格环境上。
第一次接触建议先读 **`README_STUDY_GUIDE.md`**（半小时阅读路线图），再按下面的目录查细节。

---

## 目录

1. [宏观总览：四个角色与它们的关系](#1-宏观总览四个角色与它们的关系)
2. [一条贯穿全局的数据流](#2-一条贯穿全局的数据流)
3. [接口协议：可插拔的两条正交轴](#3-接口协议可插拔的两条正交轴)
4. [微观详述：逐目录拆解](#4-微观详述逐目录拆解)
5. [安装与运行](#5-安装与运行)
6. [边学边练：examples 与 projects 双轨](#6-边学边练examples-与-projects-双轨)
7. [相对上游 `mrbtp` 砍掉了什么](#7-相对上游-mrbtp-砍掉了什么)
8. [学习导读与论文复现](#8-学习导读与论文复现)

---

## 1. 宏观总览：四个角色与它们的关系

整个系统可以拆成**四个职责清晰的角色**。理解它们各自管什么、彼此怎么搭话，
就理解了整个 demo：

| 角色 | 目录 | 一句话定位 | 类比 |
|---|---|---|---|
| **🧠 规划内核** | `core/` | BT 运行时 + BTML 语言 + 回链规划器 + MiniGrid 适配器 | 引擎（不直接面向用户）|
| **🎬 编排层** | `app/` | 把「定义世界 → 规划 → 执行 → 可视化」串成一条流水线 | 导演（调度引擎）|
| **🎨 渲染层** | `backends/` `themes/` `scenes/` | 可插拔后端 + 配色主题 + 场景数据 | 摄影棚（决定「长什么样」）|
| **📚 教学层** | `examples/` `projects/` | 6 课渐进教程 + 3 个动手练习 | 教科书（教你怎么用）|

它们的依赖方向是**单向、分层**的——上层依赖下层，下层永不反向依赖上层：

```
┌─────────────────────────────────────────────────────────────┐
│  📚 教学层   examples/（6课）   projects/（3练习 starter+答案）  │
│              └──────────────┬──────────────┘                   │
│                             │ 只调用 app 的公开函数              │
├─────────────────────────────▼───────────────────────────────┤
│  🎬 编排层   app/                                              │
│     scenario.py → planner.py → executor.py → visualize.py     │
│     run.py（CLI 把四者粘起来）  verify.py（无头自检）           │
│              │                              │                  │
│   依赖 core 的规划算法              通过协议调用渲染层           │
├──────────────▼──────────────┐    ┌──────────▼────────────────┤
│  🧠 规划内核  core/          │    │  🎨 渲染层                  │
│   behavior_tree/ (BT+BTML)  │    │  backends/ (minigrid·pygame)│
│   btp/ (MABTP·MAOBTP·回链)  │◄───┤  themes/   (home·battle 配色)│
│   envs/gridenv/minigrid/    │    │  scenes/   (场景数据·自动发现)│
│   agents/ utils/            │    │                             │
└─────────────────────────────┘    └─────────────────────────────┘
        ▲                                      │
        └──────── core/interfaces.py ──────────┘
          （SimBackend / Renderer 两个 Protocol
           + register_backend / make_* 工厂，
           是内核与渲染层之间唯一的「接缝」）
```

**关键设计哲学**：编排层（`app/`）与规划内核（`core/`）**只通过 `core/interfaces.py`
里定义的两个 `Protocol` 对话**。这意味着：

- 想换一个**仿真器**（pybullet / Isaac / 真实机器人）？实现 `SimBackend` 协议、
  `register_backend("your_sim", factory)` 即可，规划器一行不改。
- 想换一种**画面**（pygame 窗口 → 无头 GIF → 网页 canvas）？实现 `Renderer` 协议即可，
  执行器一行不改。

仿真后端与渲染器是**两条正交的轴**，可以自由组合（详见 [§3](#3-接口协议可插拔的两条正交轴)）。

---

## 2. 一条贯穿全局的数据流

无论你跑 `python -m app.run` 还是某个练习的 `solve.py`，走的都是**同一条流水线**。
下面这张图是理解整个项目的「主轴」：

```
 ① 定义世界            ② 规划                ③ 执行                  ④ 可视化
┌────────────┐   ┌──────────────────┐   ┌─────────────────┐   ┌──────────────────┐
│ Scenario   │   │ plan_behavior_   │   │ execute()        │   │ Visualizer       │
│ (scenario  │──▶│ trees()          │──▶│ (executor.py)    │──▶│ (visualize.py)   │
│  .py)      │   │ (planner.py)     │   │                  │   │                  │
│            │   │                  │   │ 逐 tick 跑每棵   │   │ 每步回调 on_step │
│ name/goal/ │   │ 3 步：           │   │ BT；共享信念在   │   │ → 调 Renderer    │
│ balls/宏库 │   │ ·动作模型        │   │ env.blackboard   │   │   画当前帧 +      │
│ /backend   │   │ ·复合宏展开      │   │ ["predict_       │   │   打印 tick 状态  │
│            │   │ ·回链搜索(MAOBTP)│   │  condition"] 流转│   │                  │
└─────┬──────┘   └────────┬─────────┘   └────────┬────────┘   └────────┬─────────┘
      │                   │                      │                     │
      ▼                   ▼                      ▼                     ▼
 build_env()         PlanResult            ExecutionResult        make_renderer()
 →make_backend()  （每机器人一棵BT）    （TickRecord/StepRecord）  → pygame Renderer
 → MiniGrid 世界                                                   + themes 调色板
```

**逐段说明**（每段对应 `app/` 里一个文件）：

1. **① 定义世界 `scenario.py`**：`Scenario` 数据类描述「世界长什么样」——
   环境 id、机器人数、有哪些球、目标谓词、每个机器人的复合动作宏库、用哪个后端。
   `build_env()` 调 `make_backend(name)` 工厂，造出一个实现了 `SimBackend` 协议的
   MiniGrid 世界。

2. **② 规划 `planner.py`**：`plan_behavior_trees()` 三步走——
   先从行为库枚举**动作模型**，再把每个机器人的**复合宏**当 0-cost 单步展开，
   最后用 `core/btp` 的**回链搜索**（默认 MAOBTP 代价最优，可切 MABTP）把目标
   反推成行为树。产出 `PlanResult`：**每个机器人一棵 BT**。

3. **③ 执行 `executor.py`**：`execute()` 逐 tick 同时跑所有机器人的 BT。
   开启共享信念时，各机器人把预测条件写进 `env.blackboard["predict_condition"]`，
   彼此读取来协调（论文核心卖点）；关掉就退化成各自为战（消融实验）。
   产出 `ExecutionResult`，内含每拍的 `TickRecord` / `StepRecord`。

4. **④ 可视化 `visualize.py`**：`Visualizer` 在每步通过 `on_step` 回调，
   调 `make_renderer(name)` 工厂拿到一个 `Renderer`（如 pygame），画出当前帧并配上
   `themes` 里的调色板，同时在终端打印这一拍每棵 BT 的 tick 结果。

> **🎯 一句话记住**：`Scenario` 描述世界 → `planner` 把目标编译成树 →
> `executor` 跑树并让机器人用「共享信念」对话 → `visualizer` 把过程画出来。
> 四步之间的「接缝」全在 `core/interfaces.py` 的两个协议上。

---

## 3. 接口协议：可插拔的两条正交轴

`core/interfaces.py` 是整个项目的**架构枢纽**。它定义了两个 `typing.Protocol`
（结构化鸭子类型，无需继承）和一套工厂/注册表，把「算什么」和「长什么样」彻底解耦。

### 两个协议

| 协议 | 回答的问题 | 关键方法 | 现有实现 |
|---|---|---|---|
| **`SimBackend`** | 「世界怎么动？」 | `reset()` · `step()` · `get_initial_state()` · `create_action_model()` | `backends/minigrid`（接 `core/envs/gridenv/minigrid`）|
| **`Renderer`** | 「世界怎么画？」 | `render(env, ...)` · 帧捕获 / 窗口刷新 | `backends/pygame`（窗口 / GIF / 无头）|

（`SimAgent` 是 `SimBackend` 内部用的单机器人协议，规定 `step()` 等。）

### 注册表与工厂

```python
# core/interfaces.py 暴露的「接缝」API
register_backend(name, factory)   # 把一个后端工厂登记到全局表
make_backend(name, scene, ...)    # 按名字造一个 SimBackend
make_renderer(name, ...)          # 按名字造一个 Renderer
```

minigrid 后端是**惰性注册**的（首次 `make_backend("minigrid")` 时才导入重依赖）。

### 为什么说「正交」

后端轴（怎么动）× 渲染轴（怎么画）可以**自由组合**，互不影响：

```
                       渲染轴 Renderer ──────────────────►
                  │  minigrid（原生）  pygame（增强）   none（无头）
   ┌──────────────┼──────────────────────────────────────────────
 后│ minigrid     │     ✅默认           ✅家具/掩体      ✅纯打印
 端│ （现有）      │   原生栅格画法      中文房名+朝向     只出 tick
 轴│──────────────┼──────────────────────────────────────────────
 ▼│ your_sim     │   （接入仿真器后，同样三种画法任选——规划内核零改动）
   │ （扩展）      │
```

**落地证据**：`backends/` 下既有真正接通的 `minigrid`、`pygame`，
也曾附带过一个 `simulator_template/`（仿真器接入骨架，`isinstance(b, SimBackend)`
运行时自检通过）——它正是「实现协议就能插进来」的活模板。

---

## 4. 微观详述：逐目录拆解

```text
mrbtp-demo/
├── pyproject.toml          # 打包 + 锁定运行期依赖（pip install -e .）
├── requirements.txt        # 同一份依赖的纯列表
│
├── core/                   # 🧠 规划内核 = 上游 mrbtp 包，改名而来
│   ├── interfaces.py       #   ★架构枢纽：SimBackend/Renderer 协议 + 工厂/注册表
│   ├── behavior_tree/      #   BT 运行时 + BTML DSL 解析 + 节点库 + 画树
│   │   ├── behavior_tree.py        #   行为树数据结构与 tick 语义
│   │   ├── behavior_library.py     #   行为库（动作/条件节点的注册中心）
│   │   ├── base_nodes/             #   Sequence/Selector/动作/条件 基类节点
│   │   ├── btml/                   #   BTML 领域语言（文本 ⇄ 树）
│   │   └── constants.py
│   ├── btp/                #   回链规划器家族（Behavior-Tree Planning）
│   │   ├── multi_robot_basic.py    #   MABTP —— FIFO 基线规划器
│   │   ├── multi_robot_optimal.py  #   MAOBTP —— 代价最优规划器（默认）
│   │   ├── multi_robot.py          #   多机器人调度共性逻辑
│   │   ├── composite_action.py     #   复合动作宏（0-cost 单步展开）
│   │   └── base/                   #   单机器人回链基类
│   ├── envs/               #   环境抽象 + 具体世界
│   │   ├── base/                   #   抽象 Env / Agent 基类
│   │   └── gridenv/minigrid/       #   ★MiniGrid 适配器 + 该域的行为库
│   ├── agents/             #   goal_provider.py —— 目标来源抽象（static/llm 决策层）
│   └── utils/              #   RNG · A* · 路径 · 字符串 · 复合动作工具
│
├── app/                    # 🎬 编排层：薄、可读的「四步流水线」
│   ├── scenario.py         #   ①定义世界：Scenario 数据类 + build_env() + 内置场景注册表
│   ├── planner.py          #   ②规划：plan_behavior_trees() → PlanResult（每机器人一棵树）
│   ├── executor.py         #   ③执行：execute() + share_belief 开关 + TickRecord/StepRecord
│   ├── visualize.py        #   ④可视化：Visualizer.on_step → Renderer + 打印 tick
│   ├── run.py              #   CLI：把四步粘起来（--scenario/--planner/--renderer/…）
│   ├── verify.py           #   无头自检：自动重试的冒烟测试（应对执行随机性）
│   ├── README.md           #   三段式设计深潜 + 完整 CLI 旗标表
│   ├── TUTORIAL.html       #   带内嵌 SVG 的可滚动图解教程
│   └── output/             #   渲染产物（GIF/帧/规划工件）落盘处
│
├── backends/               # 🎨 可插拔仿真后端（实现 SimBackend 协议）
│   ├── __init__.py         #   内置后端的惰性注册入口
│   ├── minigrid/           #   MiniGrid 后端（薄壳，接 core/envs/.../minigrid）
│   └── pygame/render.py    #   pygame 增强渲染器（家具/掩体/中文房名/按朝向画 agent）
│
├── themes/                 # 🎨 配色主题（给渲染器用）
│   ├── base.py             #   主题基类
│   ├── home.py             #   暖色「居家」主题
│   └── battle.py           #   冷色「军事」主题
│
├── scenes/                 # 🎨 后端无关的场景数据（自动发现）
│   ├── home_service.py     #   home  场景（NAME="home"  THEME="home"，专属四居室地图）
│   ├── battlefield.py      #   battle 场景（NAME="battle" THEME="battle"，星型三据点地图）
│   ├── _home_map.py        #   home 专属网格底座（下划线前缀 → 自动发现跳过）
│   ├── _battle_map.py      #   battle 专属网格底座
│   └── README.md           #   场景契约（NAME + make()）与自动发现规则
│
└── examples/               # 📚 教学层
    ├── walkthrough/        #   6 课渐进单文件教程（01_hello_env … 06_inspect_tree）
    └── projects/           #   3 个动手练习（starter TODO 留白 + solution 参考答案）
        ├── _run.py         #   三练习共用运行器（规划→执行→pygame窗口/GIF→保持窗口）
        ├── proj1_two_rooms/#   ⭐ 1 跳搬运：写 Scenario + 一份搬运宏
        ├── proj2_home/     #   ⭐⭐ 新谓词 IsNear + 动作 PutNearInRoom
        └── proj3_battle/   #   ⭐⭐⭐ 2 跳：跨开阔区 room-0 中转
```

### 模块间的依赖与调用关系

```
                          ┌──────────────────────────────┐
   examples/projects/     │  app/run.py  (CLI 入口)        │
   */solution/solve.py ──▶│  或 examples/projects/_run.py  │
   examples/walkthrough/  └───┬───────┬───────┬───────┬───┘
                              │       │       │       │
              ┌───────────────┘       │       │       └────────────┐
              ▼                       ▼       ▼                    ▼
       app/scenario.py         app/planner.py  app/executor.py   app/visualize.py
              │                       │            │                    │
   make_backend()│            uses core/btp │   tick core/behavior_tree │ make_renderer()
              ▼                  + behavior_tree              ▼          ▼
   ┌──────────────────┐         ▼                  env.blackboard   backends/pygame
   │ backends/minigrid│   core/btp/MAOBTP·MABTP    ["predict_       + themes/home·battle
   │  └─ core/envs/   │   core/behavior_tree/BTML   condition"]
   │     gridenv/     │   core/agents/goal_provider
   │     minigrid     │
   └──────────────────┘
              ▲
              └──── 都经 core/interfaces.py 的协议/工厂 ────┘
```

**要点**：

- **教学层**（examples/projects）**只调用 `app` 的公开函数**，绝不直接碰 `core` 内部。
  这正是 demo 的承诺——**用户面向的入口是 `app` / `examples`，`core` 是引擎不直接用**。
- **`app` 四个文件各司其职**，彼此通过明确的数据类（`Scenario` / `PlanResult` /
  `ExecutionResult`）传递状态，而非共享可变全局。
- **`app` 与 `core` 的唯一接缝**是 `core/interfaces.py`：所有「造世界 / 造渲染器」
  都走工厂，规划/执行代码只依赖**协议**而非具体实现。
- **`scenes/` 的自动发现**：`scenario.py` 用 `pkgutil.iter_modules` 扫描 `scenes/`，
  任何导出 `NAME`（str）+ `make(num_agent)`（工厂）的模块即被注册为一个 CLI 场景；
  下划线开头的模块（如 `_home_map.py`）被跳过——**加一个场景 = 丢一个数据文件进 `scenes/`**。

---

## 5. 安装与运行

### 安装

```bash
cd mrbtp-demo
python3 -m venv .venv && source .venv/bin/activate
pip install -e .            # 装上 app + 精简版 core 库 + 依赖
```

支持 Python ≥ 3.9。`pip install -e .` 会注册两个控制台命令：`mrbtp-demo` 与 `mrbtp-verify`。

### 运行

```bash
# 完整 warehouse 场景，4 机器人，带窗口：
python -m app.run

# 快速无头冒烟任务（开门 + 搬一个球，2 机器人）：
python -m app.run --smoke --renderer none

# 自建的两张独立地图（home / battle），用 pygame 增强渲染器：
python -m app.run --scenario home   --renderer pygame
python -m app.run --scenario battle --renderer pygame

# 分工规划：一个机器人负责一个子目标（仅最优规划器）：
python -m app.run --scenario battle --single-expand

# 无头自检 + 自动重试（稳健的通过/失败判定）：
python -m app.verify          # 或：mrbtp-verify
```

**4 个开箱即用场景**：`warehouse` / `smoke` 是经典两房 DoorKey 任务；
`home` / `battle` 跑在自建的专属地图上（暖色居家 / 冷色军事主题）。
规划/执行旋钮（`--planner` / `--no-composite` / `--single-expand` /
`--share-belief`）**正交，对每个场景都生效**。

> **⚠️ 执行是随机的**：`GoBtwRoom` 每次重规划会重排路径，两个机器人偶尔会在门口
> 死锁，所以**单次**冒烟运行约 70% 成功，且设种子也压不住。这正是 `verify.py`
> 默认重试 5 次的原因——详见 `app/README.md` 与 `app/TUTORIAL.html`。

---

## 6. 边学边练：examples 与 projects 双轨

新手别从源码读起，从这两条动手轨道入手（中文注释、每个文件可直接跑）：

### `examples/walkthrough/` —— 6 课渐进教程

| 课 | 文件 | 学什么 |
|---|---|---|
| 1 | `01_hello_env.py` | 世界长什么样 |
| 2 | `02_single_goal.py` | 一个目标 → 一棵树 |
| 3 | `03_two_robots.py` | 两个机器人 |
| 4 | `04_share_belief.py` | 共享信念开/关的差别 |
| 5 | `05_custom_scenario.py` | 自定义场景 |
| 6 | `06_inspect_tree.py` | 检视并导出规划出的行为树 |

### `examples/projects/` —— 3 个动手练习（递进难度）

每个项目都是「**骨架 starter.py（TODO 留白）+ 参考答案 solution/solve.py**」：

| 顺序 | 项目 | 难度 | 地图 | 学什么 | 新 API / 知识点 |
|---|---|---|---|---|---|
| 1 | `proj1_two_rooms` | ⭐ | home | 把球搬进相邻房间（花园→厨房，1 跳）| 写 `Scenario` + 一份搬运宏 |
| 2 | `proj2_home` | ⭐⭐ | home | 把杯子摆到收纳篮旁（厨房→客厅，1 跳）| 新谓词 `IsNear` + 动作 `PutNearInRoom` |
| 3 | `proj3_battle` | ⭐⭐⭐ | battle | 把弹药跨 2 道闸口送进中央据点 | 多跳移动：经开阔区 room-0 中转 |

**三者的内在递进**：proj1 教你**搭一个最小 `Scenario` + 单步搬运宏**；
proj2 在同一张 home 地图上**引入新谓词与新动作**（语义扩展）；
proj3 换到 battle 星型拓扑，逼你处理**跨多跳路径**（把一次搬运拆成逐段相邻的
`GoBtwRoom`，经中央开阔区中转）。难度从「会用」→「会扩展」→「会组合」层层加码。

```bash
cd ~/mywork/mrbtp-demo && source .venv/bin/activate

# 跑参考答案（弹出 pygame 窗口逐步播放）：
python examples/projects/proj1_two_rooms/solution/solve.py
python examples/projects/proj1_two_rooms/solution/solve.py --gif       # 录 GIF（无需显示器）
python examples/projects/proj1_two_rooms/solution/solve.py --headless  # 纯终端打印
```

> 三个练习共用 `examples/projects/_run.py`（规划→执行→pygame 实时窗口 / GIF 录制→
> 保持窗口），所以每个练习脚本本身只剩「定义 `Scenario`」这一件事。

---

## 7. 相对上游 `mrbtp` 砍掉了什么

| 移除项 | 原因 |
|---|---|
| `envs/virtualhome/`（~470 KB）| 三维家居仿真器；本 demo 只用 MiniGrid。`envs/base/env.py` 里一行死的 `import UnityCommunication` 曾把它整个拖进来——那行已删。 |
| `envs/numerical_env/` | 符号化基准环境，MiniGrid 链路从不加载。 |
| `envs/gridenv/minigrid_computation_env/` | 纯计算的栅格变体，此处未用。 |
| `llm_client/` | LLM 驱动宏的 OpenAI 客户端；本 demo 用预定义宏。 |
| ~12 个重型 pip 依赖 | `openai`/`hydra-core`/`sympy`/`matplotlib`/`opencv`/`networkx`/`tabulate`/`latextable`/`ipdb`/`tqdm`/`requests`/`tdw`——精简后的代码都不 import。 |

剩下的 `mrbtp` 规划算法（MABTP / MAOBTP / 回链 / 复合动作）是**与上游逐字节一致**的代码——
只删了未用子包和一行死 import。

---

## 8. 学习导读与论文复现

除上述教程与练习外，仓库还有两份独立材料，同样只使用栅格环境与 `core/` 规划链路。

### `README_STUDY_GUIDE.md` —— 半小时阅读路线图

按「先跑起来 → 读编排层 → 读回链算法内核 → 读行为树运行时」的顺序指路，
点明三个关键词（回链、行为树、信念共享）、目录速查和最容易踩的坑。
它是指路文档而非 API 手册，接口细节以本 README 与 `app/README.md` 为准。

### `examples/paper_reproduction/` —— 论文图表复现

用本仓库自己的 `app.planner.plan_behavior_trees` 与 `app.executor.execute`
复现论文 *MRBTP: Multi-Robot Behavior Tree Planning*（arXiv:2502.18072）的 Fig.4 与 Table 1–3。
这是**忠实结构、缩小规模**的近似复现：追求曲线形状与指标趋势一致，不追求绝对数值相同。
论文里的 α（同质性）、FP（动作失败概率）、Comm（意图广播）在 demo 中分别用宏库重分配、
动作失效注入和广播计数近似；LLM 预规划子树由预置宏库扮演。

| 脚本 | 复现内容 | 主要输出（`results/`） |
|---|---|---|
| `exp_fig4.py` | Fig.4(a) SR vs FP×α；Fig.4(b) TS vs 意图共享×α | `fig4a_sr_vs_fp.{csv,md}`、`fig4b_ts_vs_share.{csv,md}` |
| `exp_table1.py` | Table 1：BT-Expansion baseline vs MRBTP 的 SR/TS/RS | `table1_baseline_vs_mrbtp.{csv,md}` |
| `exp_table2.py` | Table 2：子树预规划 + 意图共享的 TS/RS/Comm | `table2_subtree_is_comm.{csv,md}` |
| `exp_table3.py` | Table 3：预规划子树的 EC/PT | `table3_ec_pt.{csv,md}` |

```bash
# 在仓库根目录，用项目自带 venv；默认每格 5 个 seed，全套约十几分钟
.venv/bin/python examples/paper_reproduction/exp_table1.py
.venv/bin/python examples/paper_reproduction/exp_table2.py
.venv/bin/python examples/paper_reproduction/exp_table3.py
.venv/bin/python examples/paper_reproduction/exp_fig4.py

# 加大 seed 数（更慢）
.venv/bin/python examples/paper_reproduction/exp_table1.py --seeds 10
```

结果 CSV、Markdown 与图落在 `examples/paper_reproduction/results/`（由脚本运行时生成，仓库不预置）；
指标口径、实验设计与预期趋势见 `examples/paper_reproduction/README.md`。

---

## 延伸阅读

- **`app/README.md`** —— 四段式架构、`share_belief` 开关、完整 CLI 旗标表、如何扩展。
- **`app/TUTORIAL.html`** —— 带内嵌 SVG 的滚动式图解教程（流水线 / 数据流 / 行为树结构 / 两类不确定性）。
- **`docs/PLANNING_OPTIONS.html`** —— 4 个正交规划/执行旋钮的一页速查（代码位置、生效时机、组合矩阵、可直接粘贴的命令）。
- **`scenes/README.md`** —— 场景契约与自动发现规则。
- **`README_STUDY_GUIDE.md`** —— 半小时阅读路线图，从跑通示例一路指到回链算法内核与行为树运行时。
- **`examples/paper_reproduction/README.md`** —— 论文 Fig.4 / Table 1–3 的近似复现设计、指标口径与预期趋势。

---

*mrbtp-demo · MIT License · 基于 AAAI 2025 Oral 论文 MRBTP 的最小可跑演示。*
