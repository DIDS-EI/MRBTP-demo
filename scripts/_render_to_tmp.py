"""Headless render of a scene to /tmp for visual inspection.

Usage:
    SDL_VIDEODRIVER=dummy ./.venv/bin/python scripts/_render_to_tmp.py home /tmp/home
    SDL_VIDEODRIVER=dummy ./.venv/bin/python scripts/_render_to_tmp.py battle /tmp/battle

Builds the scene, plans, executes, and drives the PygameGridRenderer with
out_dir pointing at the given (writable) directory, producing replay.gif +
PNG frames.  Used only for local verification when the project tree is not
writable; the real entry point is ``python -m app.run --renderer pygame``.
"""
from __future__ import annotations

import os
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import sys
import random
from pathlib import Path

# Running as ``python scripts/_render_to_tmp.py`` puts ``scripts/`` on sys.path
# (not the project root), so ``import scenes`` inside scenario discovery would
# miss the package.  Prepend the project root so discovery sees scenes/.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.scenario import SCENARIOS, SCENARIO_THEMES
from app.planner import plan_behavior_trees
from app.executor import execute
from core.interfaces import make_renderer


def main() -> None:
    which = sys.argv[1] if len(sys.argv) > 1 else "home"
    out_dir = sys.argv[2] if len(sys.argv) > 2 else f"/tmp/{which}"

    random.seed(0)
    scenario = SCENARIOS[which](num_agent=2)
    env = scenario.build_env(render=False)
    plan = plan_behavior_trees(env, scenario, optimal=True,
                               use_composite_actions=True)

    theme = SCENARIO_THEMES.get(which, "home")
    renderer = make_renderer(
        "pygame", theme=theme, mode="both",
        out_dir=out_dir, fps=6.0, gif_name=f"{which}.gif",
    )

    def on_step(record, env):
        renderer.render(env)

    result = execute(env, plan, share_belief=True, max_steps=300,
                     on_step=on_step, print_ticks=False)
    out = renderer.close()
    print(f"scene={which} success={result.success} steps={result.steps} gif={out}")


if __name__ == "__main__":
    main()
