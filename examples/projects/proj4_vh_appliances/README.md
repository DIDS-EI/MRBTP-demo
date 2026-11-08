# proj4 · VirtualHome 家电协同：异构三人各干各的 ⭐⭐

**第一个 VirtualHome 练习（中等）**。前三个项目都在 2-D 网格上搬球；从这里开始
换到 `core/envs/domains/virtualhome` 的**纯符号家庭服务世界**：没有格子、没有门、
没有画面，世界就是一组谓词字符串，动作是一次 STRIPS 状态转移。

## 场景与运行方式

场景由 `Scenario` 的四个字段决定，与网格场景完全不同：

| 字段 | 值 | 作用 |
|---|---|---|
| `backend` | `"virtualhome"` | 走 `backends/virtualhome` 的符号后端（不是 `gym.make`）|
| `behavior_lib` | `"virtualhome"` | standalone 域，不叠加 MiniGrid 原语 |
| `symbolic_task` | 一个 dict | `objects / action_space / init_state / goal`，格式与论文复现的 `vh_*_25.json` 一致 |
| `composite_library` | `[]` | 本题不写宏，全部交给规划器自动回链 |

```bash
python examples/projects/proj4_vh_appliances/starter.py            # 填完 TODO 后
python examples/projects/proj4_vh_appliances/solution/solve.py     # 参考答案
python examples/projects/proj4_vh_appliances/solution/solve.py --headless
```

> 符号世界没有位姿，`_run.py` 会一律走**纯终端 tick**：`--gif` 和实时窗口自动
> 忽略。所以加不加 `--headless` 输出都一样，不存在前三个项目那种「约 70% 成功率
> 要重试」的随机性——符号执行是确定的，`attempts=1` 即可。

## 域速查（本题用到的部分）

| 类别 | 本题物体 |
|---|---|
| `CAN_OPEN` | `fridge` |
| `HAS_SWITCH` | `fridge`, `tv` |
| `GRABBABLE` | `milk` |
| `SURFACES` | `kitchentable` |

| 动作 | pre | add | del |
|---|---|---|---|
| `Walk(self,obj)` | — | `IsNear(self,obj)` | 其余所有 `IsNear(self,*)` |
| `Open(self,obj)` | `IsClose(obj)`, `IsNear(self,obj)`, `IsLeftHandEmpty(self)` | `IsOpen(obj)` | `IsClose(obj)` |
| `SwitchOn(self,obj)` | `IsSwitchedOff(obj)`, `IsNear(self,obj)`, `IsLeftHandEmpty(self)` | `IsSwitchedOn(obj)` | `IsSwitchedOff(obj)` |
| `RightGrab(self,obj)` | `IsRightHandEmpty(self)`, `IsNear(self,obj)` | `IsRightHolding(self,obj)` | `IsRightHandEmpty(self)` |

初始状态里，每个机器人自动带上 `IsLeftHandEmpty(agent-i)` 和
`IsRightHandEmpty(agent-i)`（见 `model.start_state`）。

## 任务：三个机器人、两种能力、两个目标

给团队一套**异构动作空间**（`action_space` 是「每个机器人一份动作名单」）：

| agent | 角色 | 会做的动作 |
|---|---|---|
| agent-0 | 开门工 | `Walk`, `Open`, `Close` |
| agent-1 | 电器工 | `Walk`, `SwitchOn`, `SwitchOff` |
| agent-2 | 搬运工 | `Walk`, `RightGrab`, `RightPut`, `RightPutIn` |

初始：`IsClose(fridge)`、`IsSwitchedOff(tv)`。

目标（两个，**分别在不同位置**）：

| # | 目标 | 谁来回链 |
|---|---|---|
| 1 | `IsOpen(fridge)` | 开门工：`Walk(fridge)` → `Open(fridge)` |
| 2 | `IsSwitchedOn(tv)` | 电器工：`Walk(tv)` → `SwitchOn(tv)` |

搬运工这一题没有活干，但它的存在会让规划器在每个目标上多一个「谁能做」的
候选——这正是 MRBTP 的多机器人搜索：能力不匹配的动作自然被排除。

## 关键知识点

1. **`action_space` 就是能力契约。** 网格场景里所有机器人能力相同，这里可以逐人
   指定；域根据 `objects` 的类别交集把每个动作**grounding** 成具体谓词，例如
   `Open(agent-0,fridge)`。名单里没有的动作，这个机器人永远不会出现在对应 BT 里。
2. **`Walk` 的 delete 效应会清掉旧的 `IsNear`。** 所以「走到 A 再到 B」天然是顺序
   的，规划器靠 `check_conflict` 禁止一个前提集合里同时出现两个 `IsNear`。本题两个
   目标各自只依赖一个位置，因此都能被回链出来（更长的多跳链见 proj5）。
3. **没有画面 ≠ 没有执行。** 行为树仍是真实 `py_trees` tick：条件节点查
   `env.state`，动作节点原子地做 `(state | add) - del_set`。终端打印的每步 tick
   就是全部可视化。

## 你要填的 TODO（看 `starter.py`）

| # | 填什么 |
|---|---|
| 1 | `num_agent` —— 3 |
| 2 | `symbolic_task["action_space"]` —— 上面三份异构动作名单 |
| 3 | `goal` —— `IsOpen(fridge)` 与 `IsSwitchedOn(tv)` |
| 4 | `backend` / `behavior_lib` —— 都指向 `virtualhome` |

## 参考答案实测

`solution/solve.py`：规划约 **0.001s / 展开 9 个节点**，执行 **3 步**达成两个目标，
`success=True`（确定性，每次一样）。
