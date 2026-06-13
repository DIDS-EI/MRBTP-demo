# proj1 · 原生 MiniGrid · 带钥匙开门的三人搬运（基础）⭐

第一个项目，回归**最朴素的 MiniGrid 原生环境**：在官方 `DoorKey-16x16` 地图上，
用**纯原生行为库**（不挂任何 domain 专属库），让三人小队取钥匙开锁、把两个球搬到隔壁房间。

## 场景

直接用 MiniGrid 官方原生环境 `MiniGrid-DoorKey-16x16-v0`——两个房间被一道**上锁**的
门隔开，钥匙就在起始房间里：

```
┌──────────────┬──────────────┐
│   room-0     ║   room-1     │     ║ = 一道上锁的门 door-0
│ (钥匙+两球)   ║  (目标房)     │     钥匙 key-0 也在 room-0
└──────────────┴──────────────┘
```

> 这是三个项目里唯一用 **minigrid 官方原生地图 + 原生节点**的——没有中文房间名、
> 没有家具、没有专属动作，只有最基础的「钥匙—门—搬运」网格原语。这正是「原生态」
> 三个字的分量，也和 proj2/proj3 的语义地图形成鲜明对比。

## 任务

room-0 里有一把钥匙、两个球（绿 `ball-0`、蓝 `ball-1`），门 `door-0` **真上锁**。
三人小队要把两个球都搬进 room-1。这逼出一个天然的**异构三人分工**：

| agent | 角色 | 干的活 |
|---|---|---|
| agent-0 | 开门工 | 取钥匙 → 走到门 → `Toggle` 开锁开门 |
| agent-1 | 搬运工A | 把绿球 `ball-0` 搬进 room-1（要等门开）|
| agent-2 | 搬运工B | 把蓝球 `ball-1` 搬进 room-1（要等门开）|

三人的宏库**各不相同**——这就是「每个 agent 动作空间各异」的落点。

> 注意：proj1 **不** `unlock_all_doors`，门是真上锁的——没人开门，两名搬运工进不去。

## 你要填的 TODO（看 `starter.py`）

| # | 填什么 |
|---|---|
| 1 | `num_agent` —— 3 个（开门 1 + 搬两球 2）|
| 2 | `balls` —— 往 room-0 放绿、蓝两个球（钥匙由 DoorKey 环境自带）|
| 3 | `goal` —— `IsInRoom(ball-0,room-1)` 和 `IsInRoom(ball-1,room-1)` |
| 4 | `composite_library` —— 三人各一份不同的宏（开门 / 搬绿 / 搬蓝）|

### 三人宏范例

```python
composite_library=[
    # agent-0「开门工」：取钥匙 → 走到门 → 开门
    {"GetKeyOpenDoor": [
        "GoToInRoom(self,key-0,room-0)",
        "PickUp(self,key-0)",
        "GoToInRoom(self,door-0,room-0)",
        "Toggle(self,door-0)",
    ]},
    # agent-1「搬运工A」：搬绿球进 room-1
    {"MoveGreen": [
        "GoToInRoom(self,ball-0,room-0)",
        "PickUp(self,ball-0)",
        "GoBtwRoom(self,room-0,room-1)",
        "PutInRoom(self,ball-0,room-1)",
    ]},
    # agent-2「搬运工B」：搬蓝球进 room-1（同上换 ball-1）
    {"MoveBlue": [
        "GoToInRoom(self,ball-1,room-0)",
        "PickUp(self,ball-1)",
        "GoBtwRoom(self,room-0,room-1)",
        "PutInRoom(self,ball-1,room-1)",
    ]},
]
```

## 运行

```bash
cd ~/mywork/mrbtp-demo
source .venv/bin/activate
python examples/projects/proj1_two_rooms/starter.py            # 带窗口
python examples/projects/proj1_two_rooms/starter.py --gif       # 录制回放 GIF（无显示器也能用）
python examples/projects/proj1_two_rooms/starter.py --headless  # 无头
```

填完跑通后，对照 `solution/solve.py`。参考答案实测：规划约 4s，执行约 50~80 步一次成功
（执行有随机性，每次步数略有出入）。DoorKey 只有两个房间、组合空间小，所以 3-agent 也跑得飞快。
