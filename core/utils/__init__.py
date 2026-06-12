"""Generic, environment-agnostic helpers used across :mod:`core`.

This module deliberately re-exports a handful of small, frequently-used
utilities so that callers can write a single short import line, e.g.::

    from core.utils import ROOT_PATH, get_root_path, parse_predicate_logic

Layout
------
``core.utils.path``                Project-root resolution.
``core.utils.random``              Seeded NumPy RNG wrapper (``Random``).
``core.utils.string_format``       Predicate-logic string parsing.
``core.utils.tools``               Coloured printing, action filtering,
                                     experiment summary helpers.
``core.utils.any_tree_node``       Generic n-ary tree node + traversals.
``core.utils.composite_action_tools``  Composite-action sub-tree planner
                                     (``CompositeActionPlanner``) — only
                                     needed by the composite-action
                                     experiments.
"""

from core.utils.path import ROOT_PATH, get_root_path
from core.utils.string_format import parse_predicate_logic

__all__ = [
    "ROOT_PATH",
    "get_root_path",
    "parse_predicate_logic",
]
