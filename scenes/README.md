# scenes/ — 场景（纯数据声明，想加场景只看这里）

一个场景 = **房间布局 + 物体清单 + 任务目标**（用现有谓词 `IsInRoom` / `IsNear` 拼）。
**加新场景 = 只往这里丢一个 `.py` 文件**，规划/执行/渲染一行都不用改。
详见设计文档 `docs/PLUGGABLE_BACKEND_DESIGN.html`。

## 已落地场景

| 文件                | CLI 名   | 主题     | 专属地图底座      | 语义                                       |
| ------------------- | -------- | -------- | ----------------- | ------------------------------------------ |
| `home_service.py`   | `home`   | `home`   | `_home_map.py`    | 居家服务机器人：把杯子从厨房搬进相邻客厅，摆到收纳篮旁 |
| `battlefield.py`    | `battle` | `battle` | `_battle_map.py`  | 战场补给小队：把弹药从蓝方基地运进中央据点 |

两个场景**各用一张专属地图**（不再共用旧的线性四房间底座），各自有独立的房间布局、
中文别名和家具/掩体元数据，对齐 `docs/PLUGGABLE_BACKEND_DESIGN.html` §6/§7 的设计图：

- **home（`_home_map`）** —— 一栋悬浮在花园里的四居室：`room-0` 室外花园在外圈，
  室内 2×2 切成 `room-1` 厨房 / `room-2` 卧室 / `room-3` 客厅 / `room-4` 卫生间。
  实测相邻房间对：`(0,1) (1,2) (1,3) (2,4) (3,4)`。
- **battle（`_battle_map`）** —— 星型拓扑：`room-0` 开阔交火区居中，三据点
  （`room-1` 蓝方基地 / `room-2` 红方基地 / `room-3` 中央据点）各只通中央区。
  实测相邻房间对：`(0,1) (0,2) (0,3)`——**据点彼此不相邻**，跨据点必经 room-0 中转。

```bash
# 跑家庭服务场景（自动配 home 主题），存 GIF 回放
python -m app.run --scenario home --renderer pygame

# 跑战场场景（自动配 battle 主题）
python -m app.run --scenario battle --renderer pygame
```

> **房间编号为什么不按直觉？** 编号由「房间识别 DFS（列优先扫描）」决定，不是
> 行优先顺序——这正是「规划内核只认 `room-i` 编号，人类靠中文别名读懂」解耦的
> 活教材。别名（厨房 / 蓝方基地…）只供渲染与文档，规划器永远只看编号。

## 为什么底座是自建的

下划线开头的 `_home_map.py` / `_battle_map.py` **不是场景**（自动发现会跳过它们），
而是各场景专属的网格环境定义。之所以不用 MiniGrid 现成的多房间环境：

| 现成环境     | 为什么不能用                                                       |
| ------------ | ------------------------------------------------------------------ |
| `DoorKey`    | 只有 2 个房间                                                      |
| `FourRooms`  | 开口是**空格**而非门对象，房间识别 DFS 会穿过开口，把多间看成 1 间 |
| `MultiRoom`  | 碎成多个大小不一的蛇形房间，编号混乱                              |
| `LockedRoom` | 房间够多，但过多的门让 `GoBtwRoom` 跨房间动作模型组合爆炸          |

自建解法的关键洞察：**房间靠门*对象*隔开**（而非空格开口），朴素 flood-fill 房间识别
DFS 就能把门当墙、天然数对房间数；同时**布局固定**（房间编号、门 id 跨 run 稳定），
才能写死 `balls=[(color, room)]`。紧凑网格 + 短跳搬运能把规划压到亚秒。

门一律不上锁，对应「假设任何智能体都能开门」的设定：房间仍由门对象隔开，但没人
需要先取钥匙。

## ⚠️ 规划成本设计法则（加场景前必读）

实测规划开销 ∝ **目标数 × 搬运跳数 × 房间尺寸**，**与房间数无关**：

| 任务                        | 规划耗时 |
| --------------------------- | -------- |
| 1 球、1 跳搬运              | 0.09 s   |
| 1 球、2 跳搬运              | 0.43 s   |
| 2 球、各自独立目标          | 23 s（组合爆炸！） |

所以每个场景**只设 1～2 个短跳目标**，靠房间承载*空间叙事*（每间扮演一个语义
角色），而不是堆目标数。home / battle 都只设 1 个相邻房间的单跳目标，规划稳定亚秒。

## 自动发现契约

`app/scenario.py` 启动时用 `pkgutil` 扫描本目录，凡导出下面两样的模块自动注册：

```python
NAME = "home"                       # 必填：CLI --scenario 用的名字（str）
def make(num_agent=2) -> Scenario:  # 必填：返回一个 Scenario 实例
    ...
THEME = "home"                      # 选填：推荐配色，--theme 未指定时用它
```

- 下划线开头的模块（`_*.py`，如 `_home_map.py` / `_battle_map.py`）被跳过；不满足契约的模块静默忽略。
- 单个场景文件出错只打印一行警告并跳过，**不会拖垮整个 demo**。
- 注册后即可 `--scenario <NAME>`，`--scenario` 的可选值是动态生成的。

## 怎么照着抄一个新场景

1. 复制 `home_service.py` 改名，比如 `rescue.py`。
2. 顶部保留 `from scenes import _home_map`（触发地图环境注册），`env_id=_home_map.ENV_ID`；
   或自建一张专属底座 `_rescue_map.py` 仿照 `_home_map.py` 写。
3. 改 `NAME`（CLI 名）、`THEME`（配色，可选 `home`/`battle`/`default`）。
4. 改 `balls`（`(颜色, 房间号)` 列表；`red` 习惯当锚点物）。
5. 改 `composite_library`（宏库：把一串原子动作 `GoToInRoom`/`PickUp`/
   `GoBtwRoom`/`PutInRoom`/`PutNearInRoom` 编成可复用子树）。
6. 改 `goal`（用 `IsInRoom(ball-i,room-j)` / `IsNear(ball-i,ball-j)` 拼目标）。
7. 保留 `unlock_all_doors=True`（无锁世界）。

> ⚠️ `GoBtwRoom(self,room-a,room-b)` **只在相邻房间间有效**。跨多跳的目标要拆成
> 逐段相邻跳（如 battle 跨据点必经 room-0 中转）。跨多跳会显著抬高规划耗时，务必
> 参照上面的成本法则控制在 1～2 跳以内。
