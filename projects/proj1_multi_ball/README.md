# proj1 · 多球搬运（基础）

> **难度**：⭐ 入门 · 巩固 examples 01–05 学到的 goal / composite_library。

## 目标

room-0 里有 **2 个球（绿、紫）**，把它们**都搬进 room-1**。门是锁的，需要有人先开门。

跑通后你应该看到类似：

```
✅ 成功！团队用 41 步把两个球都搬进了 room-1。
```

## 你要做什么

打开 `starter.py`，完成 4 处 `TODO`：

| TODO | 填什么 |
|---|---|
| (1) | `num_agent` —— 这个任务需要几个机器人？ |
| (2) | `balls` —— 往 room-0 放绿球和紫球 |
| (3) | `goal` —— 两个球都在 room-1 的谓词集合 |
| (4) | `composite_library` —— 补出"搬球"的两份宏（开门那份已给范例） |

完成后运行：

```bash
cd ~/mywork/mrbtp-demo
source .venv/bin/activate
python projects/proj1_multi_ball/starter.py            # 默认弹窗口播放
python projects/proj1_multi_ball/starter.py --headless  # 无头模式（只打印，不开窗口）
```

> 默认会弹出 pygame 窗口逐步播放搬运过程；在 SSH / 无图形界面环境请加 `--headless`。

## 关键规则（必看）

- **机器人数 ≥ 2**：这个 demo 的任务分配在单机器人下不工作。
- **`composite_library` 长度必须 == `num_agent`**：一人一份，没活干也要给个空 `{}`。
- **DoorKey 只有 room-0 / room-1 两个房间**，写 room-2 会报错。
- **执行有随机性**（单次约 70% 成功）：starter 已内置自动重试，跑不通就再运行一次。

## 卡住了？

对照参考答案：`solution/solve.py`。建议先自己折腾 15 分钟再看。

## 进阶挑战（选做）

- 加第 3 个球 `("yellow", 0)`：目标加一条 `IsInRoom(ball-2,room-1)`，机器人加到 4 个，再补一份搬运宏。（注意：球越多执行越慢，8x8 上 4 机器人可能要等 1–2 分钟。）
- 把绿球改成放在 room-1、紫球放 room-0，目标改成两球都进 **room-0**，看规划器怎么应对。
