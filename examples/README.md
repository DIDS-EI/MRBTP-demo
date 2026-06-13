# examples · 从零上手 MRBTP

本目录分成两部分，建议按顺序学：

| 子目录 | 内容 | 适合 |
|---|---|---|
| [`walkthrough/`](walkthrough/) | **6 个循序渐进的单文件教程**（01~06）| 先跑这个，从"看懂世界"到"把行为树看出来" |
| [`projects/`](projects/) | **3 个动手小项目**（骨架 + TODO + 参考答案）| 学完 walkthrough 后练手，真正用起来 |

> 所有命令都在**仓库根目录**、用项目自带的虚拟环境运行：
> ```bash
> cd ~/mywork/mrbtp-demo
> source .venv/bin/activate      # 没有 .venv 就先 python -m venv .venv && pip install -e .
> ```

## 1. walkthrough/ —— 先跑这 6 课

照顺序跑一遍，你就能独立用这个 demo 做多机器人行为树规划了：

```bash
python examples/walkthrough/01_hello_env.py        # 建环境、看初始状态
python examples/walkthrough/02_single_goal.py      # 第一次调用规划器
python examples/walkthrough/03_two_robots.py       # 双机器人分工
python examples/walkthrough/04_share_belief.py     # 共享信念消融对比
python examples/walkthrough/05_custom_scenario.py  # 从零拼自己的场景
python examples/walkthrough/06_inspect_tree.py     # 把行为树打印 / 导出
```

详见 [`walkthrough/README.md`](walkthrough/README.md)。

## 2. projects/ —— 再做这 3 个练习

每个项目都是「骨架 `starter.py` + TODO 留白 + 参考答案 `solution/solve.py`」：

```bash
python examples/projects/proj1_two_rooms/starter.py   # ⭐ 跨房间搬运
python examples/projects/proj2_home/starter.py        # ⭐⭐ 摆到锚点旁（IsNear）
python examples/projects/proj3_battle/starter.py      # ⭐⭐⭐ 跨多门多跳搬运
```

详见 [`projects/README.md`](projects/README.md)。

## 三个必须知道的「坑」

这些是新同学最容易踩、且报错信息不直观的点，提前记住能省很多时间：

1. **最少 2 个机器人。**
   这个 demo 的任务分配机制（基于"认领任务 + 共享信念队列"）在 `num_agent=1`
   时不工作——树能规划出来，但所有叶子恒 FAILURE、机器人原地不动。
   smoke 用 2 个、warehouse 用 4 个，自己写场景时 `num_agent >= 2`。

2. **DoorKey 地图只有 2 个房间：`room-0` / `room-1`。**
   goal 或宏里写 `room-2` 会直接报错。球的房间号也只能填 0 或 1。
   （projects/ 用的是自建四房间走廊，有 `room-0` ~ `room-3`。）

3. **执行是非确定性的，单次约 ~70% 成功率。**
   同一 seed 多跑几次结果都会不一样。这不是 bug——正式入口 `app.verify`
   就是用「最多重试 5 次」来兜住的。教程里的例子也都内置了重试。

## 跑完之后

- 想看更系统的图文讲解：打开 `../app/TUTORIAL.html`。
- 想知道这些 API 从哪来：`app/{scenario,planner,executor}.py` 是编排层，
  底层算法在 `core/` 库里。
