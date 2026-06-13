# `core/btp/` — Behavior-Tree Planning

Multi-robot behavior-tree planners used in the paper

> **MRBTP: Efficient Multi-Robot Behavior Tree Planning and Collaboration**
> AAAI Oral · [arXiv 2502.18072](https://arxiv.org/abs/2502.18072) ·
> [Project page](https://dids-ei.github.io/Project/MRBTP/)

## Paper ↔ code name map

| Paper term            | Class            | File                       | Role                                                    |
| --------------------- | ---------------- | -------------------------- | ------------------------------------------------------- |
| **MRBTP**             | `MRBTP`          | `multi_robot.py`           | Top-level decentralized multi-robot BT-planning facade. |
| MR-BTP (baseline)     | `MABTP`          | `multi_robot_basic.py`     | Per-step FIFO back-chaining search.                     |
| Optimal MR-BTP        | `MAOBTP`         | `multi_robot_optimal.py`   | Cost-priority heap search; supports composite actions.  |
| Composite-action BTP  | `CABTP`          | `composite_action.py`      | Single-agent planner that builds sub-tree macros.       |
| Single-agent baseline | `PlanningAgent`  | `base/`                    | Generic back-chaining building blocks.                  |

> The class used to be called `DMR` (*Decentralized Multi-Robot*).
> `DMR` is now a **class-level alias of `MRBTP`** (`DMR is MRBTP` →
> `True`), re-exported from `core.btp`, so historical
> `from core.btp import DMR` keeps working.

## Layout

```
core/btp/
├── __init__.py                Public API (re-exports every class below)
├── README.md                  You are here.
│
├── base/                      Shared building blocks
│   ├── planning_condition.py    PlanningCondition (back-chaining graph node)
│   └── planning_agent.py        PlanningAgent     (single-agent planner)
│
├── multi_robot_basic.py       MABTP   — Multi-Robot BTP, FIFO baseline
├── multi_robot_optimal.py     MAOBTP  — Multi-Robot Optimal BTP
│                                        (cost-priority heap; composite acts)
├── composite_action.py        CABTP   — Composite-Action BTP
│                                        (single agent, fixed sequence;
│                                         builds sub-tree macros)
└── multi_robot.py             MRBTP   — paper-aligned facade that wires
                                         MABTP / MAOBTP into a runnable
                                         per-agent BehaviorTree pipeline.
                                         Exports ``DMR = MRBTP`` for
                                         backward compatibility.
```

Four real algorithm files, all in `multi_robot_*` / `composite_action`
naming. No more legacy shim files — the directory contains exactly the
code that runs.

## Algorithm cheat-sheet

| Class            | Purpose                                                | Search frontier             | Cost-aware? | Composite actions             |
| ---------------- | ------------------------------------------------------ | --------------------------- | ----------- | ----------------------------- |
| `PlanningAgent`  | Single agent, generic back-chaining                    | FIFO list                   | no          | no                            |
| `CABTP`          | Single agent, walks one fixed action sequence backward | (no search)                 | no          | builds them                   |
| `MABTP`          | Many robots, generic back-chaining                     | FIFO list                   | no          | no                            |
| `MAOBTP`         | Many robots, optimal back-chaining                     | min-heap by cumulative cost | yes         | yes                           |
| `MRBTP` (`DMR`)  | High-level driver that returns runnable BTs            | —                           | —           | toggled by `with_comp_action` |

## Recommended imports

```python
# paper-aligned (recommended)
from core.btp import MRBTP, MABTP, MAOBTP, CABTP
from core.btp import PlanningAgent, PlanningCondition

# fully-qualified canonical paths
from core.btp.multi_robot          import MRBTP
from core.btp.multi_robot_basic    import MABTP
from core.btp.multi_robot_optimal  import MAOBTP
from core.btp.composite_action     import CABTP

# DMR alias (paper's historical class name) — still works
from core.btp import DMR     # DMR is MRBTP  →  True
```

## Pipeline at a glance

```text
                    ┌──────────────────────────────────────────┐
goal, action_lists ─►│ MRBTP.planning()                         │
                    │   ├─ MABTP.planning()       (no comp.act) │
                    │   └─ MAOBTP.bfs_planning()  (with comp.)  │
                    └──────────────────────────────────────────┘
                                       │
                                       ▼
            MRBTP.get_btml_and_bt_ls(behavior_lib, comp_btml_ls=…)
                                       │
                          per-agent BTML  ──►  per-agent BehaviorTree
```

## Naming conventions

* **Classes** use the acronyms from the paper (`MRBTP`, `MABTP`,
  `MAOBTP`, `CABTP`) so citations are 1-to-1.
* **Module files** are descriptive snake_case (`multi_robot.py`,
  `multi_robot_basic.py`, `multi_robot_optimal.py`,
  `composite_action.py`) so scanning the directory immediately answers
  *"which file is which"*.
* `_dict` is preferred over `_dic`; `_list` is preferred over `_ls` in
  new code. Public attributes whose names existed before the refactor
  (e.g. `mrbtp.bt_ls`, `mrbtp.btml_ls`, `cap.btml_ls`) are kept verbatim
  for backward compatibility; new `*_list` aliases are exposed via
  `@property` for forward-compatible code.

## History

* **2026-06**: planner module files renamed from acronyms to descriptive
  names (`mabtp.py` → `multi_robot_basic.py`,
  `maobtp.py` → `multi_robot_optimal.py`,
  `cabtp.py` → `composite_action.py`,
  `mrbtp.py` → `multi_robot.py`). Active callers were migrated and the
  short-name shim files were removed.
* **2026-06**: facade class renamed from `DMR` → `MRBTP` to match the
  paper title. `DMR` survives as a class-level alias re-exported from
  `core.btp` (`DMR is MRBTP` → `True`).
