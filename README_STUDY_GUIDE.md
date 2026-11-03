# MRBTP 学习导读

> 这份文档不是 API 手册，而是一份**阅读路线图**。
> 目标：让一个没接触过这个仓库的人，在半小时内搞懂
> 「多机器人行为树规划」到底在干什么、代码在哪、该按什么顺序读。
>
> 详细的接口说明请看 `README.md`；本文只负责**指路**和**点破关键处**。

---

## 0. 先建立一句话心智模型

整个系统做的事，可以压缩成一句话：

> 给 N 个机器人一个**符号化目标**（比如「把球搬进 2 号房间」），
> 规划器把这个目标**倒着推**成 N 棵**行为树**，
> 执行器在栅格世界里逐拍运行这些树，机器人之间可选地**共享信念**来协调。

三个关键词，理解了它们就理解了 80%：

| 关键词 | 是什么 | 在哪看 |
|---|---|---|
| **回链（back-chaining）** | 从目标出发，反向问「要让这个成立，前提是什么？」，一路推到初始状态 | `core/btp/multi_robot_optimal.py` |
| **行为树（BT）** | 规划的产物。不是一次性动作序列，而是**带反应式的决策结构**——每拍重新求值，失败可回退重试 | `core/behavior_tree/` |
| **信念共享（belief sharing）** | 机器人把「我打算做什么」广播出去，别人据此避让/分工 | `04_share_belief.py` |

**行为树是整个设计的灵魂**：它让规划出的东西不是脆弱的脚本，而是**能在执行失败时自我恢复**的策略。这也是为什么这个方向叫「behavior tree planning」而不是「multi-agent path finding」。

---

## 1. 推荐阅读顺序（照做即可）

### 第 1 步：先跑起来，建立感性认识（10 分钟）

**不要一上来就读代码。** 先跑教程，看到东西动起来，再回头看实现。

```bash
cd mrbtp-demo-core
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python examples/walkthrough/01_hello_env.py     # 世界长什么样
python examples/walkthrough/02_single_goal.py   # 第一次规划
python examples/walkthrough/03_two_robots.py   # 双机器人协作
python examples/walkthrough/04_share_belief.py # 论文核心卖点
```

`examples/walkthrough/` 的 6 个文件是**渐进式单文件教程，注释极多**，照序跑一遍就入门了。
每个文件都可独立运行。

想**亲眼看到机器人在窗口里动**（而不是只看文字输出）：

```bash
python examples/projects/proj1_two_rooms/solution/solve.py
```

---

### 第 2 步：读编排层，搞清「谁调用谁」（20 分钟）

看完现象，再看主干流水线。按这个顺序读 `app/`（只有 7 个文件，共约 1400 行）：

| 顺序 | 文件 | 看什么 |
|---|---|---|
| 1 | `app/run.py` | **入口**。一条命令走完「场景 → 规划 → 执行 → 渲染」，先看懂它的 `main()` |
| 2 | `app/scenario.py` | 场景怎么定义：地图、机器人、球、目标、宏动作 |
| 3 | `app/planner.py` | 把场景喂给规划器（**编排层与算法层的接缝**） |
| 4 | `app/executor.py` | 逐拍 tick 行为树，驱动世界前进 |
| 5 | `app/verify.py` | 带重试的回归入口（为什么需要重试见第 4 节） |

**关键接缝**：`app/planner.py` 里构造 `action_lists` 传给规划器。
规划器**只吃符号化的动作模型**（pre/add/del），完全不碰栅格几何——
这个解耦是整个设计最漂亮的地方，也是后面能做纯符号实验的原因。

---

### 第 3 步：读算法内核，看回链到底怎么推（30 分钟）

`core/btp/` 是算法本体，**只有 1141 行**。按此顺序：

| 顺序 | 文件 | 行数 | 看什么 |
|---|---|---|---|
| 1 | `core/btp/multi_robot.py` | 206 | `MRBTP` 门面类：选哪个搜索、把结果转成 BT。**先读它的 docstring**，论文与代码的对应关系写得很清楚 |
| 2 | `core/btp/multi_robot_optimal.py` | 194 | **`MAOBTP`——核心算法就在这** |
| 3 | `core/btp/base/planning_agent.py` | 432 | 单个 agent 如何「一步扩展」一个条件（最复杂的一个文件） |
| 4 | `core/btp/base/planning_condition.py` | 61 | 回链图的节点结构（很短，一看就懂） |
| 5 | `core/btp/multi_robot_basic.py` | 111 | `MABTP`：FIFO 无宏动作版本，作为对照 |

