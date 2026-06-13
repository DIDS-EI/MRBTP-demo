# proj3 · 战场补给：跨多个房间（挑战）⭐⭐⭐

学**跨多个房间的连续移动**：一次搬运要穿过两道门。

## 场景

复用成品场景 `battle` 的独立地图（`MRBTP-BattleMap-v0`，闸口都不上锁）。这是
**星型**拓扑——三个据点各自只通过一道闸口连到中央开阔区，据点**彼此不相邻**：

```
 room-1 蓝方基地 ─door-0─┐
 room-2 红方基地 ─door-1─┤ room-0 开阔交火区
 room-3 中央据点 ─door-2─┘
```

## 任务

把**蓝方基地 `room-1`** 的弹药箱（绿球）运到**中央据点 `room-3`**——两据点不相邻，
必须经开阔区 `room-0` 中转（跨**两道闸口**：room-1 → room-0 → room-3，2 跳）。

## 关键知识点：多跳要拆成相邻段

`GoBtwRoom(self, 起房, 终房)` **只在相邻房间之间生效**。蓝方基地 room-1 和中央据点
room-3 不相邻（它们各自只连开阔区 room-0），所以不能写
`GoBtwRoom(self,room-1,room-3)`，必须经开阔区中转、拆成**逐跳相邻**的两段：

```python
"GoBtwRoom(self,room-1,room-0)",   # 第 1 跳：蓝方基地→开阔区
"GoBtwRoom(self,room-0,room-3)",   # 第 2 跳：开阔区→中央据点
```

## 你要填的 TODO（看 `starter.py`）

| # | 填什么 |
|---|---|
| 1 | `goal` —— `IsInRoom(ball-0,room-3)` |
| 2 | agent-0 的宏：捡弹药 → 两段相邻 GoBtwRoom(经 room-0 中转) → 放进 room-3；agent-1 空 `{}` |

## 性能提醒

2 跳搬运比 1 跳重一些（仍是亚秒到 1 秒级规划）。**不要**再加第二个独立搬运目标——
规划开销随「目标数 × 跳数 × 房间大小」增长，两个独立目标会让搜索组合爆炸到几十秒。

## 运行

```bash
python examples/projects/proj3_battle/starter.py            # 带窗口
python examples/projects/proj3_battle/starter.py --gif       # 录制回放 GIF（无显示器也能用）
python examples/projects/proj3_battle/starter.py --headless  # 无头
```

参考答案 `solution/solve.py` 实测数十步成功。
