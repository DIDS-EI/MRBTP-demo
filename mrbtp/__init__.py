"""mrbtp — Multi-Robot Behavior-Tree Planning toolkit.

This top-level package re-exports the most commonly used symbols so user
code can simply do::

    import mrbtp
    bt  = mrbtp.BehaviorTree(...)
    lib = mrbtp.BehaviorLibrary(...)
    env = mrbtp.make("MABTPG-MiniGrid-...-v0")

Sub-packages
------------
``mrbtp.btp``           Multi-robot BT planners
                         (``MRBTP``, ``MABTP``, ``MAOBTP``).
``mrbtp.behavior_tree`` Behavior-tree runtime, ``BTML`` parser,
                         ``BehaviorLibrary``.
``mrbtp.envs``          Environments (MiniGrid multi-agent grid worlds).
``mrbtp.utils``         Generic helpers (paths, RNG, string parsing).
"""

import os
import warnings

# Silence the noisy gymnasium "the environment is passed a reset..." warning.
warnings.filterwarnings("ignore", category=UserWarning, module="gymnasium.core")

# Hide the pygame "Hello from the pygame community" banner.
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "True")

import gymnasium  # noqa: E402  (must come after the env tweaks above)

from mrbtp.behavior_tree.behavior_library import BehaviorLibrary  # noqa: E402
from mrbtp.behavior_tree.behavior_tree import BehaviorTree  # noqa: E402
from mrbtp.envs.gridenv.minigrid.minigrid_env import MiniGridToMAGridEnv  # noqa: E402
from mrbtp.utils import ROOT_PATH  # noqa: E402
from mrbtp.utils.random import Random  # noqa: E402

# Initialise the global RNG once at import time.
Random.initialize()

# Convenience alias so users can write ``mrbtp.make(env_id)``.
make = gymnasium.make

__all__ = [
    "BehaviorTree",
    "BehaviorLibrary",
    "MiniGridToMAGridEnv",
    "Random",
    "ROOT_PATH",
    "make",
]
