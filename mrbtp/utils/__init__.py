"""Generic, environment-agnostic helpers used across :mod:`mrbtp`.

This module deliberately re-exports a handful of small, frequently-used
utilities so that callers can write a single short import line, e.g.::

    from mrbtp.utils import ROOT_PATH, get_root_path, parse_predicate_logic

Layout
------
``mrbtp.utils.path``                Project-root resolution.
``mrbtp.utils.random``              Seeded NumPy RNG wrapper (``Random``).
``mrbtp.utils.string_format``       Predicate-logic string parsing.
``mrbtp.utils.tools``               Coloured printing, action filtering,
                                     experiment summary helpers.
``mrbtp.utils.any_tree_node``       Generic n-ary tree node + traversals.
``mrbtp.utils.composite_action_tools``  Composite-action sub-tree planner
                                     (``CompositeActionPlanner``) — only
                                     needed by the composite-action
                                     experiments.
"""

from mrbtp.utils.path import ROOT_PATH, get_root_path
from mrbtp.utils.string_format import parse_predicate_logic

__all__ = [
    "ROOT_PATH",
    "get_root_path",
    "parse_predicate_logic",
]
