"""
``mrbtp.envs`` — environment adapters used by the planner.

Layout
------

* ``mrbtp.envs.base``     — abstract base classes (``Env``, ``Agent``) shared
                             by every concrete environment.
* ``mrbtp.envs.gridenv``  — MiniGrid-based 2-D multi-agent grid worlds.  The
                             only concrete implementation in this demo lives
                             in ``mrbtp.envs.gridenv.minigrid``.

Naming convention
-----------------

Sub-packages use ``snake_case`` lowercase identifiers.  Compact compound
words such as ``gridenv`` are kept without an underscore because they are
well-established short forms across the codebase.
"""
