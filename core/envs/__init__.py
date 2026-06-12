"""
``core.envs`` — environment adapters used by the planner.

Layout
------

* ``core.envs.base``     — abstract base classes (``Env``, ``Agent``) shared
                             by every concrete environment.
* ``core.envs.gridenv``  — MiniGrid-based 2-D multi-agent grid worlds.  The
                             only concrete implementation in this demo lives
                             in ``core.envs.gridenv.minigrid``.

Naming convention
-----------------

Sub-packages use ``snake_case`` lowercase identifiers.  Compact compound
words such as ``gridenv`` are kept without an underscore because they are
well-established short forms across the codebase.
"""
