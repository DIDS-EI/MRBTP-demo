"""Unified entry point: plan -> execute -> visualize, behind a small CLI.

Run from the repository root with the project's virtualenv, e.g.::

    # Watch the 4-robot warehouse demo with the shared belief space ON:
    python -m app.run

    # Same task, but DISABLE the shared communication belief space
    # (watch the team lose coordination):
    python -m app.run --no-share-belief

    # Headless (no window), just print behavior-tree ticks, and save the
    # planned trees as .bt / .svg under app/output/:
    python -m app.run --renderer none --save

    # Pluggable Pygame renderer: run headless and save an animated GIF replay
    # under app/output/pygame/ (remote-friendly, no display needed):
    python -m app.run --renderer pygame --theme home

    # Same, but the "battle" theme and PNG frames instead of a GIF:
    python -m app.run --renderer pygame --theme battle --render-mode save_frames

    # Use the simpler FIFO planner instead of the optimal one:
    python -m app.run --planner basic

    # Quick self-check shortcut (tiny 8x8 open-door + carry task), headless
    # and fast — handy as a smoke test.  Execution is stochastic, so a single
    # run succeeds ~70% of the time; for a robust pass/fail use app.verify
    # which auto-retries:
    python -m app.run --smoke --renderer none

    # Pure-symbolic VirtualHome (no window, no Unity, no MiniGrid):
    python -m app.run --scenario virtualhome --renderer none --agents 2

    # Or select the backend / domain explicitly on top of any scene:
    python -m app.run --scenario virtualhome --backend virtualhome \
        --domain virtualhome --renderer none

The three stages are intentionally separate modules so you can read or
reuse them independently:

    Part 1  app.planner.plan_behavior_trees
    Part 2  app.executor.execute
    Part 3  app.visualize.Visualizer
"""

from __future__ import annotations

import argparse
import os
import random
from pathlib import Path

from core.utils.tools import print_colored
from core.interfaces import available_backends, make_backend
from core.envs.domains import DOMAIN_REGISTRY, STANDALONE_DOMAINS
from core.agents import make_goal_provider

# Importing a backend module is what triggers its ``register_backend`` call.
# MiniGrid is registered lazily by ``make_backend``; symbolic backends are not.
import backends.virtualhome  # noqa: F401

from app.scenario import SCENARIOS, SCENARIO_THEMES
from app.planner import plan_behavior_trees
from app.executor import execute
from app.visualize import Visualizer


OUTPUT_DIR = Path(__file__).resolve().parent / "output"


def _known_backends():
    """Backend names shown in ``--help`` / accepted by ``--backend``."""
    return sorted({"minigrid"} | set(available_backends()))


