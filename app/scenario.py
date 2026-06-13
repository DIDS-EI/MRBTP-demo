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
from minigrid.core.world_object import Ball, Door

from core import MiniGridToMAGridEnv
from core.envs.domains import resolve_behavior_lib_path


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

    # Which behavior library (Condition/Action node folder) this scenario's
    # agents plan with.  ``None`` -> the built-in MiniGrid library (the
    # historical default).  A domain scene (home / battle) points this at its
    # own folder under ``core/envs/domains/<domain>/behavior_lib`` so it can
    # use scene-specific predicates and actions on top of the shared grid
    # primitives.  Accepts either an absolute path or a registered domain name
    # (resolved by :func:`resolve_behavior_lib_path`).
    behavior_lib: str | None = None

    # Domain fluents that should hold *at episode start* (e.g. a room that is
    # already secured, an item that starts clean).  Most scenes leave this
    # empty — goals usually start unsatisfied so the plan has work to do.  These
    # strings are written into the env's ``domain_state`` right after the world
    # is built; conditions not listed here simply evaluate to ``False`` at t=0.
    initial_fluents: frozenset = field(default_factory=frozenset)

    # Which simulation backend builds the world.  ``"minigrid"`` (default) uses
    # the built-in grid env via :meth:`build_env`.  A robot simulator registers
    # its own factory through :func:`core.interfaces.register_backend` and is
    # then selectable here by name — the planner / executor never change because
    # both only depend on the :class:`~core.interfaces.SimBackend` protocol.
    # See docs/PLUGGABLE_BACKEND_DESIGN.html for the full接入规范.
    backend: str = "minigrid"

    # If ``True``, every locked door is unlocked right after the world is
    # built.  This models the "assume every agent can open any door" setup:
    # rooms are still partitioned by *door objects* (so the room-index DFS in
    # ``assign_cells_to_rooms`` keeps working and multi-room layouts stay
    # multi-room), but no agent needs to fetch a key first.  Used by the
    # multi-room ``home`` / ``battle`` scenes on the LockedRoom base.
    unlock_all_doors: bool = False

    # Rendering knobs (kept here so the scenario fully describes the demo).
    tile_size: int = 32
    agent_view_size: int = 7
    screen_size: int = 1024
    seed: int = 0

    # ----- Presentation-only metadata (the planning kernel never reads these) -
    # Both are attached as plain attributes onto the built env so a pluggable
    # renderer can pick them up via ``getattr`` — keeping the renderer optional
    # and the kernel untouched.
    #
    # ``room_aliases``: room-index -> human-readable name, e.g. {1: "厨房"}.
    #   Used only for on-screen room labels and documentation readability; the
    #   planner internally always refers to ``room-i``.
    # ``decor``: a list of furniture / cover descriptors that are NOT part of
    #   the grid geometry (so they are invisible to planning).  Each item is a
    #   dict like {"kind": "furniture", "cell": (x, y), "size": (w, h),
    #   "label": "冰箱"}.  Only the renderer reads them, to draw icons on top of
    #   the floor.  See scenes/home_service.py DECOR and scenes/battlefield.py.
    room_aliases: Dict[int, str] = field(default_factory=dict)
    decor: List[Dict] = field(default_factory=list)

    def build_env(self, render: bool = False) -> MiniGridToMAGridEnv:
        """Construct and reset the multi-agent MiniGrid environment.

        Args:
            render: if ``True`` the env keeps a ``"human"`` render mode so a
                pygame window is opened by :mod:`app.visualize`.
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

        env = MiniGridToMAGridEnv(
            minigrid_env,
            num_agent=self.num_agent,
            behavior_lib_path=resolve_behavior_lib_path(self.behavior_lib),
        )

        # ── 关键：在任何 reset 之前就决定 render_mode ──
        # MiniGridToMAGridEnv.__init__ 硬把 self.render_mode 设成 "human"，于是
        # 下面两次 env.reset() 会触发父类 MiniGridEnv.render()（human 模式）去调
        # ``pygame.display.set_mode``。而此刻 backends/pygame/render.py 顶部 import
        # 时设的 ``SDL_VIDEODRIVER=dummy`` 往往还没被清掉——一旦 display 子系统在
        # dummy 下完成初始化，就被**锁死成 dummy 驱动**，之后 renderer 再 pop 掉
        # 环境变量、再 set_mode 也回不到 cocoa。表现就是「窗口 surface 合法、日志
        # 照常跑完，但屏幕上根本没有窗口」。
        #
        # 修复：headless（render=False）时，在 reset 之前就把 render_mode 压成
        # None，从根上保证构造阶段绝不碰 pygame，dummy 驱动不会被提前锁死，留给
        # 真正的 live 渲染器一个干净的 display 子系统。
        if not render:
            env.render_mode = None

        # First reset lays out the rooms so we know where to drop objects.
        env.reset(seed=self.seed)

        for color, room_index in self.balls:
            env.place_object_in_room(Ball(color), room_index)

        # "Doors are not an obstacle in this scenario": unlock **and open**
        # every door, keeping the door *objects* in place.  The room-index DFS
        # treats a door cell as a wall regardless of its open/lock state, so the
        # multi-room partition is preserved — we only drop both the need to
        # fetch a key *and* the need to plan an explicit open step.
        #
        # Why open (``is_open=True``) and not merely unlock+close:
        #   The domain navigation primitive ``GoBtwRoom`` is *location-agnostic*
        #   in the home_service / battlefield libraries — its precondition was
        #   relaxed to just ``{ IsOpen(door) }`` so an agent can reach any room
        #   from any starting cell in a single back-chaining step.  That only
        #   pays off if ``IsOpen(door)`` already holds in the start state; if the
        #   door starts *closed*, the planner must back-chain an open step, and
        #   opening requires first walking to the door (``IsNear(agent,door)``),
        #   which re-introduces ``GoToInRoom(door)``'s room precondition and
        #   re-creates the very room-chain explosion we are eliminating (planning
        #   blew past the 20 s limit).  Opening the doors up front collapses that
        #   whole sub-problem: ``IsOpen`` enters the start state, ``GoBtwRoom``
        #   stops in one step, and proj2 / proj3 planning drops from a 20 s
        #   timeout to ~0.5 s.  proj1 never sets ``unlock_all_doors`` (its single
        #   door is genuinely locked and must be opened with a key), so this
        #   branch never runs for it — proj1 is byte-for-byte unaffected.
        if self.unlock_all_doors:
            grid = minigrid_env.unwrapped.grid
            for gx in range(grid.width):
                for gy in range(grid.height):
                    cell = grid.get(gx, gy)
                    if isinstance(cell, Door):
                        cell.is_locked = False
                        cell.is_open = True  # open & passable for everyone

        # Second reset re-indexes the world now that the balls exist.
        env.reset(seed=self.seed)

        # Seed any domain fluents that should hold at episode start.  The reset
        # above always clears ``domain_state`` to a fresh set, so we apply the
        # scenario's declared initial fluents on top of that clean slate.
        for fluent in self.initial_fluents:
            env.set_fluent(fluent, True)

        # Presentation-only metadata: attach to the env so a pluggable renderer
        # can read it via ``getattr``.  The planning kernel never touches these
        # attributes — they exist purely for on-screen labels / furniture icons.
        env.scene_room_aliases = dict(self.room_aliases)
        env.scene_decor = list(self.decor)

        # ``render_mode`` 已在 reset 之前按 ``render`` 压好（见上方注释）。这里
        # 不再重复设置——提前设置才能避免构造期 pygame 把 SDL 锁成 dummy。

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
    ``run.py --smoke`` and :mod:`app.verify` use it for.
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


# A registry so ``run.py`` can pick a scenario by name on the CLI.  The two
# built-ins live here; everything under ``scenes/`` is auto-discovered below.
SCENARIOS = {
    "warehouse": warehouse_scenario,
    "smoke": smoke_scenario,
}

# Themes recommended per scenario (entry point uses this as the default
# --theme when the user does not pass one).  Built-ins have no preference.
SCENARIO_THEMES: Dict[str, str] = {}


def _discover_scene_modules() -> None:
    """Auto-register every scenario declared under the ``scenes/`` package.

    The promise in ``scenes/README.md`` is *"adding a scenario = dropping one
    data file in ``scenes/``"*.  We honour it by walking that package and
    pulling in any module that exposes the tiny contract:

        NAME              -- the CLI name (str)
        make(num_agent)   -- a factory returning a Scenario

    Optionally a module may also export ``THEME`` (a colour-theme name) which
    we record in :data:`SCENARIO_THEMES` so the entry point can pick a sensible
    default palette.  Discovery failures are reported but never fatal — a
    broken scene file must not take down the whole demo.
    """
    try:
        import importlib
        import pkgutil

        import scenes
    except Exception:  # pragma: no cover - scenes/ is optional
        return

    for mod_info in pkgutil.iter_modules(scenes.__path__):
        if mod_info.name.startswith("_"):
            continue
        try:
            mod = importlib.import_module(f"scenes.{mod_info.name}")
        except Exception as exc:  # noqa: BLE001 - report and skip the bad file
            print(f"[scenes] skip '{mod_info.name}': {type(exc).__name__}: {exc}")
            continue

        name = getattr(mod, "NAME", None)
        factory = getattr(mod, "make", None)
        if not isinstance(name, str) or not callable(factory):
            continue  # not a scene module (no contract) -> ignore silently
        SCENARIOS[name] = factory
        theme = getattr(mod, "THEME", None)
        if isinstance(theme, str):
            SCENARIO_THEMES[name] = theme


_discover_scene_modules()
