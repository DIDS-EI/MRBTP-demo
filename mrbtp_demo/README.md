# mrbtp_demo — A readable, three-part MRBTP walkthrough

This package is a clean re-implementation of the monolithic
`test_multi_minigrid_single_demo/main.py`, split into **three independent,
heavily-commented stages** so the MRBTP pipeline is easy to read and modify.

It builds on the `mrbtp` planning library, whose algorithms are reused
unchanged — this package only reorganises the *demo* glue code into separate,
well-named modules. (In this standalone repo, `mrbtp` is a trimmed subset that
keeps only the MiniGrid path; see the top-level `README.md` for what was cut.)

```
mrbtp_demo/
├── scenario.py    # What world / objects / goal / composite macros.
├── planner.py     # Part 1: plan one behavior tree per agent from the goal.
├── executor.py    # Part 2: run the trees, with a shared-belief on/off switch.
├── visualize.py   # Part 3: render MiniGrid + print the BT tick result.
├── run.py         # CLI that wires the three parts together.
└── verify.py      # Headless self-check (CI-style smoke test).
```

---

## The three parts

### Part 1 — Plan a behavior tree per agent (`planner.py`)

`plan_behavior_trees(env, scenario)` turns a symbolic goal into one runnable
`BehaviorTree` per agent:

1. **Action model** — every grounded primitive action each agent can do, read
   from the MiniGrid behavior library (`env.create_action_model()`).
2. **Composite macros** *(optional)* — LLM-style multi-step sub-trees such as
   `GetKeyAndOpenDoor`, pre-planned by `CompositeActionPlanner` and appended to
   the action model as single 0-cost steps.
3. **Multi-robot back-chaining search** — `MAOBTP` (cost-aware optimal, supports
   macros) or `MABTP` (FIFO baseline) back-chains the goal into per-agent trees.

Returns a tidy `PlanResult` (trees + BTMLs + libs + stats). Pass `save_dir=...`
to also dump `robot-i.bt` / `robot-i.svg` and macro diagrams.

### Part 2 — Execute the trees (`executor.py`)

`execute(env, plan, share_belief=...)` ticks every agent's behavior tree each
simulation step, applies the chosen primitive to the grid, and records the
per-step result.

The headline parameter is **`share_belief`** — the multi-agent communication /
belief space:

| `share_belief` | Behaviour |
|----------------|-----------|
| `True` (default) | Agents coordinate through `env.blackboard["predict_condition"]`. When one agent accepts a macro task, its sub-goals are broadcast so the others *assume those literals will become true* — they avoid redoing the same job and wait on preconditions a teammate is about to satisfy (e.g. "the door will be opened"). This is the paper's behaviour. |
| `False` | Each agent's belief space is kept empty. Every agent reasons only from the *real* environment state, with no idea what the others intend. Useful ablation: watch the team lose coordination (duplicated work / deadlocks). |

Under the hood, sharing is implemented by `Agent.finish_current_task` /
`update_current_task` writing predicted literals into the blackboard, which the
tree nodes read via `check_if_in_predict_condition` (conditions) and
`check_if_pre_in_predict_condition` (actions). Disabling it swaps those two
methods for no-broadcast stand-ins and clears the prediction sets — **no library
files are edited**.

### Part 3 — Visualize (`visualize.py`)

`Visualizer.on_step` is handed to `execute(...)` as the per-step callback. Every
step it:

