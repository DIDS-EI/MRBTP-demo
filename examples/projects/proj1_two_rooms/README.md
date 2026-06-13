# proj1 · 跨房间搬运（基础）⭐

第一个项目，最小可用：把一个球搬到隔壁房间。

## 场景

直接复用成品场景 `home` 的独立地图（`scenes/home_service.py`，gym id =
`MRBTP-HomeMap-v0`）——一栋悬浮在花园里的四居室，门**都不上锁**。本题只用到其中
两个直接相邻的房间（共享 `door-0`）：

```
 room-0 室外花园 ─door-0─ room-1 厨房
```

> 窗口里会看到中文房间名和冰箱 / 沙发 / 床等家具——它们是渲染元数据，规划器看不见。

## 任务

把**室外花园 `room-0`** 的绿球搬进**相邻**的**厨房 `room-1`**（只跨一道门 = 1 跳）。

## 你要填的 TODO（看 `starter.py`）

| # | 填什么 |
|---|---|
| 1 | `num_agent` —— 最少 2 个（搬球 1 人 + 占位 1 人）|
| 2 | `balls` —— 往 room-0 放一个绿球 |
| 3 | `goal` —— `IsInRoom(ball-0,room-1)` |
| 4 | `composite_library` —— agent-0 搬球的 4 步宏；agent-1 空 `{}` |

### agent-0 宏范例

```python
{"MoveBall0": [
    "GoToInRoom(self,ball-0,room-0)",   # 走到花园 room-0 里的球旁
    "PickUp(self,ball-0)",               # 捡起
    "GoBtwRoom(self,room-0,room-1)",     # 跨 door-0 到厨房 room-1
    "PutInRoom(self,ball-0,room-1)",     # 放下
]}
```

## 运行

```bash
cd ~/mywork/mrbtp-demo
source .venv/bin/activate
python examples/projects/proj1_two_rooms/starter.py            # 带窗口
python examples/projects/proj1_two_rooms/starter.py --gif       # 录制回放 GIF（无显示器也能用）
python examples/projects/proj1_two_rooms/starter.py --headless  # 无头
```

填完跑通后，对照 `solution/solve.py`。参考答案实测数十步成功，规划亚秒级。
