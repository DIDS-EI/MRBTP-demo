"""Domain behavior-library registry.

A *domain* bundles a scene-specific behavior library — a folder of
``Condition/`` and ``Action/`` node classes — that the planner expands and
the executor ticks.  Historically the only library lived under
``core/envs/gridenv/minigrid/behavior_lib`` and its path was hard-coded inside
``minigrid_env.py``.  That made it impossible for the *home-service* and
*battlefield* scenes to plan with their own predicates and actions.

This package fixes that by turning "which behavior library" into a first-class,
pluggable choice:

    * Each domain owns a directory ``core/envs/domains/<domain>/behavior_lib``
      with the same loader contract as the MiniGrid library (one node class
      per ``*.py`` file, subclassing ``Action`` / ``Condition``; the
      :class:`~core.behavior_tree.behavior_library.BehaviorLibrary` walks every
      sub-folder and registers the classes).
    * A domain library may freely ``import`` the shared MiniGrid primitives
      (``GoToInRoom``, ``PickUp``, ``IsInRoom`` …) and only add the handful of
      *domain-specific* nodes on top — so we never duplicate the grid logic.

A :class:`~app.scenario.Scenario` selects a library through its
``behavior_lib`` field, which may be:

    * ``None``                 -> the built-in MiniGrid library (default; the
                                  historical behaviour, byte-for-byte).
    * a registered domain name -> e.g. ``"home_service"`` / ``"battlefield"``.
    * an absolute filesystem path -> used verbatim (escape hatch for ad-hoc
      libraries living outside this tree).

:func:`resolve_behavior_lib_path` performs that mapping.  Adding a new domain
is therefore: drop a ``behavior_lib`` folder under ``core/envs/domains/<name>``
and register it in :data:`DOMAIN_REGISTRY` below.
"""

from __future__ import annotations

import os
from typing import Dict, List, Optional, Union

# A resolved behavior-library selector: either a single root path (the built-in
# MiniGrid library) or an ordered overlay ``[base_root, domain_root]`` that the
# loader merges (domain nodes override / extend the shared grid primitives).
BehaviorLibPath = Union[str, List[str]]


def _domains_root() -> str:
    """Absolute path of this ``core/envs/domains`` package directory."""
    return os.path.dirname(os.path.abspath(__file__))


def _domain_behavior_lib(domain: str) -> str:
    """``core/envs/domains/<domain>/behavior_lib`` as an absolute path."""
    return os.path.join(_domains_root(), domain, "behavior_lib")


# Registered domains.  The value is the *relative* domain folder name; the
# behavior library is always ``<domain>/behavior_lib`` underneath it.  Keep
# this list in sync with the sub-folders that ship a behavior library.
DOMAIN_REGISTRY: Dict[str, str] = {
    "home_service": "home_service",
    "battlefield": "battlefield",
    "virtualhome": "virtualhome",
}

#: 自包含的**非网格**域：它们不复用 MiniGrid 原语，因此解析成单一行为库路径
#: 而不是 ``[minigrid_root, domain_root]`` 的 overlay。当前只有 VirtualHome
#: 纯符号域（配套 ``backends/virtualhome``，不能配 ``--backend minigrid``）。
STANDALONE_DOMAINS = frozenset({"virtualhome"})


def minigrid_behavior_lib_path() -> str:
    """Absolute path of the built-in MiniGrid behavior library (the default).

    Kept here (rather than importing the env module) so this registry has no
    dependency on the heavy MiniGrid env import chain.
    """
    from core.utils import get_root_path

    return os.path.join(
        get_root_path(), "envs", "gridenv", "minigrid", "behavior_lib"
    )


def resolve_behavior_lib_path(behavior_lib: Optional[str]) -> BehaviorLibPath:
    """Resolve a scenario's ``behavior_lib`` selector to loadable path(s).

    Args:
        behavior_lib:
            * ``None``  -> the built-in MiniGrid library (historical default).
            * a registered domain name (key of :data:`DOMAIN_REGISTRY`).
            * an absolute filesystem path -> used verbatim.

        Returns:
            Either a single absolute path (the MiniGrid default / an absolute
            override / a standalone domain) or an **overlay list**
            ``[minigrid_root, domain_root]`` for a grid domain.  The overlay lets
            a domain reuse every shared grid primitive and only ship the handful
            of nodes it adds or overrides — the
            :class:`~core.behavior_tree.behavior_library.BehaviorLibrary` loader
            merges the list in order.  Domains listed in
            :data:`STANDALONE_DOMAINS` ship a complete library of their own.


    Raises:
        ValueError: if a non-path string is given that is not a registered
            domain — failing loudly beats silently planning with the wrong
            (or empty) library.
    """
    if behavior_lib is None:
        return minigrid_behavior_lib_path()

    # Absolute path escape hatch: use it as-is (single root, no overlay).
    if os.path.isabs(behavior_lib):
        return behavior_lib

    # Standalone domain -> its own complete library (no grid primitives).
    if behavior_lib in STANDALONE_DOMAINS:
        return _domain_behavior_lib(DOMAIN_REGISTRY[behavior_lib])

    # Registered grid domain -> overlay on top of the shared grid primitives.
    if behavior_lib in DOMAIN_REGISTRY:
        return [
            minigrid_behavior_lib_path(),
            _domain_behavior_lib(DOMAIN_REGISTRY[behavior_lib]),
        ]

    raise ValueError(
        f"Unknown behavior_lib selector {behavior_lib!r}. "
        f"Expected None, an absolute path, or one of the registered domains: "
        f"{sorted(DOMAIN_REGISTRY)}."
    )
