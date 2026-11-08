# proj5 · VirtualHome 双线搬运：左右手宏子树 + 意图接单 ⭐⭐⭐

**第二个 VirtualHome 练习（复杂）**。proj4 只让规划器走两步浅链；这一题要同时
完成**两条五步搬运链**和一个独立目标，体会论文 Eq.(6)-(8) 的**子树预规划**
怎么把深链压成一个 0-cost 动作。

## 场景

| 项 | 值 |
|---|---|
| `backend` / `behavior_lib` | `"virtualhome"` / `"virtualhome"` |
| 机器人 | 3（右手搬运工 / 左手搬运工 / 电器工）|
| 物体 | `milk`, `fridge`, `apple`, `microwave`, `tv`, `kitchentable` |
| 初始 | `IsClose(fridge)`, `IsClose(microwave)`, `IsSwitchedOff(tv)` |
| 目标 | `IsIn(milk,fridge)` ∧ `IsIn(apple,microwave)` ∧ `IsSwitchedOn(tv)` |

```bash
python examples/projects/proj5_vh_subtrees/starter.py            # 填完 TODO 后
python examples/projects/proj5_vh_subtrees/solution/solve.py     # 参考答案
python examples/projects/proj5_vh_subtrees/solution/solve.py --headless
```

符号世界没有位姿，`_run.py` 一律走**纯终端 tick**（`--gif` / 窗口自动忽略）；
执行是确定的，`attempts=1`。

## 任务分解

| # | 目标 | 负责 | 动作链 |
|---|---|---|---|
| 1 | `IsIn(milk,fridge)` | agent-0（右手）| `Walk(milk)` → `RightGrab(milk)` → `Walk(fridge)` → `Open(fridge)` → `RightPutIn(milk,fridge)` |
| 2 | `IsIn(apple,microwave)` | agent-1（左手）| `Walk(apple)` → `LeftGrab(apple)` → `Walk(microwave)` → `Open(microwave)` → `LeftPutIn(apple,microwave)` |
| 3 | `IsSwitchedOn(tv)` | agent-2 | `Walk(tv)` → `SwitchOn(tv)`，不写宏，自动回链 |

前两条链各有一个**绕不过去的坑**：`Walk(self,fridge)` 的 `del_set` 会删掉
`IsNear(self,milk)`，而 `RightGrab` 需要它；`RightPutIn` 又需要
`IsNear(self,fridge)` 和 `IsOpen(fridge)`。`check_conflict` 规定一个前提集合里
最多只能有一个 `IsNear`，因此把这条链摊开给主搜索回链，中间条件会大量交织、
搜索膨胀（本项目实测关掉宏后仍可解，但展开节点约翻倍、耗时约 3 倍）。

**解法就是宏**：把整条链按顺序列进 `composite_library`，
`CompositeActionPlanner` 用 `CABTP` 为它规划一棵子树，再折叠成一个 `cost=0` 的
`PlanningAction`（`pre` 只剩初始就成立的 `IsClose(...)` / 双手空闲）。主搜索于是
一步达成目标，深链被完全藏进子树。

> 运行时宏子树由 `sub_btml_dict` 展开成真实 `py_trees` tick；接单 / 完成靠
> `IsSelfTask` / `SelfAcceptTask` / `FinishTask` 三个结构节点——VirtualHome 域在
> `behavior_lib/Fix*` 下提供了它们的符号版本。

## 关键知识点

1. **左右手是两套独立动作。** `RightGrab / RightPutIn` 只动右手状态，
   `LeftGrab / LeftPutIn` 只动左手；`Open` 却要求 `IsLeftHandEmpty`，所以左手
   搬运链里必须先放完东西再开门（本题顺序天然满足）。
2. **可开合容器要先 `IsOpen`。** `fridge`、`microwave` 都在 `CAN_OPEN` 与
   `CONTAINERS` 交集里，`*PutIn` 的 pre 会额外带 `IsOpen(容器)`；`model.py`
   的 `build_action_lists` 自动加这条前件，不用手写。
3. **`composite_library` 长度必须 == `num_agent`**，一人一份；没宏的写 `{}`。
   宏里的 `self` 会被替换成 `agent-i`，所以动作名必须和域 grounding 出来的名字
   逐字一致（例如 `RightPutIn(self,milk,fridge)`）。
4. **宏不是银弹**：它把规划压快了，但执行时要多几拍「认领任务 → tick 子树 →
   撤销意图」，本项目参考答案执行 12 步，比不写宏的 8 步略长。规划省下的
   搜索开销换来的是可组合性，不是步数减少。

## 你要填的 TODO（看 `starter.py`）

| # | 填什么 |
|---|---|
| 1 | `num_agent` —— 3 |
| 2 | `symbolic_task["action_space"]` —— 三份异构能力名单 |
| 3 | `goal` —— 上面的三个目标谓词 |
| 4 | `composite_library` —— agent-0 的右手宏、agent-1 的左手宏、agent-2 留 `{}` |

## 参考答案实测

`solution/solve.py`：规划约 **0.43s / 展开 759 个节点**，执行 **12 步**达成
三个目标，`success=True`。把 `composite_library` 改成 `[{}, {}, {}]` 关掉宏后：
同一任务仍可解，但约 **1.35s / 展开 1474 个节点**、执行 8 步——这个对照就是
「深目标配宏」的收益与代价。
