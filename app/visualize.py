"""Part 3 — Visualize execution: MiniGrid window + behavior-tree tick result.

This module provides a small :class:`Visualizer` whose ``on_step`` method is
handed to :func:`app.executor.execute`.  Every simulation step it:

    1. renders the MiniGrid world (a pygame window, when enabled), and
    2. prints the behavior-tree *tick result* for every agent — i.e. which
       condition / action nodes returned SUCCESS / RUNNING / FAILURE this
       step, plus the primitive action each agent took.

The tick result is exactly the per-node status that the original demo dumped
via ``env.print_ticks``; here it is captured through each behavior tree's
``StatusVisitor`` (``bt.visitor.output_str``) so we control the formatting.
"""

from __future__ import annotations

import time
from typing import Optional

from core.utils.tools import print_colored

from app.executor import StepRecord


# ANSI colours per BT status, for the printed tick result.
_STATUS_COLOUR = {
    "SUCCESS": "green",
    "RUNNING": "blue",
    "FAILURE": "red",
    "INVALID": "yellow",
}


class Visualizer:
    """Render the world and print behavior-tree ticks during execution."""

    def __init__(
        self,
        render: bool = True,
        print_tree: bool = True,
        fps: float = 10.0,
    ):
        """
        Args:
            render: open/refresh the MiniGrid pygame window each step.
            print_tree: print the per-node behavior-tree tick result.
            fps: cap on rendering speed (frames per second).
        """
        self.render = render
        self.print_tree = print_tree
        self.min_dt = 1.0 / fps if fps > 0 else 0.0
        self._last_frame = 0.0

    # The signature matches ``StepCallback`` in executor.py.
    def on_step(self, record: StepRecord, env) -> None:
        if self.print_tree:
            self._print_tick_result(record)
        if self.render:
            self._render(env)

    # ------------------------------------------------------------------ #
    # Rendering
    # ------------------------------------------------------------------ #

    def _render(self, env) -> None:
        # Throttle to the requested FPS so fast runs stay watchable.
        now = time.time()
        if now - self._last_frame < self.min_dt:
            time.sleep(max(0.0, self.min_dt - (now - self._last_frame)))
        self._last_frame = time.time()

        env.render_mode = "human"
        env.render()

    def hold_open(self, env) -> None:
        """Keep the window open after the task finishes (until closed)."""
        if not self.render:
            return
        print_colored("Task done — close the window to exit.", "green")
        try:
            while True:
                env.render_mode = "human"
                env.render()
                time.sleep(self.min_dt or 0.05)
        except KeyboardInterrupt:
            pass

    # ------------------------------------------------------------------ #
    # Behavior-tree tick printout
    # ------------------------------------------------------------------ #

    def _print_tick_result(self, record: StepRecord) -> None:
        print_colored(
            f"\n========== STEP {record.step}"
            f"{'  [DONE]' if record.done else ''} ==========",
            "blue",
        )
        for tick in record.ticks:
            head_colour = _STATUS_COLOUR.get(tick.bt_status, "yellow")
            print_colored(
                f"-- agent-{tick.agent_id} | primitive action: "
                f"{tick.action_name} | BT root: {tick.bt_status}",
                head_colour,
            )
            # The visitor output is one line per leaf node ("name: STATUS").
            for line in tick.tick_output.splitlines():
                self._print_node_line(line)

    @staticmethod
    def _print_node_line(line: str) -> None:
        line = line.rstrip()
        if not line:
            return
        if "SUCCESS" in line:
            print_colored(f"     {line}", "green")
        elif "RUNNING" in line:
            print_colored(f"     {line}", "blue")
        elif "FAILURE" in line:
            print_colored(f"     {line}", "red")
        else:
            print(f"     {line}")
