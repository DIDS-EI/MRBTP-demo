"""Scenario definition — *what world, what objects, what goal*.

This module isolates every "problem setup" decision into one place so you
can tweak the demo without touching the planning / execution / rendering
code.  A :class:`Scenario` bundles:

    * the MiniGrid layout (env id + size),
    * the movable objects placed into the rooms,
    * the symbolic ``goal`` the team must jointly satisfy,
    * the per-agent composite-action library (LLM-style macro sub-trees).

The default :func:`warehouse_scenario` reproduces the classic 4-ball
DoorKey demo from ``test_multi_minigrid_single_demo/main.py``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple

import gymnasium as gym
from minigrid.core.world_object import Ball

from core import MiniGridToMAGridEnv


# A composite-action library is, per agent, a dict mapping a macro name to
# the ordered list of primitive actions it expands into.  ``self`` is a
# placeholder that gets bound to the concrete ``agent-i`` at plan time.
CompositeLibrary = List[Dict[str, List[str]]]


@dataclass
class Scenario:
    """A self-contained MRBTP problem instance."""

    name: str
    env_id: str
    num_agent: int
    # Objects to drop into the world: list of (color, room_index).
    balls: List[Tuple[str, int]]
    # The symbolic goal the whole team must satisfy.
    goal: frozenset
    # Per-agent composite-action macros (may be empty -> no macros).
    composite_library: CompositeLibrary = field(default_factory=list)

    # Rendering knobs (kept here so the scenario fully describes the demo).
    tile_size: int = 32
    agent_view_size: int = 7
    screen_size: int = 1024
    seed: int = 0

    def build_env(self, render: bool = False) -> MiniGridToMAGridEnv:
        """Construct and reset the multi-agent MiniGrid environment.

        Args:
            render: if ``True`` the env keeps a ``"human"`` render mode so a
                pygame window is opened by :mod:`mrbtp_demo.visualize`.
                When ``False`` everything runs headless.

        Returns:
            A reset :class:`MiniGridToMAGridEnv` with all balls placed.
        """
        minigrid_env = gym.make(
            self.env_id,
            tile_size=self.tile_size,
            render_mode=None,
            agent_view_size=self.agent_view_size,
            screen_size=self.screen_size,
        )

        env = MiniGridToMAGridEnv(minigrid_env, num_agent=self.num_agent)
        # First reset lays out the rooms so we know where to drop objects.
        env.reset(seed=self.seed)

        for color, room_index in self.balls:
            env.place_object_in_room(Ball(color), room_index)

        # Second reset re-indexes the world now that the balls exist.
        env.reset(seed=self.seed)

        # ``render_mode`` is forced to "human" inside MiniGridToMAGridEnv;
        # when we do NOT want a window we silence it back to None so
        # ``env.step()`` never tries to open pygame.
        if not render:
            env.render_mode = None

        return env


def warehouse_scenario(num_agent: int = 4) -> Scenario:
    """The canonical 'move balls between rooms' DoorKey demo.

    Three balls start in room-0 plus a red 'anchor' ball in room-1.  The
    team must move ball-0 into room-1 and park ball-1 / ball-2 next to the
    red ball — which first requires somebody to fetch the key and open the
    locked door.  The composite-action library encodes exactly those
    multi-step macros (one per logical job).
    """
    composite_library: CompositeLibrary = [
        {
            "GetKeyAndOpenDoor": [
                "GoToInRoom(self,key-0,room-0)",
                "PickUp(self,key-0)",
                "GoToInRoom(self,door-0,room-0)",
                "Toggle(self,door-0)",
            ],
        },
        {
            "Move0BetweenRooms": [
                "GoToInRoom(self,ball-0,room-0)",
                "PickUp(self,ball-0)",
                "GoBtwRoom(self,room-0,room-1)",
                "PutInRoom(self,ball-0,room-1)",
            ],
        },
        {
            "Move1NearRed": [
                "GoToInRoom(self,ball-1,room-0)",
                "PickUp(self,ball-1)",
                "GoBtwRoom(self,room-0,room-1)",
                "PutNearInRoom(self,ball-1,ball-3,room-1)",
            ],
        },
        {
            "Move2NearRed": [
                "GoToInRoom(self,ball-2,room-0)",
                "PickUp(self,ball-2)",
                "GoBtwRoom(self,room-0,room-1)",
                "PutNearInRoom(self,ball-2,ball-3,room-1)",
            ],
        },
    ]
    # The composite library must have exactly one dict per agent; if the
    # caller asks for fewer agents we pad/truncate so the demo still runs.
    composite_library = _fit_library_to_agents(composite_library, num_agent)

    return Scenario(
        name="warehouse",
        env_id="MiniGrid-DoorKey-16x16-v0",
        num_agent=num_agent,
        balls=[
            ("green", 0),
            ("purple", 0),
            ("yellow", 0),
            ("red", 1),
        ],
        goal=frozenset(
            {
                "IsInRoom(ball-0,room-1)",
                "IsNear(ball-1,ball-3)",
                "IsNear(ball-2,ball-3)",
            }
        ),
        composite_library=composite_library,
    )


def smoke_scenario(num_agent: int = 2) -> Scenario:
    """A deliberately tiny 8x8 task for quick, near-deterministic self-checks.

    Unlike the canonical 4-ball :func:`warehouse_scenario` (which makes the
    team grind through open-door + three separate carries, so execution runs
    long and is heavily affected by ``GoBtwRoom`` randomness), this scenario
    keeps just **one job per agent**: somebody opens the locked door, somebody
    moves the green ball into room-1.  It finishes in a few dozen steps and is
    robust enough to use as a CI-style smoke test, which is exactly what both
    ``run.py --smoke`` and :mod:`mrbtp_demo.verify` use it for.
    """
    composite_library: CompositeLibrary = [
        {
            "GetKeyAndOpenDoor": [
                "GoToInRoom(self,key-0,room-0)",
                "PickUp(self,key-0)",
                "GoToInRoom(self,door-0,room-0)",
                "Toggle(self,door-0)",
            ],
        },
        {
            "Move0BetweenRooms": [
                "GoToInRoom(self,ball-0,room-0)",
                "PickUp(self,ball-0)",
                "GoBtwRoom(self,room-0,room-1)",
                "PutInRoom(self,ball-0,room-1)",
            ],
        },
    ]
    return Scenario(
        name="smoke-8x8",
        env_id="MiniGrid-DoorKey-8x8-v0",
        num_agent=num_agent,
        balls=[("green", 0)],
        goal=frozenset({"IsInRoom(ball-0,room-1)"}),
        composite_library=_fit_library_to_agents(composite_library, num_agent),
        seed=0,
    )


def _fit_library_to_agents(
    library: CompositeLibrary, num_agent: int
) -> CompositeLibrary:
    """Reshape a per-job macro library so it has exactly ``num_agent`` slots.

    * If there are more jobs than agents, the extra jobs are merged into the
      last agent's dict (so every macro is still available to *some* agent).
    * If there are fewer jobs than agents, the remaining agents get empty
      macro dicts (they will rely purely on primitive actions).
    """
    if num_agent <= 0:
        return []

    if len(library) <= num_agent:
        padded = list(library)
        while len(padded) < num_agent:
            padded.append({})
        return padded

    # More jobs than agents: keep the first ``num_agent-1`` as-is and fold
    # the rest into the final agent.
    head = library[: num_agent - 1]
    tail_merged: Dict[str, List[str]] = {}
    for job in library[num_agent - 1:]:
        tail_merged.update(job)
    return head + [tail_merged]


# A registry so ``run.py`` can pick a scenario by name on the CLI.
SCENARIOS = {
    "warehouse": warehouse_scenario,
    "smoke": smoke_scenario,
}
