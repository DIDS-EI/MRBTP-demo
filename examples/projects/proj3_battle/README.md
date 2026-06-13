# proj3 · 战场补给：三人协同的运·占·筑（挑战）⭐⭐⭐

接入 **battlefield 专属行为库**，让三个机器人各干一类**不同**的战术活，并体会
真正的**三步战术链** `Scout → Suppress → Secure` 是怎么由谓词依赖串起来、再被
打包进一段可复用宏的。

## 场景

复用成品场景 `battle` 的独立地图（`MRBTP-BattleMap-v0`，闸口都不上锁），并设置
`behavior_lib="battlefield"` 启用战术专属库。这是**星型**拓扑——三个据点各自只通过
一道闸口连到中央开阔区，据点**彼此不相邻**：

```
 room-1 蓝方基地 ─door-0─┐
 room-2 红方基地 ─door-1─┤ room-0 开阔交火区
 room-3 中央据点 ─door-2─┘
```

## 专属行为库（battlefield）

在共享网格原语之上，叠加一整套战术语义节点：

| 谓词 Condition | 动作 Action | 语义 |
|---|---|---|
| `IsScouted(room)` **[新增]** | `Scout(self,room)` | 侦察（进据点即可）|
| `IsThreatCleared(room)` | `Suppress(self,room)` | 压制清场（**须先** `IsScouted`）|
| `IsSecured(room)` | `Secure(self,room)` | 占领（**须先** `IsThreatCleared`）|
| `IsFortified(room)` **[新增]** | `Fortify(self,room)` | 构筑工事（独立，进据点即可）|

其中 **Scout → Suppress → Secure** 串成一条真正的**三步战术链**：要让据点
「确保安全 `IsSecured`」，规划器必须沿
`Secure ← IsThreatCleared ← Suppress ← IsScouted ← Scout` 依次回链出 侦察→压制→占领。

> 这套 cond/act 和 proj2 家务域的（清洁 / 整理 / 归置）**完全不同**——两个项目各挂
> 各的 domain 库，这正是「proj2 和 proj3 的 behavior lib 各不相同」的实现。

## 任务（3 个浅目标，驱动三人各干一类不同的战术活）

| # | 目标 | 触发的动作 |
|---|---|---|
| 1 | `IsInRoom(ball-0,room-3)` | 把弹药(绿,蓝方基地)运抵中央据点 → 共享原语，跨 2 跳 |
| 2 | `IsSecured(room-3)` | 确保中央据点安全 → 专属**三步链** Scout→Suppress→Secure |
| 3 | `IsFortified(room-1)` | 在蓝方基地构筑工事 → 新增专属 `Fortify` |

## 异构三人分工

| agent | 角色 | 怎么实现 |
|---|---|---|
| agent-0 | 运输兵 | 写宏 `DeliverAmmoToOutpost`，经开阔区中转**跨两跳**运弹药 |
| agent-1 | 突击兵 | 写宏 `AssaultAndSecure`，把 进据点→侦察→压制→占领 三步战术链打包成一举 `IsSecured` |
| agent-2 | 工兵 | 宏库留空 `{}`，`IsFortified` 被自动回链成 `GoTo→Fortify` |

## 关键知识点一：多跳要拆成相邻段

`GoBtwRoom(self, 起房, 终房)` **只在相邻房间之间生效**。蓝方基地 room-1 和中央据点
room-3 不相邻，所以不能写 `GoBtwRoom(self,room-1,room-3)`，必须经开阔区中转、拆成
**逐跳相邻**的两段：

```python
"GoBtwRoom(self,room-1,room-0)",   # 第 1 跳：蓝方基地→开阔区
"GoBtwRoom(self,room-0,room-3)",   # 第 2 跳：开阔区→中央据点
```

## 关键知识点二：三步链由依赖串起来，再打包成宏避免合取爆炸

战术链 `Scout → Suppress → Secure` 不是凭空写死的——它由谓词依赖串起来
（`Secure ← IsThreatCleared ← Suppress ← IsScouted ← Scout`）。你在
`AssaultAndSecure` 宏里按顺序列出这几步，宏规划器会校验这条依赖链确实成立。

那为什么不干脆让宏库留空、让规划器在主搜索里自动回链这条链？因为本任务的目标是
**三者合取**「运弹 ∧ 占领 ∧ 构筑」，而 `IsSecured` 是一条 depth-3 的深链。若把它
摊给所有 agent 在合取目标下自由回链，三条子链（搬运 / 战术 / 构筑）的中间状态会
相互**交织成笛卡尔积**，搜索节点爆炸（实测 >20s 超时）。把战术链收进一段 **0-cost
宏**（入口 pre 仅 `IsOpen(door-2)`，一步产出 `IsSecured`），回链深度被压到 1，
交织积随即坍缩——规划从 20s+ 超时降到 **~1s 秒收敛**。这跟运输兵用
`DeliverAmmoToOutpost` 收起搬运链是同一招：**给深目标配宏，是 MRBTP 控制多目标
合取组合爆炸的关键手段。**

## 你要填的 TODO（看 `starter.py`）

| # | 填什么 |
|---|---|
| 1 | `num_agent` —— 3 个（运弹 + 占领 + 构筑）|
| 2 | `balls` —— 弹药(绿)在 room-1、指挥旗锚点(红)在 room-3 |
| 3 | `goal` —— 上面三个浅目标 |
| 4 | `composite_library` —— agent-0 写两跳运输宏 `DeliverAmmoToOutpost`；agent-1 写三步战术宏 `AssaultAndSecure`；agent-2 留空 `{}` |

## 运行

```bash
python examples/projects/proj3_battle/starter.py            # 带窗口
python examples/projects/proj3_battle/starter.py --gif       # 录制回放 GIF（无显示器也能用）
python examples/projects/proj3_battle/starter.py --headless  # 无头
```

参考答案 `solution/solve.py` 实测：规划约 **1~2s**（两段宏把搬运链与战术链都压成
0-cost 单步），执行 **约 30 步**成功（执行有随机性，步数略有出入）——三人分别运抵弹药、
侦察压制占领据点、构筑工事。
