# proj2 · 接力开门搬运（进阶）

> **难度**：⭐⭐ 进阶 · 学会"一个机器人承担多份工作"，理解 `share_belief` 在协作里的作用。

## 目标

只有 **2 个机器人**，却要完成 **3 件事**：

1. 开门（门是锁的）
2. 把 ball-0 搬进 room-1
3. 把 ball-1 搬进 room-1

人手不够，于是必须有人**身兼两职**：agent-0 开完门后接着去搬一个球，这就是"接力"。

跑通后你应该看到类似：

```
✅ 成功！2 个机器人靠接力分工用 44 步搬完了两个球。
```

## 核心知识点

proj1 里是"一人一份活"。这次的新东西是：

> **一份宏库 dict 里可以放多个宏。** 规划器会把同一份 dict 里的所有宏都派给同一个机器人，并按目标需要的顺序展开。

所以"开门 + 搬球"两份工作，只要写进 **同一个 dict**，就都归 agent-0。

另一个要点是 `execute(..., share_belief=True)`：agent-1 要进 room-1 搬球，但门是 agent-0 开的——靠**信念共享**，agent-1 才能"得知"门已经开了，不必自己再跑一趟。把它改成 `False` 跑跑看，体会差异。

## 你要做什么

打开 `starter.py`，完成 2 处 `TODO`：

| TODO | 填什么 |
|---|---|
| (1) | 在 agent-0 的 dict 里**再加一个宏** `MoveBall0`（搬 ball-0 的 4 步） |
| (2) | 写出 agent-1 的宏库（一个 `MoveBall1` 宏） |

运行：

```bash
cd ~/mywork/mrbtp-demo
source .venv/bin/activate
python projects/proj2_relay/starter.py            # 默认弹窗口播放
python projects/proj2_relay/starter.py --headless  # 无头模式（只打印，不开窗口）
```

> 默认会弹出 pygame 窗口逐步播放接力搬运过程；在 SSH / 无图形界面环境请加 `--headless`。

## 卡住了？

对照 `solution/solve.py`。

## 进阶挑战（选做）

- 把 `share_belief` 改成 `False`，多跑几次，观察成功率/步数的变化。
- 让 agent-0 身兼三职（开门 + 搬两个球），agent-1 完全空闲（空 dict `{}`）。还能成吗？为什么会更慢？
