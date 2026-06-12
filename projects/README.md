# projects · 动手练习

跑完 `../examples/` 的 6 课后，来这里做 **3 个循序渐进的小项目**，把学到的东西
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

## 三个项目

| 顺序 | 项目 | 难度 | 学什么 | 新 API / 知识点 |
|---|---|---|---|---|
| 1 | `proj1_multi_ball` | ⭐ | 把多个球搬进同一房间 | 扩展 `goal` 和 `composite_library`（一人一份活） |
| 2 | `proj2_relay` | ⭐⭐ | 2 人做 3 件事，有人身兼两职 | 一份宏库放多个宏；`share_belief` 在协作中的作用 |
| 3 | `proj3_gather` | ⭐⭐⭐ | 把球聚到锚点旁 | 全新谓词 `IsNear` + 动作 `PutNearInRoom` |

逐个运行（先填完 starter 的 TODO）：

```bash
cd ~/mywork/mrbtp-demo
source .venv/bin/activate

python projects/proj1_multi_ball/starter.py
python projects/proj2_relay/starter.py
python projects/proj3_gather/starter.py
```

想直接看参考答案跑通的样子，把 `starter.py` 换成 `solution/solve.py` 即可。

## 可视化（看机器人在窗口里动起来）

`starter.py` 和 `solution/solve.py` 都支持两种运行方式：

```bash
python projects/proj1_multi_ball/solution/solve.py            # 默认：弹出 pygame 窗口逐步播放
python projects/proj1_multi_ball/solution/solve.py --headless  # 无头模式：只在终端打印
```

- **默认带窗口**：每一步渲染 MiniGrid 世界，终端同步打印每个机器人的行为树 tick 状态；任务成功后窗口停住，关掉窗口即退出。
- **`--headless`**：不开窗口（自动启用 pygame 的 dummy 驱动），适合 SSH / CI / 无图形界面环境。
- 需要本机有图形界面且装好 `pygame`（项目依赖，通常已装）；在无显示环境务必加 `--headless`，否则开窗口会报错。
- 注意：`starter.py` 里还有 `TODO` 占位，**要先填完才能跑通**可视化。

## 通用规则（三个项目都适用，务必记住）

1. **机器人数 ≥ 2。** 这个 demo 的任务分配机制在单机器人下不工作。
2. **`composite_library` 长度必须 == `num_agent`。** 一人一份，没活干也要给空 `{}`。
3. **DoorKey 只有 `room-0` / `room-1` 两个房间。** 写 `room-2` 会报错。
4. **执行有随机性**（单次约 70% 成功）。每个 starter 都内置了自动重试，跑不通就再运行一次。
5. **8x8 地图比 16x16 快很多。** 练习一律用 `MiniGrid-DoorKey-8x8-v0`，机器人/球越多越慢。

## 常用原子动作速查

| 动作 | 含义 |
|---|---|
| `GoToInRoom(self, 物体, 房间)` | 走到某房间里的某物体旁 |
| `PickUp(self, 物体)` | 捡起 |
| `Toggle(self, door-0)` | 开/关门（要先拿钥匙、站在门旁）|
| `GoBtwRoom(self, 起房, 终房)` | 跨房间移动 |
| `PutInRoom(self, 物体, 房间)` | 把手里的物体放进某房间（随便落地）|
| `PutNearInRoom(self, 物体, 锚点, 房间)` | 放到某锚点物体旁（proj3 用）|

> 想看这些 API 的完整列表和真实大场景用法，看 `../mrbtp_demo/TUTORIAL.html`
> 和 `../mrbtp_demo/scenario.py`（仓库自带的 warehouse / smoke 场景）。
