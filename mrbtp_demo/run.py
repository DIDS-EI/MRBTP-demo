"""Unified entry point: plan -> execute -> visualize, behind a small CLI.

Run from the repository root with the project's virtualenv, e.g.::

    # Watch the 4-robot warehouse demo with the shared belief space ON:
    python -m mrbtp_demo.run

    # Same task, but DISABLE the shared communication belief space
    # (watch the team lose coordination):
    python -m mrbtp_demo.run --no-share-belief

    # Headless (no window), just print behavior-tree ticks, and save the
    # planned trees as .bt / .svg under mrbtp_demo/output/:
    python -m mrbtp_demo.run --no-render --save

    # Use the simpler FIFO planner instead of the optimal one:
    python -m mrbtp_demo.run --planner basic

    # Quick self-check shortcut (tiny 8x8 open-door + carry task), headless
    # and fast — handy as a smoke test.  Execution is stochastic, so a single
    # run succeeds ~70% of the time; for a robust pass/fail use mrbtp_demo.verify
    # which auto-retries:
    python -m mrbtp_demo.run --smoke --no-render

The three stages are intentionally separate modules so you can read or
reuse them independently:

    Part 1  mrbtp_demo.planner.plan_behavior_trees
    Part 2  mrbtp_demo.executor.execute
    Part 3  mrbtp_demo.visualize.Visualizer
"""

from __future__ import annotations

import argparse
import os
import random
from pathlib import Path

from mrbtp.utils.tools import print_colored

from mrbtp_demo.scenario import SCENARIOS
from mrbtp_demo.planner import plan_behavior_trees
from mrbtp_demo.executor import execute
from mrbtp_demo.visualize import Visualizer


OUTPUT_DIR = Path(__file__).resolve().parent / "output"


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="MRBTP demo: plan, execute and visualize multi-robot "
        "behavior trees in MiniGrid.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument(
        "--scenario", choices=sorted(SCENARIOS), default="warehouse",
        help="Which problem instance to run.",
    )
    p.add_argument(
        "--smoke", action="store_true",
        help="Quick self-check preset: equivalent to "
             "'--scenario smoke --agents 2 --seed 6' on the tiny 8x8 "
             "open-door + carry-one-ball task.  Usually finishes in ~25 "
             "steps; combine with --no-render for a fast headless run.  "
             "NOTE: the executor is not fully seed-deterministic (two "
             "agents can occasionally deadlock at the door), so for a "
             "reliable CI gate use 'python -m mrbtp_demo.verify', which "
             "auto-retries.",
    )
    p.add_argument(
        "--agents", type=int, default=4,
        help="Number of robots in the team.",
    )
    p.add_argument(
        "--planner", choices=["optimal", "basic"], default="optimal",
        help="'optimal' = MAOBTP (cost-aware, supports macros); "
             "'basic' = MABTP (FIFO baseline, primitives only).",
    )
    p.add_argument(
        "--no-composite", action="store_true",
        help="Disable LLM-style composite-action macros.",
    )

    # Part 2 — the headline belief-space switch.
    belief = p.add_mutually_exclusive_group()
    belief.add_argument(
        "--share-belief", dest="share_belief", action="store_true",
        help="Enable the shared communication belief space (default).",
    )
    belief.add_argument(
        "--no-share-belief", dest="share_belief", action="store_false",
        help="Disable the shared belief space (coordination ablation).",
    )
    p.set_defaults(share_belief=True)

    # Part 3 — rendering / output.
    p.add_argument(
        "--no-render", dest="render", action="store_false",
        help="Run headless (no pygame window).",
    )
    p.set_defaults(render=True)
    p.add_argument(
        "--quiet-ticks", dest="print_tree", action="store_false",
        help="Do not print the behavior-tree tick result each step.",
    )
    p.set_defaults(print_tree=True)
    p.add_argument(
        "--save", action="store_true",
        help="Save planned trees as robot-i.bt / robot-i.svg in output/.",
    )
    p.add_argument(
        "--fps", type=float, default=10.0, help="Render frames per second.",
    )
    p.add_argument(
        "--max-steps", type=int, default=500,
        help="Safety cap on simulation steps.",
    )
    p.add_argument(
        "--seed", type=int, default=None,
        help="If set, seed ``random`` right before execution so "
             "GoBtwRoom's random walk (and hence the step count) is "
             "reproducible.  --smoke sets this to 6 automatically.",
    )
    p.add_argument("--verbose", action="store_true", help="Verbose planning.")
    return p


def main(argv=None) -> int:
    args = build_arg_parser().parse_args(argv)

    # ---- --smoke preset ------------------------------------------------- #
    # A one-flag shortcut for the tiny, near-deterministic self-check.  We
    # only override values the user left at their defaults, so e.g.
    # ``--smoke --agents 3`` still honours the explicit agent count.
    if args.smoke:
        if args.scenario == "warehouse":   # still the default -> use smoke
            args.scenario = "smoke"
        if args.agents == 4:               # warehouse default -> shrink
            args.agents = 2
        if args.seed is None:
            args.seed = 6

    # In headless mode the underlying MiniGrid env still constructs a pygame
    # window during ``reset()``; point SDL at its dummy drivers so it does not
    # try (and fail) to open a real one on a machine with no display.
    if not args.render:
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

    # ---- Scenario ------------------------------------------------------- #
    scenario = SCENARIOS[args.scenario](num_agent=args.agents)
    print_colored(
        f"Scenario '{scenario.name}': {scenario.num_agent} agents, "
        f"goal = {set(scenario.goal)}",
        "blue",
    )

    env = scenario.build_env(render=args.render)

    # ---- Part 1: plan --------------------------------------------------- #
    plan = plan_behavior_trees(
        env,
        scenario,
        optimal=(args.planner == "optimal"),
        use_composite_actions=not args.no_composite,
        save_dir=str(OUTPUT_DIR) if args.save else None,
        verbose=args.verbose,
    )
    print_colored(
        f"Planned {len(plan.bt_list)} behavior trees in "
        f"{plan.planning_time:.3f}s (expanded {plan.expanded_num} nodes).",
        "green",
    )

    # Seed *after* planning, right before execution.  The planner consumes
    # the RNG by a variable amount (its search time differs run to run), so
    # seeding earlier cannot pin down the execution path; seeding here makes
    # GoBtwRoom's random.shuffle — and thus the step count — reproducible.
    if args.seed is not None:
        random.seed(args.seed)

    # ---- Part 3 hook (used during Part 2) ------------------------------- #
    viz = Visualizer(
        render=args.render, print_tree=args.print_tree, fps=args.fps
    )

    # ---- Part 2: execute (drives Part 3 via on_step) -------------------- #
    result = execute(
        env,
        plan,
        share_belief=args.share_belief,
        max_steps=args.max_steps,
        on_step=viz.on_step,
        print_ticks=False,  # the visualizer already prints ticks
    )

    print_colored(
        f"\nResult: success={result.success}, steps={result.steps}, "
        f"share_belief={result.share_belief}",
        "green" if result.success else "red",
    )

    if args.render:
        viz.hold_open(env)

    return 0 if result.success else 1


if __name__ == "__main__":
    raise SystemExit(main())
