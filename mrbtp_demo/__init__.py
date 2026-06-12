"""mrbtp_demo — a small, readable, three-part walkthrough of MRBTP.

The package deliberately splits the original monolithic
``test_multi_minigrid_single_demo/main.py`` into three independent,
well-documented stages so the pipeline is easy to read and modify:

    1. planner.py   — Part 1: plan one behavior tree per agent from a goal.
    2. executor.py  — Part 2: run those behavior trees, with a switch for
                      whether agents SHARE the communication / belief space.
    3. visualize.py — Part 3: render the MiniGrid world live and print the
                      behavior-tree tick result every step.

``run.py`` wires the three stages together behind a small CLI.
"""
