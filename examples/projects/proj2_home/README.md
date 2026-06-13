# proj2 · 家庭整理：三人分工的搬·擦·扫（进阶）⭐⭐

接入 **home_service 专属行为库**，让三个机器人各干一类**不同**的家务活，体会
「共享网格原语 + 域专属动作」如何被规划器自动分派给不同的人。

## 场景

复用成品场景 `home` 的独立地图（`MRBTP-HomeMap-v0`，门都不上锁），并设置
`behavior_lib="home_service"` 启用家务专属库。本题用到两个相邻房间（共享 `door-2`）：

```
 room-1 厨房 ─door-2─ room-3 客厅
```

## 专属行为库（home_service）

在共享网格原语（`GoTo` / `PickUp` / `Put` / `PutNear`…）之上，叠加一整套家务语义节点：

| 谓词 Condition | 动作 Action | 语义 |
|---|---|---|
| `IsNear(a,b)` *(共享)* | `PutNearInRoom` *(共享)* | 把物体放到锚点旁 |
| `IsClean(obj)` | `Wipe(self,obj)` | 擦干净（到物体旁即可）|
| `IsTidy(room)` | `Tidy(self,room)` | 整理房间（进房即可）|
| `IsSwept(room)` **[新增]** | `Sweep(self,room)` | 扫地（进房即可）|
| `IsStocked(obj)` **[新增]** | `Stock(self,obj)` | 归置入柜（须先拿在手上）|

> 这套 cond/act 和 proj3 战场域的（侦察 / 压制 / 占领）**完全不同**——两个项目各挂
> 各的 domain 库，这正是「proj2 和 proj3 的 behavior lib 各不相同」的实现。

## 任务（3 个浅目标，驱动三人各干一类不同的活）

| # | 目标 | 触发的动作 |
|---|---|---|
| 1 | `IsNear(ball-0,ball-1)` | 把杯子(绿,room-1)搬到客厅收纳篮(红)旁 → 共享 `PutNear` |
| 2 | `IsClean(ball-1)` | 把收纳篮擦干净 → 专属 `Wipe` |
| 3 | `IsSwept(room-1)` | 把厨房扫干净 → 新增专属 `Sweep` |

## 异构三人分工

| agent | 角色 | 怎么实现 |
|---|---|---|
| agent-0 | 搬运工 | 写一段宏 `TidyCupToBasket`，复用共享 `GoTo/PickUp/PutNear` |
| agent-1 | 清洁工 | 宏库留空 `{}`，`IsClean` 被规划器**自动回链**成 `GoTo→Wipe` |
| agent-2 | 整理工 | 宏库留空 `{}`，`IsSwept` 被规划器**自动回链**成 `GoTo→Sweep` |

> 关键体会：后两人没写死宏，只要目标谓词存在，规划器就会自动回链到对应专属动作，
> 并分派给能力匹配的 agent——这就是「共享原语 + 专属动作」的威力。

## 你要填的 TODO（看 `starter.py`）

| # | 填什么 |
|---|---|
| 1 | `num_agent` —— 3 个（搬运 + 清洁 + 整理）|
| 2 | `balls` —— 杯子(绿)在 room-1、收纳篮(红)在 room-3，顺序决定编号 |
| 3 | `goal` —— 上面三个浅目标 |
| 4 | `composite_library` —— agent-0 写搬运宏；agent-1、agent-2 留空 `{}` |

## 运行

```bash
python examples/projects/proj2_home/starter.py            # 带窗口
python examples/projects/proj2_home/starter.py --gif       # 录制回放 GIF（无显示器也能用）
python examples/projects/proj2_home/starter.py --headless  # 无头
```

参考答案 `solution/solve.py` 实测：规划约 1~2s（门初始打开 + 位置无关 `GoBtwRoom`，
把三目标的回链深度都压平，避免合取爆炸），执行约 50~60 步成功（执行有随机性，步数略有出入）。
