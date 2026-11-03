# paper_reproduction · 用 mrbtp-demo 复现 MRBTP 论文的图表

本目录用 **mrbtp-demo 自己的算法**（`app.planner.plan_behavior_trees` +
`app.executor.execute`）去复现论文 **MRBTP: Multi-Robot Behavior Tree Planning**
（arXiv:2502.18072）里的 **Fig.4 / Table 1 / Table 2 / Table 3**。

参考的原始实验来自 `MRBTP` 仓库的 `test_experiment/` 三个实验、以及
`legacy_exp1_robustness_parallelism` / `legacy_exp2_vh_subtree_llms`——本目录只**参考它们的
指标口径与实验设计**，算法一律用 mrbtp-demo 的（不引入 MRBTP 仓库的求解器/LLM）。

---

## 这是「忠实结构、缩小规模」的近似复现

论文原实验：真实 MRBTP、多套仿真环境（warehouse / VirtualHome）、真实 LLM 预规划子树、
每格 **500 trials**、机器人数 4/8 可切换。

mrbtp-demo：教学 demo，只有 **3 个网格 project**、**无 LLM**、规模小。因此本目录追求
**曲线形状 / 指标趋势对得上**，不追求绝对数值与论文逐位相同。四处关键适配：

| 论文概念 | 论文里怎么来 | demo 里怎么近似 |
|---|---|---|
| **α**（Homogeneity 同质性） | 横扫 α∈[0,1] 的团队 | 在同一 project 上**重分配宏库**造 3 档 α：宏库越互不重叠 α 越大（异构），越共享 α 越小（同构）。见 `common.make_alpha_variants` |
| **FP**（Action Failure Probability 动作失败概率） | 求解器/环境自带 | monkeypatch 让 agent 每 tick 的高层原语以概率 p 失效（改成 done、不推进栅格）。见 `common.inject_action_failure` |
| **Comm**（意图广播次数） | 统计意图共享广播条数 | monkeypatch `agent.update_current_task` 计数；无意图共享（`share_belief=False`）时 executor 会关闭广播 → Comm≈0。见 `common.install_comm_counter` |
| **LLM 预规划子树** | 真实 LLM 把长程任务规划成子树 | demo 的 `use_composite_actions=True` 用**预置宏库**扮演同一角色（宏=一段预规划好的多步子树）。论文 Table3 的 LLM 4.2s 响应 demo 里不存在，PT 只含回链搜索时间 |
| **机器人数 4/8** | 直接切换队伍规模 | demo 三个 project 都是 3 agent，用**三个不同 project**（不同规模/结构）近似「不同队伍」维度 |

---

## 指标定义（与论文口径对齐）

| 指标 | 含义 | demo 里来源 |
|---|---|---|
| **SR** | Success Rate 成功率 | 多 seed 成功回合占比 |
| **TS** | Team Steps 团队并行步数 | `ExecutionResult.steps`（每仿真步全队各动一次） |
| **RS** | Total Robot Steps 各机器人独立步数之和 | 逐步累加「非空闲原语（action≠done）的 agent 数」 |
| **Comm** | 意图广播次数 | monkeypatch 计数（见上） |
| **EC** | Number of Expanded Conditions 扩展条件数 | `PlanResult.expanded_num`（planner 的 record_expanded_num） |
| **PT** | Planning Time 规划时间 | `PlanResult.planning_time`（回链搜索墙钟秒数，取中位数） |

---

## 脚本 → 论文图表 对应

| 脚本 | 复现 | 输出（`results/`） |
|---|---|---|
| `exp_fig4.py` | **Fig.4(a)** SR vs FP×α（鲁棒性）+ **Fig.4(b)** TS vs 意图共享×α（执行效率） | `fig4a_sr_vs_fp.{csv,md}`、`fig4b_ts_vs_share.{csv,md}` |
| `exp_table1.py` | **Table 1** BT-Expansion(baseline) vs MRBTP 的 SR/TS/RS × α | `table1_baseline_vs_mrbtp.{csv,md}` |
| `exp_table2.py` | **Table 2** 子树预规划 + 意图共享的 TS/RS/Comm（Subtree / Subtree IS / Atomic IS） | `table2_subtree_is_comm.{csv,md}` |
| `exp_table3.py` | **Table 3** 预规划子树的 EC/PT × α | `table3_ec_pt.{csv,md}` |

`common.py`：四个脚本共享的基础设施（项目加载、α 变体构造、FP/Comm 注入、指标采集、结果落盘）。

---

## 怎么跑

```bash
# 在仓库根目录，用项目自带 venv
cd /path/to/mrbtp-demo

# 各实验（默认每格 5 个 seed；proj1 原生 DoorKey 规划较慢，全套约十几分钟）
.venv/bin/python examples/paper_reproduction/exp_table1.py
.venv/bin/python examples/paper_reproduction/exp_table2.py
.venv/bin/python examples/paper_reproduction/exp_table3.py
.venv/bin/python examples/paper_reproduction/exp_fig4.py

# 想更贴近论文数值可加大 seed 数（更慢）
.venv/bin/python examples/paper_reproduction/exp_table1.py --seeds 10
```

结果 CSV/Markdown 落在 `examples/paper_reproduction/results/`。

---

## 预期趋势（复现应看到的定性结论）

- **Table 1**：MRBTP（用宏预规划+意图共享）相对 BT-Expansion baseline，SR 不降、TS/RS 更小。
- **Fig.4(a)**：SR 随 FP 升高而下降，但 MRBTP 在各 α 档都较鲁棒。
- **Fig.4(b)**：开意图共享的 TS 明显小于不开（不开常因重复劳动/死锁而步数暴涨或失败）。
- **Table 2**：Subtree IS 在低通信开销下拿到低 TS/RS；Atomic IS 通信最频繁。
- **Table 3**：预规划子树（Subtree）比纯原子回链（Atomic）扩展条件数 EC、规划时间 PT 更低。