def _known_domains():
    """Domain names shown in ``--help`` / accepted by ``--domain``.

    ``none`` explicitly falls back to the built-in MiniGrid behavior library.
    """
    return ["none"] + sorted(DOMAIN_REGISTRY)


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
        "--backend", choices=_known_backends(), default=None,
        help="Override the scenario's simulation backend.  Leaving it unset "
             "keeps the scenario's own choice (MiniGrid scenes -> 'minigrid', "
             "the VirtualHome scene -> 'virtualhome').  New backends become "
             "selectable here once their module is imported and calls "
             "core.interfaces.register_backend().",
    )
    p.add_argument(
        "--domain", choices=_known_domains(), default=None,
        help="Override the scenario's behavior-library domain.  Leaving it "
             "unset keeps the scenario's own choice; 'none' falls back to the "
             "built-in MiniGrid library.  'virtualhome' is a standalone "
             "symbolic domain and must be paired with '--backend virtualhome'.",
    )
    p.add_argument(
        "--smoke", action="store_true",
        help="Quick self-check preset: equivalent to "
             "'--scenario smoke --agents 2 --seed 6' on the tiny 8x8 "
             "open-door + carry-one-ball task.  Usually finishes in ~25 "
             "steps; combine with --no-render for a fast headless run.  "
             "NOTE: the executor is not fully seed-deterministic (two "
             "agents can occasionally deadlock at the door), so for a "
             "reliable CI gate use 'python -m app.verify', which "
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
    p.add_argument(
        "--single-expand", action="store_true",
        help="Division-of-labour planning (optimal planner only): each goal "
             "condition is back-chained by exactly ONE agent (round-robin "
             "assigned) instead of every agent.  Splits sub-goals across the "
             "team at plan time, giving each robot a smaller specialised tree "
             "that must cooperate to finish the shared goal.",
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
        "--goal-provider", choices=["static", "llm"], default="static",
        help="Decision layer that produces the team goal:\n"
             "'static' (default) = use the scenario's hard-coded goal "
             "(behaviour unchanged); 'llm' = route through the multi-robot "
             "LLM agent stub (core.agents.LLMGoalProvider), which currently "
             "falls back to the static goal until planning_llm_server is wired.",
    )
    p.add_argument(
        "--renderer", choices=["minigrid", "pygame", "none"], default="minigrid",
        help="Which renderer to drive via the executor's on_step hook:\n"
             "'minigrid' = the original numpy/pygame human window (needs a "
             "display); 'pygame' = the pluggable Pygame grid renderer that "
             "writes a GIF/PNG frames headlessly (remote-friendly, see "
             "--theme / --render-mode); 'none' = headless, ticks only.",
    )
    p.add_argument(
        "--theme", choices=["home", "battle", "default"], default=None,
        help="Colour theme for the 'pygame' renderer.  If omitted, the "
             "scenario's recommended theme is used (e.g. '--scenario home' "
             "defaults to the 'home' palette); falls back to 'home' otherwise.",
    )
    p.add_argument(
        "--render-mode", choices=["save_gif", "save_frames", "both"],
        default="save_gif",
        help="Output mode for the 'pygame' renderer.",
    )
    p.add_argument(
        "--no-render", dest="render", action="store_false",
        help="Deprecated alias for '--renderer none' (run headless).",
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
    parser = build_arg_parser()
    args = parser.parse_args(argv)

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

    # ``--no-render`` is the old way to ask for a headless run; fold it into
    # the new ``--renderer`` choice so the rest of main() has one source of
    # truth.  Explicit ``--renderer`` always wins over the deprecated flag.
    if not args.render and args.renderer == "minigrid":
        args.renderer = "none"

    # Only the original 'minigrid' renderer needs the env to open a real
    # "human" pygame window.  The pluggable 'pygame' renderer draws from the
    # env's grid data on its own offscreen Surface, so the env stays headless.
    use_minigrid_window = args.renderer == "minigrid"

    # In headless mode the underlying MiniGrid env still constructs a pygame
    # window during ``reset()``; point SDL at its dummy drivers so it does not
    # try (and fail) to open a real one on a machine with no display.
    if not use_minigrid_window:
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

    # ---- Scenario ------------------------------------------------------- #
    scenario = SCENARIOS[args.scenario](num_agent=args.agents)
    if args.backend is not None:
        scenario.backend = args.backend
    if args.domain is not None:
        scenario.behavior_lib = None if args.domain == "none" else args.domain

    symbolic_backend = scenario.backend != "minigrid"
    if symbolic_backend and getattr(scenario, "symbolic_task", None) is None:
        parser.error(
            f"--backend {scenario.backend!r} 需要一个带符号任务的场景；"
            "请配合 '--scenario virtualhome' 使用。"
        )
    domain = scenario.behavior_lib if isinstance(scenario.behavior_lib, str) else None
    if domain in STANDALONE_DOMAINS and not symbolic_backend:
        parser.error(
            f"域 '{scenario.behavior_lib}' 是纯符号域，请加 "
            "'--backend virtualhome'（不能配 MiniGrid 后端）。"
        )
    if symbolic_backend and domain not in STANDALONE_DOMAINS:
        parser.error(
            f"--backend {scenario.backend!r} 需要 standalone 符号域；"
            f"当前 behavior_lib={scenario.behavior_lib!r}，"
            "请加 '--domain virtualhome'。"
        )

    # A symbolic world has no grid / window to draw.  Force headless so the
    # user does not have to remember '--renderer none' for the VH scene.
    if symbolic_backend and args.renderer != "none":
        print_colored(
            f"后端 '{scenario.backend}' 是纯符号世界，没有画面；"
            "已自动切换到 --renderer none。", "yellow",
        )
        args.renderer = "none"
        use_minigrid_window = False

    print_colored(
        f"Scenario '{scenario.name}': {scenario.num_agent} agents, "
        f"backend={scenario.backend}, domain={scenario.behavior_lib}, "
        f"goal = {set(scenario.goal)}",
        "blue",
    )

    # Build the world through the backend factory so the scenario's chosen
    # backend ("minigrid" by default; a robot simulator once registered) is
    # honoured.  The planner / executor below only see the SimBackend protocol,
    # so swapping the backend never touches them.
    env = make_backend(scenario.backend, scene=scenario, render=use_minigrid_window)

    # ---- Part 0: decide the goal (decision layer) ----------------------- #
    # The GoalProvider turns "world state -> team goal".  The default static
    # provider just returns the scenario's goal (behaviour unchanged); pass
    # --goal-provider llm to route through the (stubbed) LLM agent instead.
    goal_provider = make_goal_provider(scenario, kind=args.goal_provider)
    goal = goal_provider.propose_goal(env)
    if set(goal) != set(scenario.goal):
        print_colored(f"GoalProvider proposed goal = {set(goal)}", "blue")

    # ---- Part 1: plan --------------------------------------------------- #
    plan = plan_behavior_trees(
        env,
        scenario,
        goal=goal,
        optimal=(args.planner == "optimal"),
        use_composite_actions=not args.no_composite,
        single_expand=args.single_expand,
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
    # Build the per-step callback according to the chosen renderer.  Both
    # paths still print the behavior-tree ticks via the Visualizer; the
    # difference is *where the frame goes*.
    viz = Visualizer(
        render=use_minigrid_window, print_tree=args.print_tree, fps=args.fps
    )
    pygame_renderer = None
    if args.renderer == "pygame":
        # Pluggable renderer: ticks via the Visualizer, frames via the
        # backend-agnostic PygameGridRenderer (headless -> GIF/PNG).
        from core.interfaces import make_renderer

        # Theme resolution: an explicit --theme always wins; otherwise fall
        # back to the scenario's recommended palette (e.g. the 'home' scene
        # ships with the 'home' theme), and finally to 'home' as a default.
        theme = args.theme or SCENARIO_THEMES.get(args.scenario, "home")

        pygame_renderer = make_renderer(
            "pygame",
            theme=theme,
            mode=args.render_mode,
            out_dir=str(OUTPUT_DIR / "pygame"),
            fps=args.fps,
        )

        def on_step(record, env):
            viz.on_step(record, env)          # still prints the BT ticks
            pygame_renderer.render(env)       # + draws a frame

    else:
        on_step = viz.on_step

    # ---- Part 2: execute (drives Part 3 via on_step) -------------------- #
    result = execute(
        env,
        plan,
        share_belief=args.share_belief,
        max_steps=args.max_steps,
        on_step=on_step,
        print_ticks=False,  # the visualizer already prints ticks
    )

    print_colored(
        f"\nResult: success={result.success}, steps={result.steps}, "
        f"share_belief={result.share_belief}",
        "green" if result.success else "red",
    )

    # ---- Part 3 finalize ------------------------------------------------ #
    if pygame_renderer is not None:
        out = pygame_renderer.close()         # compose the GIF, release pygame
        if out:
            print_colored(f"Saved replay -> {out}", "green")
    elif use_minigrid_window:
        viz.hold_open(env)

    return 0 if result.success else 1


if __name__ == "__main__":
    raise SystemExit(main())