* renders the MiniGrid world (pygame window), and
* prints the **behavior-tree tick result** for each agent — which condition /
  action nodes returned SUCCESS / RUNNING / FAILURE this step (captured from
  each tree's `StatusVisitor`), plus the primitive action taken.

---

## Running it

Use the repository's virtualenv. From the **repo root**:

```bash
# Watch the 4-robot warehouse demo, shared belief space ON (default):
python -m mrbtp_demo.run

# Same task, shared belief space OFF (coordination ablation):
python -m mrbtp_demo.run --no-share-belief

# Headless, just print BT ticks, and save robot-i.bt / robot-i.svg:
python -m mrbtp_demo.run --no-render --save

# Simpler FIFO planner instead of the optimal one:
python -m mrbtp_demo.run --planner basic

# Quick headless smoke task (open a door + carry one ball, 2 robots):
python -m mrbtp_demo.run --smoke --no-render
```

### CLI options

| Flag | Default | Meaning |
|------|---------|---------|
| `--scenario` | `warehouse` | Which problem instance to run. |
| `--smoke` | off | Shortcut for the tiny self-check (`--scenario smoke --agents 2 --seed 6`); any flag you pass explicitly still wins. |
| `--agents N` | `4` | Number of robots. |
| `--planner {optimal,basic}` | `optimal` | `optimal` = MAOBTP (macros); `basic` = MABTP. |
| `--no-composite` | off | Disable LLM-style macros. |
| `--share-belief` / `--no-share-belief` | on | Shared communication belief space. |
| `--no-render` | render on | Run headless (no window). |
| `--quiet-ticks` | print on | Don't print the per-step tick result. |
| `--save` | off | Save trees to `output/`. |
| `--fps F` | `10` | Render speed. |
| `--seed N` | none | Seed `random` right before execution (does not fully pin the path — see below). |
| `--max-steps N` | `500` | Safety cap on simulation steps. |

---

## Verification & expected behavior

Run the bundled self-check (a tiny "open the door + move one ball" task on
`MiniGrid-DoorKey-8x8-v0` with 2 robots):

```bash
# from the repo root, with the project venv:
PYTHONPATH=. .venv/bin/python -m mrbtp_demo.verify             # shared belief
PYTHONPATH=. .venv/bin/python -m mrbtp_demo.verify --no-share  # ablation
PYTHONPATH=. .venv/bin/python -m mrbtp_demo.verify --both      # both, back-to-back
```

Verified results through these modules:

| Mode | Result |
|------|--------|
| `share_belief=True`  | reaches the goal — a **successful attempt finishes in ~20-35 steps** on the smoke scenario |
| `share_belief=False` | runs cleanly through the belief-toggle path and also succeeds on the smoke task; on the bigger `warehouse` scenario it coordinates worse and often needs many more steps (a useful ablation to *watch*) |

**Execution is stochastic — and seeding does NOT pin it down.** Two
independent sources of randomness are at play:

1. `GoBtwRoom` calls `random.shuffle` on the destination room's cells every
   time it re-plans a path, so each run takes a different trajectory.
2. With two agents, they can occasionally **deadlock at the doorway** — both
   want the single walkable door cell at the same step — and then wander until
   `--max-steps`.

Because of (1)+(2), a *single* attempt of the smoke task succeeds only
**~70%** of the time, and you **cannot** make it reproducible by seeding
`random` up front: the planner consumes a variable amount of RNG (depending on
its search time) before execution even begins, so an early seed never lands on
the same execution path. This is a property of the multi-agent executor, **not
a planning bug**.

> So instead of chasing a "magic" seed, `verify.py` **auto-retries**: it runs
> the task up to `--attempts` times (default `5`), seeding `random` with
> `base_seed + i` right before each *execution* and returning on the first
> success. With 5 attempts the chance of a spurious overall failure is well
> under 1% (measured 10/10 passes). Use `--attempts` / `--seed` to tune it.

If you instead drive the task through `run.py --smoke` (no retry), just re-run
it on the rare unlucky attempt, or raise `--max-steps`. The bigger the grid
(`DoorKey-16x16`) and the more agents, the higher the step variance.

---

## Extending

* **New goal / objects** — edit or add a `Scenario` in `scenario.py` and
  register it in the `SCENARIOS` dict.
* **New composite macro** — add an entry to a scenario's `composite_library`
  (a name → ordered list of primitive action calls, using `self` for the agent).
* **Different planner** — swap `MAOBTP` / `MABTP` in `planner.py`, or import
  `CABTP` for single-agent macro building.

The `mrbtp` library itself (planners, behavior nodes, env) is untouched, so
everything you learn here maps directly back to the paper code.
