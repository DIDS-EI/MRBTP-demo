"""_rooms4 —— a hand-built **linear 4-room** layout shared by the multi-room scenes.

Why this exists
---------------
The stock MiniGrid multi-room envs were all unusable as a clean "3+ rooms"
base for the demo:

    * ``DoorKey``      — only 2 rooms.
    * ``FourRooms``    — the openings are blank cells, so the room-index DFS
                          flood-fills straight through them and sees 1 room.
    * ``MultiRoom``    — shattered into many uneven snake-shaped rooms.
    * ``LockedRoom``   — genuinely 6 rooms, but its 6 doors blow up the
                          ``GoBtwRoom`` cross-room action model: even a single
                          1-ball goal took ~25 s to plan.

So we hand-build the simplest honest multi-room world: four equal rooms in a
horizontal row, separated by three **unlocked** doors, forming a chain

    room-0  ─door-0─  room-1  ─door-1─  room-2  ─door-2─  room-3

Every neighbour is exactly one ``GoBtwRoom`` hop apart, the partition is clean
(the room-index DFS treats each door *object* as a wall, so it splits into
exactly four rooms), and a compact 15x7 grid plans a short carry in well under
a second.

The doors are created unlocked on purpose: this is the "assume every agent can
open any door" world the scenes want — rooms stay partitioned by door objects,
but nobody has to fetch a key first.

Design rule for callers
------------------------
Planning cost scales with **(number of goals) x (carry hops) x (room size)**,
*not* with the number of rooms.  A probe showed:

    * 1 ball, 1-hop carry   -> 0.09 s
    * 1 ball, 2-hop carry   -> 0.43 s
    * 2 balls, independent  -> 23 s   (!)

So keep each scene to **one or two short-hop goals** and lean on the four
rooms for *spatial narrative* (each room plays a semantic role) rather than
piling on goal count.
"""
from __future__ import annotations

import gymnasium as gym
from minigrid.core.grid import Grid
from minigrid.core.mission import MissionSpace
from minigrid.core.world_object import Door, Key
from minigrid.minigrid_env import MiniGridEnv

#: The gym id every multi-room scene passes as ``Scenario.env_id``.  This one
#: is the all-unlocked chain used by the ready-to-run ``home`` / ``battle``
#: scenes.
ENV_ID = "MRBTP-Linear4Room-v0"

#: A variant where ``door-0`` is **locked** and a matching key sits in room-0.
#: Kept for reference only — **no scene or project currently uses it**.  The
#: locked-door flow was dropped because the executor dead-loops on locked doors
#: (``max_steps`` never fires, 0 actions emitted); every scene/project now uses
#: the all-unlocked :data:`ENV_ID` instead.  Leave this here until that
#: executor bug is fixed and the "fetch key -> open door -> carry" flow can be
#: revived as a teaching project.
ENV_ID_LOCKED = "MRBTP-Linear4RoomLocked-v0"

#: Default compact footprint — four ~3x5 rooms, fast to plan.
DEFAULT_WIDTH = 15
DEFAULT_HEIGHT = 7


class Linear4RoomEnv(MiniGridEnv):
    """Four equal rooms in a row, split by three doors forming a chain.

    The layout is **fixed** (not randomised), so room indices and door ids are
    stable across runs — essential for declaring ``balls=[(color, room)]`` and
    macro libraries that name ``room-i`` / ``door-i`` explicitly.

    Args:
        lock_first_door: when ``True``, ``door-0`` (between room-0 and room-1)
            is created *locked* and a matching yellow key is dropped in room-0.
            All other doors stay unlocked.  When ``False`` (default) every door
            is unlocked — the "assume every agent can open any door" world.
    """

    def __init__(self, width: int = DEFAULT_WIDTH, height: int = DEFAULT_HEIGHT,
                 max_steps: int | None = None, lock_first_door: bool = False,
                 **kwargs):
        if max_steps is None:
            max_steps = 8 * width * height
        self._lock_first_door = lock_first_door
        mission_space = MissionSpace(mission_func=lambda: "move the balls")
        super().__init__(
            mission_space=mission_space,
            width=width,
            height=height,
            max_steps=max_steps,
            see_through_walls=True,
            **kwargs,
        )

    @staticmethod
    def _split_cols(width: int) -> list[int]:
        """Column x of each of the three interior vertical walls."""
        return [width * (i + 1) // 4 for i in range(3)]

    def _gen_grid(self, width: int, height: int) -> None:
        self.grid = Grid(width, height)
        self.grid.wall_rect(0, 0, width, height)
        door_row = height // 2
        for idx, sx in enumerate(self._split_cols(width)):
            self.grid.vert_wall(sx, 0)
            locked = self._lock_first_door and idx == 0
            self.put_obj(Door("yellow", is_locked=locked), sx, door_row)
        if self._lock_first_door:
            # Drop the key that opens door-0 inside room-0 (top-left cell area).
            self.put_obj(Key("yellow"), 1, 1)
            self.agent_pos = (2, 1)
        else:
            self.agent_pos = (1, 1)
        # Agent starts in room-0 facing east toward room-1.
        self.agent_dir = 0
        self.mission = "move the balls"


class Linear4RoomLockedEnv(Linear4RoomEnv):
    """:class:`Linear4RoomEnv` with ``door-0`` locked + a key in room-0."""

    def __init__(self, *args, **kwargs):
        kwargs["lock_first_door"] = True
        super().__init__(*args, **kwargs)


# Register exactly once, when this module is first imported.  Scene modules do
# ``from scenes import _rooms4`` at import time so the ids are live before any
# ``gym.make(_rooms4.ENV_ID)`` in ``Scenario.build_env`` runs.
if ENV_ID not in gym.registry:
    gym.register(id=ENV_ID, entry_point=__name__ + ":Linear4RoomEnv")
if ENV_ID_LOCKED not in gym.registry:
    gym.register(id=ENV_ID_LOCKED, entry_point=__name__ + ":Linear4RoomLockedEnv")
