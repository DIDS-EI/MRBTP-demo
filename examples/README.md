# examples · 从零上手 MRBTP

这一组 **6 个循序渐进的单文件教程**，带你从「看懂世界长什么样」一路走到
「自己设计任务、把规划出的行为树看出来」。每个文件都**可独立运行、注释极多**，
照着顺序跑一遍，你就能独立用这个 demo 做多机器人行为树规划了。

> 所有命令都在**仓库根目录**、用项目自带的虚拟环境运行：
> ```bash
> cd ~/mywork/mrbtp-demo
> source .venv/bin/activate      # 没有 .venv 就先 python -m venv .venv && pip install -e .
> ```

## 学习路线

| 顺序 | 文件 | 学什么 | 一句话 |
|---|---|---|---|
| 1 | `01_hello_env.py` | 建环境、放球、看初始状态 | 世界长什么样、有哪些物体和谓词 |
| 2 | `02_single_goal.py` | 第一次调用规划器 | 给一个 goal，看它倒推成行为树并执行 |
| 3 | `03_two_robots.py` | 双机器人协作 | 两棵树如何并行、各自认领不同任务 |
| 4 | `04_share_belief.py` | 共享信念消融对比 | 论文核心卖点：信念共享 on/off 的差异与如何做消融 |
| 5 | `05_custom_scenario.py` | 从零拼自己的场景 | 设计新任务的基本功（地图/机器人/球/目标/宏） |
| 6 | `06_inspect_tree.py` | 把行为树看出来/存下来 | 打开"黑盒"，打印 BTML + 导出 .bt/.svg |

逐个运行：

```bash
python examples/01_hello_env.py
python examples/02_single_goal.py
python examples/03_two_robots.py
python examples/04_share_belief.py
python examples/05_custom_scenario.py
python examples/06_inspect_tree.py
```

## 三个必须知道的「坑」

这些是新同学最容易踩、且报错信息不直观的点，提前记住能省很多时间：

1. **最少 2 个机器人。**
   这个 demo 的任务分配机制（基于"认领任务 + 共享信念队列"）在 `num_agent=1`
   时不工作——树能规划出来，但所有叶子恒 FAILURE、机器人原地不动。
   smoke 用 2 个、warehouse 用 4 个，自己写场景时 `num_agent >= 2`。

2. **DoorKey 地图只有 2 个房间：`room-0` / `room-1`。**
   goal 或宏里写 `room-2` 会直接报错。球的房间号也只能填 0 或 1。

3. **执行是非确定性的，单次约 ~70% 成功率。**
   目标是一个 `set`，集合迭代顺序受 `PYTHONHASHSEED` 每进程随机化影响，所以
   **同一 seed 多跑几次结果都会不一样**。这不是 bug——正式入口 `mrbtp_demo.verify`
   就是用「最多重试 5 次」来兜住的。教程里的例子也都内置了重试。

## 可视化（看机器人在窗口里动起来）

本目录的 6 个 example 默认都跑**无头模式**（顶部设了 pygame 的 dummy 驱动），
专注于把"发生了什么"用文字打印清楚，方便对照学习。

想**亲眼看到 pygame 窗口里机器人逐步行动**，去 `../projects/`：那里的
`starter.py` / `solution/solve.py` 都内置了可视化开关——

```bash
python projects/proj1_multi_ball/solution/solve.py            # 默认弹窗口播放
python projects/proj1_multi_ball/solution/solve.py --headless  # 无头模式（同 examples）
```

窗口由 `mrbtp_demo/visualize.py` 的 `Visualizer` 渲染：每步刷新 MiniGrid 世界 +
打印每个机器人的行为树 tick 状态，任务成功后窗口停住，关掉即退出。
在 SSH / CI / 无图形界面环境请加 `--headless`，否则开窗口会报错。

## 跑完之后

- 想看更系统的图文讲解：打开 `../mrbtp_demo/TUTORIAL.html`。
- 想动手做更大的练习：去 `../projects/`，那里有带 TODO 留白和参考答案的小项目。
- 想知道这些 API 从哪来：`mrbtp_demo/{scenario,planner,executor}.py` 是编排层，
  底层算法在 `mrbtp/` 库里。
