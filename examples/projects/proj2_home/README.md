# proj2 · 家庭整理：摆到锚点旁（进阶）⭐⭐

学新谓词 `IsNear`：目标不再是"进某房间"，而是"挨着某个锚点物体"。

## 场景

复用成品场景 `home` 的独立地图（`MRBTP-HomeMap-v0`，门都不上锁）。本题用其中
两个直接相邻的房间（共享 `door-2`）：

```
 room-1 厨房 ─door-2─ room-3 客厅
```

## 任务

把厨房 `room-1` 的杯子（绿球）搬到**相邻**的客厅 `room-3`，**摆在收纳篮（红球）旁边**。

- `ball-0`（绿）= 杯子，起点厨房 room-1
- `ball-1`（红）= 收纳篮（锚点），在客厅 room-3

## 新知识点

| API | 含义 |
|---|---|
| `IsNear(a,b)` | 目标谓词：物体 a 紧挨着物体 b |
| `PutNearInRoom(self, 物体, 锚点, 房间)` | 把手里的物体放到锚点物体旁 |

## 你要填的 TODO（看 `starter.py`）

| # | 填什么 |
|---|---|
| 1 | `balls` —— 杯子(绿)在 room-1、收纳篮(红)在 room-3，注意顺序决定编号 |
| 2 | `goal` —— `IsNear(ball-0,ball-1)` |
| 3 | agent-0 的宏：捡杯子 → 跨一跳(room-1→room-3) → `PutNearInRoom(self,ball-0,ball-1,room-3)`；agent-1 空 `{}` |

## 运行

```bash
python examples/projects/proj2_home/starter.py            # 带窗口
python examples/projects/proj2_home/starter.py --gif       # 录制回放 GIF（无显示器也能用）
python examples/projects/proj2_home/starter.py --headless  # 无头
```

参考答案 `solution/solve.py` 实测约十步成功。
