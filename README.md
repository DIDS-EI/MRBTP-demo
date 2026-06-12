# mrbtp-demo

A **minimal, self-contained** demo of **M**ulti-**R**obot **B**ehavior-**T**ree
**P**lanning (MRBTP) on MiniGrid. Several robots are given a single symbolic
goal (e.g. *"get a ball into the next room"*); the planner back-chains it into
one behavior tree per robot, and the executor runs them in a shared 2-D grid
world — optionally sharing a communication belief space so they coordinate
instead of stepping on each other.

This repo is a trimmed extract of the full `mrbtp` research codebase: it ships
**only** the MiniGrid planning/execution path, with the VirtualHome simulator,
the numerical env, the LLM client and other unused extras removed. The whole
thing is ~750 KB and runs on a few lightweight pip packages.

```text
mrbtp-demo/
├── pyproject.toml          # Packaging + pinned runtime deps (pip install -e .)
├── requirements.txt        # The same deps, as a plain list
├── .gitignore
│
├── mrbtp_demo/             # ← the demo: thin, readable orchestration layer
│   ├── __init__.py
│   ├── scenario.py         # World / objects / goal / composite macros
│   ├── planner.py          # Part 1 · goal → one behavior tree per robot
│   ├── executor.py         # Part 2 · tick the trees, shared-belief on/off
│   ├── visualize.py         # Part 3 · render MiniGrid + print tick results
│   ├── run.py              # CLI gluing the three parts together
│   ├── verify.py           # Headless self-check (auto-retry smoke test)
│   ├── README.md           # Deep-dive into the three-part design
│   └── TUTORIAL.html       # Illustrated, click-through tutorial
│
├── examples/              # ← 6 progressive single-file tutorials (start here)
├── projects/              # ← 3 practice projects: starter (TODO) + solution
│
└── mrbtp/                 # ← trimmed planning library the demo builds on
    ├── __init__.py
    ├── behavior_tree/      # BT runtime + BTML DSL parser + drawing
    ├── btp/                # MABTP / MAOBTP / CABTP back-chaining planners
    ├── envs/
    │   ├── base/           # Abstract env / agent base classes
    │   └── gridenv/
    │       └── minigrid/   # The MiniGrid adapter + behavior library
    └── utils/              # RNG, A*, path & string helpers
```

## Install

```bash
cd mrbtp-demo
python3 -m venv .venv && source .venv/bin/activate
pip install -e .            # installs mrbtp_demo + the trimmed mrbtp + deps
```

Python ≥ 3.9 is supported. `pip install -e .` registers two console commands,
`mrbtp-demo` and `mrbtp-verify`.

## Run

```bash
# Full warehouse scenario, 4 robots, with a window:
python -m mrbtp_demo.run

# Quick headless smoke task (open a door + carry one ball, 2 robots):
python -m mrbtp_demo.run --smoke --no-render

# Headless self-check with automatic retry (robust pass/fail):
python -m mrbtp_demo.verify
# …or, via the installed console script:
mrbtp-verify
```

> **Heads-up — execution is stochastic.** `GoBtwRoom` reshuffles its path every
> time it re-plans, and two robots can occasionally deadlock at a doorway, so a
> *single* smoke run succeeds only ~70 % of the time and seeding does **not**
> pin it down. That's why `verify.py` auto-retries (default 5 attempts) — see
> `mrbtp_demo/README.md` and `TUTORIAL.html` for the full explanation.

## Learn by doing — `examples/` and `projects/`

New here? Don't start from the source. Start from these two hands-on tracks
(both written in Chinese, heavily commented, every file runnable as-is):

- **`examples/`** — 6 progressive single-file tutorials, from "what does the
  world look like" to "inspect & export the planned behavior tree". Run them in
  order; see `examples/README.md` for the learning path.
- **`projects/`** — 3 small practice projects with **starter (TODO blanks) +
  reference solution**. You design the goal / composite library yourself, then
  check against `solution/`. See `projects/README.md`.

## Learn more

- **`mrbtp_demo/README.md`** — the three-part architecture, the `share_belief`
  switch, the CLI flag table and how to extend the demo.
- **`mrbtp_demo/TUTORIAL.html`** — an illustrated, scroll-spy tutorial with
  inline SVG diagrams of the pipeline, data flow, behavior-tree structure and
  the two sources of non-determinism.

## What was trimmed vs. upstream `mrbtp`

| Removed | Why |
|---------|-----|
| `envs/virtualhome/` (~470 KB) | 3-D household simulator; this demo is MiniGrid-only. A single dead `import UnityCommunication` in `envs/base/env.py` used to pull it all in — that line is now gone. |
| `envs/numerical_env/` | Symbolic benchmarking env, never loaded by the MiniGrid path. |
| `envs/gridenv/minigrid_computation_env/` | Computation-only grid variant, unused here. |
| `llm_client/` | OpenAI client for LLM-driven macros; the demo uses pre-defined macros. |
| ~12 heavy pip deps | `openai`, `hydra-core`, `sympy`, `matplotlib`, `opencv`, `networkx`, `tabulate`, `latextable`, `ipdb`, `tqdm`, `requests`, `tdw` — none are imported by the trimmed code. |

The remaining `mrbtp` planning algorithms (MABTP / MAOBTP / back-chaining /
composite actions) are **byte-for-byte the upstream code** — only unused
sub-packages and one dead import were removed.
