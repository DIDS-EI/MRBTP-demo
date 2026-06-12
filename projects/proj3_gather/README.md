# proj3 · 聚集 IsNear（挑战）

> **难度**：⭐⭐⭐ 挑战 · 跳出"放进房间"，学会用 **IsNear** 表达"相对位置"目标。

## 目标

把绿球搬到红球**旁边**：

- ball-0(红) 是"锚点"，一开始就在 room-1。
- ball-1(绿) 在 room-0，要搬进 room-1 并**停在 ball-0 旁**。
- 门是锁的，要有人先开门。

跑通后你应该看到类似：

```
✅ 成功！用 27 步把绿球搬到了红球旁边（IsNear 达成）。
```

## 核心知识点：两个全新 API

前两个项目的目标都是 `IsInRoom(球, 房间)`——只关心"在哪个房间"。这次换一类目标：

| 新东西 | 含义 |
|---|---|
| 目标谓词 `IsNear(a, b)` | a 和 b 相邻（不在乎具体坐标，只要挨着） |
| 动作 `PutNearInRoom(self, obj, anchor, room)` | 把手里的 `obj` 放到 `room` 里 `anchor` 物体**旁边**（而不是随便找空格落地） |

关键差异：搬运宏的**最后一步**从 `PutInRoom(self, ball-1, room-1)` 换成
`PutNearInRoom(self, ball-1, ball-0, room-1)`。前者随便放，后者专门放到锚点旁，
这才能满足 `IsNear` 目标。

> 想看真实项目里怎么用？仓库自带的 `warehouse` 场景就用 IsNear 把多个球都聚到红球旁，
> 见 `mrbtp_demo/scenario.py`。

## 你要做什么

打开 `starter.py`，完成 3 处 `TODO`：

| TODO | 填什么 |
|---|---|
| (1) | `balls` —— 红球放 room-1（锚点）、绿球放 room-0 |
| (2) | `goal` —— 一条 `IsNear(ball-1,ball-0)` |
| (3) | agent-1 的搬运宏，最后一步用 `PutNearInRoom` |

运行：

```bash
cd ~/mywork/mrbtp-demo
source .venv/bin/activate
python projects/proj3_gather/starter.py            # 默认弹窗口播放
python projects/proj3_gather/starter.py --headless  # 无头模式（只打印，不开窗口）
```

> 默认会弹出 pygame 窗口逐步播放聚集过程；在 SSH / 无图形界面环境请加 `--headless`。

## 卡住了？

对照 `solution/solve.py`。

## 进阶挑战（选做）

- 再加一个紫球放 room-0，目标加 `IsNear(ball-2,ball-0)`，让两个球都聚到红球旁
  （加一个机器人 + 一份 `PutNearInRoom` 宏）。这就复刻了仓库 `warehouse` 场景的核心玩法。
- 把锚点红球也改成放在 room-0，看规划器要不要先把它运过去——目标的"依赖链"会更长。