#### 算法核心：就这 40 行

`multi_robot_optimal.py` 的 `bfs_planning()`（第 105–194 行）是整个仓库的心脏。
剥掉参数检查，主干逻辑只有这些：

```python
frontier = []                              # 优先队列（按累积代价排序）
heapq.heappush(frontier, CondCostPair(goal, 0))   # 从【目标】出发，不是从初始状态

while frontier:
    condition_cost = heapq.heappop(frontier)      # 取出代价最小的条件
    condition = condition_cost.cond

    for agent in planning_agent_list:            # 每个 agent 尝试扩展
        premises = agent.one_step_expand(condition_cost)
        for cc in premises:
            heapq.heappush(frontier, cc)         # 前提条件入队，继续往下推

    if self.start is not None and self.start >= condition:
        break                                    # 初始状态已覆盖该条件 → 找到计划
    if time.time() - start_time > self.max_time_limit:
        break                                    # 20 秒墙钟上限
```

**要点：**

- **方向是反的**。从 goal 倒推到 start，不是从 start 正推到 goal。
  这叫 back-chaining，是 BT 规划区别于经典 PDDL 前向搜索的根本特征。
- **终止条件是 `start >= condition`**——即「当前推到的前提，初始状态已经满足了」，
  说明回链链到了地面，计划成立。
- **每个 agent 都有一棵自己的树**。`planning_agent_list` 里每个 agent 独立扩展，
  谁的 action 能覆盖某个子目标，那部分就归它——**任务分配是搜索的副产品，不是单独一个模块**。
- **`single_expand` 参数**（第 105 行 docstring 有详细解释）：
  - `False`（默认）：每个条件被**所有** agent 扩展。灵活，但分支因子随队伍规模爆炸。
  - `True`：每个条件**只被一个** agent 认领（轮转分配）。搜索小得多，但会漏掉一些协作方案。

  这一对开关**就是论文里效率与完备性的权衡**，也是做消融实验时第一个该动的旋钮。

---

### 第 4 步：读行为树运行时（按需）

`core/behavior_tree/` 是 BT 的执行引擎与 BTML 语言：

- `behavior_tree.py` —— tick 机制：每拍从根求值，返回 SUCCESS/FAILURE/RUNNING
- `btml/` —— BTML 的文本/解析（ANTLR 生成的 lexer/parser，**不用读**，是自动生成的代码）
- `base_nodes/` —— 各类节点（Sequence/Selector/Condition/Action/CompositeAction）

**只读 `behavior_tree.py` 的 tick 逻辑就够了**，BTML 那堆是语法层实现细节。

---

## 2. 目录速查

```
mrbtp-demo-core/
├── README.md              ← 完整接口文档，写得很好，遇到问题先查它
├── README_STUDY_GUIDE.md  ← 本文件
├── core/                  ← 🧠 规划内核（上游 mrbtp 包本身，仅改名）
│   ├── btp/               ← ★ 算法本体，1141 行，最该精读的部分
│   ├── behavior_tree/     ← BT 运行时 + BTML 语言
│   ├── envs/              ← MiniGrid 多智能体栅格环境适配
│   ├── agents/            ← 决策层（GoalProvider 抽象）
│   ├── interfaces.py      ← 可插拔协议定义（后端/渲染器）
│   └── utils/             ← 通用工具
├── app/                   ← 🎬 编排层（7 个文件，把流水线串起来）
│   ├── run.py             ← 正式入口
│   ├── scenario.py  planner.py  executor.py
│   └── verify.py  visualize.py
├── backends/ themes/ scenes/   ← 🎨 渲染层（可插拔后端 + 配色 + 场景数据）
├── examples/
│   ├── walkthrough/        ← ★ 6 课渐进教程，学习起点
│   ├── projects/           ← 3 个带 TODO 的动手练习（含答案）
│   └── paper_reproduction/ ← 论文 Fig.4 / Table 1–3 的近似复现（结果本地生成）
└── requirements.txt  pyproject.toml
```

**四层职责**（README 里的划分，很好用）：

| 角色 | 目录 | 一句话 |
|---|---|---|
| 规划内核 | `core/` | 引擎（不直接面向用户） |
| 编排层 | `app/` | 导演（调度引擎） |
| 渲染层 | `backends/` `themes/` `scenes/` | 摄影棚（决定长什么样） |
| 教学层 | `examples/` | 教科书（教你怎么用） |

---

## 3. 三个最容易踩的坑（务必先记）

这三条来自 `examples/walkthrough/README.md`，是新同学最容易卡住、
且**报错信息完全不直观**的地方：

1. **最少 2 个机器人。**
   任务分配机制在 `num_agent=1` 时不工作——树能规划出来，但所有叶子恒 FAILURE、
   机器人原地不动。自己写场景时保证 `num_agent >= 2`。

2. **DoorKey 地图只有 2 个房间（`room-0` / `room-1`）。**
   goal 或宏里写 `room-2` 会直接报错。

3. **执行是非确定性的，单次约 ~70% 成功率。**
   因为目标是个 `set`，集合迭代顺序受 `PYTHONHASHSEED` 每进程随机化影响，
   **同一 seed 多跑几次结果都不一样**。这不是 bug——
   正式入口 `app/verify.py` 就是用「最多重试 5 次」来兜住的。
   （`app/run.py` 里 `random.seed()` 的位置在 planner 之后，也有影响。）

---

## 4. 想做实验/改代码，从哪下手

| 你想做的事 | 动哪里 |
|---|---|
| 换一个新任务/地图 | `scenes/` + `app/scenario.py` |
| 对比「是否共享信念」 | `04_share_belief.py` 是现成模板 |
| 对比算法效率 | `single_expand` 开关（`bfs_planning` 参数） |
| 改搜索策略 / 启发式 | `core/btp/base/planning_agent.py` 的 `one_step_expand()` |
| 加新动作类型 | 对应 domain 的 `behavior_lib/Action/` |
| 换渲染方式 | `backends/`（实现 `interfaces.py` 的 `Renderer` 协议即可） |

**衡量搜索代价的现成指标**：`record_expanded_num`（扩展条件数）
和 `expanded_time`。做效率对比时直接读这两个，比计时更稳定。

---

## 5. 与论文的关系

本仓库是论文 *MRBTP: Efficient Multi-Robot Behavior Tree Planning and Collaboration*
（AAAI Oral, [arXiv:2502.18072](https://arxiv.org/abs/2502.18072)）的**精简实现**。

代码与论文的对应：

- `MRBTP` 类 ← 论文中的 MRBTP 算法（旧名 `DMR`，仍保留别名兼容老脚本）
- `MABTP` / `MAOBTP` ← 两种回链搜索（FIFO vs 代价优先）。它们是**类名而不是文件名**：分别定义在 `core/btp/multi_robot_basic.py`（`class MABTP`）与 `core/btp/multi_robot_optimal.py`（`class MAOBTP`），由 `app/planner.py` 的 `optimal` 开关选择
- `single_expand` ← 论文中「分工式扩展」与「经典全扩展」的对照
- 信念共享 ← 论文的协作卖点（见 `04_share_belief.py`）
- 宏动作（composite action）← 预规划子树，`core/btp/composite_action.py`

相对完整科研代码库，本仓库**砍掉了** VirtualHome 三维仿真器、数值环境、LLM 客户端等，
只保留 MiniGrid 这条规划/执行链路。所以它是**最小可跑、最适合学习**的版本。

---

## 6. 本仓库未包含的内容

为控制体积与聚焦核心，以下内容不随仓库提供：

- `examples/ablation_study/` —— 同质性消融实验与结果
- `examples/paper_reproduction/results/` —— 论文复现的 CSV / 图表，运行 `exp_*.py` 本地生成
- `app/output/` —— 演示动画 GIF 等运行产物
- `docs/cys/` —— 私有开发文档

`docs/` 的其余内容（`PLANNING_OPTIONS.html` 与示意 GIF/PNG）以及
`examples/paper_reproduction/` 的脚本都随仓库提供。

---

## 7. 一句话路线总结

```
跑 01→04 教程          建立感性认识（10 min）
    ↓
读 app/run.py          搞清流水线主干（20 min）
    ↓
读 core/btp/           精读回链算法（30 min）★ 核心
    ↓
读 walkthrough/05,06   学会自定义场景 + 导出行为树
    ↓
去 examples/projects/  动手做练习
```

**如果只有 30 分钟**：跑完 `02_single_goal.py`，然后精读
`core/btp/multi_robot_optimal.py` 的 `bfs_planning()`（第 105–194 行）。
剩下的都是这个循环的展开。
