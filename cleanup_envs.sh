#!/usr/bin/env bash
# =============================================================================
# cleanup_envs.sh — refactor & slim down mrbtp/envs + fix code-style issues
#
# Safe to run from inside the mrbtp-demo project root.  The script is
# IDEMPOTENT: running it twice is harmless (already-applied changes are
# detected and skipped).  A timestamped backup of every touched file is
# written to ./.cleanup_bak.<ts>/ before anything is modified.
#
# What it does
#   A) delete the dead `mrbtp/envs/gridenv/base/` directory (~1650 lines,
#      an obsolete self-drawn-grid implementation the runtime never imports)
#   B) delete 5 behaviour-tree nodes the planner never instantiates
#   C) tidy source: explicit imports (no `import *`), drop commented-out
#      dead-code blocks (incl. Chinese ones), fix the `BahaviorNode` typo,
#      and correct out-of-date package docstrings.  Valid explanatory
#      comments (Chinese or English) are KEPT on purpose.
#
# After running:  pip install -e .   (re-register the package in your venv)
# =============================================================================
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

if [[ ! -d "mrbtp/envs/gridenv/minigrid" ]]; then
  echo "[!] This does not look like the mrbtp-demo root (mrbtp/envs/gridenv/minigrid not found)." >&2
  echo "    Run the script from inside ~/mywork/mrbtp-demo/." >&2
  exit 1
fi

TS="$(date +%Y%m%d_%H%M%S)"
BAK=".cleanup_bak.$TS"
mkdir -p "$BAK"
echo "[*] Project root: $ROOT"
echo "[*] Backup dir  : $BAK"

backup() {  # backup a path (file or dir) preserving structure
  local p="$1"
  [[ -e "$p" ]] || return 0
  mkdir -p "$BAK/$(dirname "$p")"
  cp -R "$p" "$BAK/$p"
}

# --- A) delete dead gridenv/base ------------------------------------------
if [[ -d "mrbtp/envs/gridenv/base" ]]; then
  backup "mrbtp/envs/gridenv/base"
  rm -rf "mrbtp/envs/gridenv/base"
  echo "[A] removed mrbtp/envs/gridenv/base/"
else
  echo "[A] gridenv/base already gone — skip"
fi

# --- B) delete dead behaviour nodes ---------------------------------------
DEAD_NODES=(
  "mrbtp/envs/gridenv/minigrid/behavior_lib/FixAction/SelfDoTask.py"
  "mrbtp/envs/gridenv/minigrid/behavior_lib/FixAction/RandomAction.py"
  "mrbtp/envs/gridenv/minigrid/behavior_lib/FixCondition/CanSelfDoTask.py"
  "mrbtp/envs/gridenv/minigrid/behavior_lib/FixCondition/IsTaskAssigned.py"
  "mrbtp/envs/gridenv/minigrid/behavior_lib/FixCondition/IsTrue.py"
)
for f in "${DEAD_NODES[@]}"; do
  if [[ -f "$f" ]]; then backup "$f"; rm -f "$f"; echo "[B] removed $(basename "$f")"; fi
done

# --- C) source tidy via inline Python (utf-8 safe, exact block replace) ----
backup "mrbtp/envs/gridenv/minigrid/minigrid_env.py"
backup "mrbtp/__init__.py"
backup "mrbtp/envs/__init__.py"
backup "mrbtp/behavior_tree/base_nodes/Condition.py"
backup "mrbtp/envs/gridenv/minigrid/behavior_lib/FixAction/SelfAcceptTask.py"
backup "mrbtp/envs/gridenv/minigrid/magrid_env.py"
backup "mrbtp/envs/gridenv/minigrid/agent.py"

python3 - <<'PY'
import io, sys

def patch(path, repls):
    with io.open(path, encoding="utf-8") as f:
        s = f.read()
    for old, new, label in repls:
        if old in s:
            s = s.replace(old, new, 1)
            print(f"[C] {path}: {label}")
        elif new in s:
            print(f"[C] {path}: {label} (already applied)")
        else:
            print(f"[C][warn] {path}: pattern NOT found -> {label}", file=sys.stderr)
    with io.open(path, "w", encoding="utf-8") as f:
        f.write(s)

# ---- minigrid_env.py ----
ME = "mrbtp/envs/gridenv/minigrid/minigrid_env.py"
patch(ME, [
    (
        "import itertools\nfrom mrbtp.envs.gridenv.minigrid.magrid_env import MiniGridMAGridEnv",
        "import itertools\nimport numpy as np\nfrom mrbtp.envs.gridenv.minigrid.magrid_env import MiniGridMAGridEnv",
        "add explicit `import numpy as np`",
    ),
    (
        "from minigrid.core.mission import MissionSpace\nfrom minigrid.envs.babyai.core.verifier import *",
        "from minigrid.core.mission import MissionSpace\nfrom minigrid.minigrid_env import MiniGridEnv\nfrom minigrid.envs.babyai.core.verifier import GoToInstr, PickupInstr",
        "replace `import *` with explicit imports (MiniGridEnv, GoToInstr, PickupInstr)",
    ),
    (
        """        return can_goto, can_pickup, can_toggle


    # def get_action_lists(self,verbose=False,centralize=False):
    #
    #     self.get_objects_lists()
    #     self.doors_to_adj_rooms,self.adj_rooms_to_doors = self.get_adjacent_rooms_and_doors()
    #
    #     # obj cache
    #     can_goto, can_pickup, can_toggle = self.initialize_cache()
    #
    #     # generate action list for all Agents
    #     action_list = []
    #     for i in range(self.num_agent):
    #         if verbose: print("\\n" + "-"*10 + f" getting action list for agent_{i} " + "-"*10)
    #         action_list.append([])
    #         for cls in self.agents[i].behavior_lib["Action"].values():
    #             if cls.can_be_expanded:
    #                 agent_action_list = cls.get_planning_action_list(self.agents[i], self)
    #                 action_list[i] += agent_action_list
    #                 if verbose:print(f"action: {cls.__name__}, got {len(agent_action_list)} instances.")
    #
    #         if verbose:
    #             print(f"full action list ({len(action_list[i])} in total):")
    #             for a in action_list[i]:
    #                 print(a.name)
    #             # print(a.name,"pre:",a.pre)
    #
    #     if centralize:
    #         self.action_list = list(itertools.chain(*action_list)) #flattened_list
    #     else:
    #         self.action_list = action_list
    #
    #     # write it into blackboard
    #     for act_ls in action_list:
    #         for act in act_ls:
    #             self.blackboard["action_pre"][act.name] = frozenset(act.pre)
    #
    #     return action_list

    def get_initial_state(self):""",
        """        return can_goto, can_pickup, can_toggle

    def get_initial_state(self):""",
        "drop commented-out get_action_lists() block",
    ),
    (
        """            status = condition_node.update()
            if status == Status.FAILURE:
                start -= {state}
            # anytree_root.add_child(AnyTreeNode(NODE_TYPE.condition, cls_name, args))
            # btml = BTML()
            # btml.bt_root = anytree_root
            # bt = BehaviorTree(btml=btml, behavior_lib=behavior_lib)
            # # bt.tick()
            # self.agents[0].bind_bt(bt)
            # self.print_ticks = False
            # obs,done,_,_ = self.step(num_agent=1)
            # if bt.root.status == Status.FAILURE:
            #     start -= {state}
        # print(start)
        return start""",
        """            status = condition_node.update()
            if status == Status.FAILURE:
                start -= {state}
        return start""",
        "drop commented-out tail block in get_initial_state()",
    ),
    ("# \u68c0\u6d4b IsNear \u6a21\u5f0f", "# Detect IsNear() patterns", "translate Chinese comment (IsNear)"),
    ("# \u68c0\u6d4b IsHolding \u6a21\u5f0f", "# Detect IsHolding() patterns", "translate Chinese comment (IsHolding)"),
    ("# \u68c0\u6d4b IsHandEmpty \u6a21\u5f0f", "# Detect IsHandEmpty() patterns", "translate Chinese comment (IsHandEmpty)"),
    ("# \u68c0\u6d4b IsInRoom \u6a21\u5f0f", "# Detect IsInRoom() patterns", "translate Chinese comment (IsInRoom)"),
    ("# \u68c0\u67e5 IsOpen() \u548c IsClose() \u4e0d\u80fd\u9488\u5bf9\u540c\u4e00\u4e2a\u7269\u4f53\u90fd\u6709",
     "# IsOpen() and IsClose() must not both hold for the same object",
     "translate Chinese comment (IsOpen/IsClose rule)"),
    ("# \u68c0\u6d4b IsOpen \u548c IsClose \u6a21\u5f0f", "# Detect IsOpen() / IsClose() patterns", "translate Chinese comment (IsOpen/IsClose)"),
])

# ---- mrbtp/__init__.py docstring ----
patch("mrbtp/__init__.py", [
    (
        """Sub-packages
------------
``mrbtp.btp``           Multi-robot / multi-robot BT planners
                         (``DMR``, ``MABTP``, ``MAOBTP``, ``CABTP``).
``mrbtp.behavior_tree`` Behavior-tree runtime, ``BTML`` parser,
                         ``BehaviorLibrary``.
``mrbtp.envs``          Environments (MiniGrid, NumericalEnv, VirtualHome\u2026).
``mrbtp.llm_client``    Thin OpenAI-compatible LLM client + schemas.
``mrbtp.utils``         Generic helpers (paths, RNG, string parsing).
\"\"\"""",
        """Sub-packages
------------
``mrbtp.btp``           Multi-robot BT planners
                         (``MRBTP``, ``MABTP``, ``MAOBTP``).
``mrbtp.behavior_tree`` Behavior-tree runtime, ``BTML`` parser,
                         ``BehaviorLibrary``.
``mrbtp.envs``          Environments (MiniGrid multi-agent grid worlds).
``mrbtp.utils``         Generic helpers (paths, RNG, string parsing).
\"\"\"""",
        "fix stale top-level docstring (remove non-existent subpackages)",
    ),
])

# ---- mrbtp/envs/__init__.py docstring ----
patch("mrbtp/envs/__init__.py", [
    (
        """* ``mrbtp.envs.base``           \u2014 abstract base classes shared by every env.
* ``mrbtp.envs.gridenv``        \u2014 MiniGrid-based 2-D grid environments
                                   (sub-packages ``minigrid``, ``minigrid_computation_env``).
* ``mrbtp.envs.numerical_env``  \u2014 purely numeric / symbolic simulator used
                                   for benchmarking the planner without a
                                   physics engine.
* ``mrbtp.envs.virtualhome``    \u2014 VirtualHome adapter (3-D household scenes).

Naming convention
-----------------

All sub-packages use ``snake_case`` lowercase identifiers.  Compact compound
words such as ``gridenv`` and ``virtualhome`` are kept without an underscore
because they are well-established short forms across the codebase.  Longer
names (``numerical_env``, ``minigrid_computation_env``) keep the underscore
to remain readable.  For backward compatibility the historical import paths
are preserved verbatim and **must not** be renamed without a deprecation
shim \u2014 they are referenced by 100+ external experiment scripts.""",
        """* ``mrbtp.envs.base``     \u2014 abstract base classes (``Env``, ``Agent``) shared
                             by every concrete environment.
* ``mrbtp.envs.gridenv``  \u2014 MiniGrid-based 2-D multi-agent grid worlds.  The
                             only concrete implementation in this demo lives
                             in ``mrbtp.envs.gridenv.minigrid``.

Naming convention
-----------------

Sub-packages use ``snake_case`` lowercase identifiers.  Compact compound
words such as ``gridenv`` are kept without an underscore because they are
well-established short forms across the codebase.""",
        "fix stale envs docstring (remove non-existent subpackages)",
    ),
])

# ---- truncate files whose tail is a commented-out dead-code block --------
# Each entry: (path, anchor_substring).  Everything AFTER the line that
# contains `anchor_substring` is deleted IFF every remaining non-blank line
# is a comment (`#...`).  This guards against accidentally cutting live code.
def truncate_after(path, anchor):
    try:
        with io.open(path, encoding="utf-8") as f:
            lines = f.readlines()
    except FileNotFoundError:
        print(f"[C][warn] {path}: not found -> skip truncate", file=sys.stderr)
        return
    idx = next((i for i, l in enumerate(lines) if anchor in l), None)
    if idx is None:
        print(f"[C][warn] {path}: anchor not found -> {anchor!r}", file=sys.stderr)
        return
    tail = lines[idx + 1:]
    nonblank = [l for l in tail if l.strip()]
    if not nonblank:
        print(f"[C] {path}: already truncated (no dead block) — skip")
        return
    if not all(l.lstrip().startswith("#") for l in nonblank):
        print(f"[C][warn] {path}: tail after anchor is NOT all-comment -> skip (safety)", file=sys.stderr)
        return
    keep = lines[:idx + 1]
    if keep and not keep[-1].endswith("\n"):
        keep[-1] += "\n"
    with io.open(path, "w", encoding="utf-8") as f:
        f.writelines(keep)
    print(f"[C] {path}: dropped {len(tail)} trailing dead-code lines")

truncate_after("mrbtp/behavior_tree/base_nodes/Condition.py", "return False, False")
truncate_after("mrbtp/envs/gridenv/minigrid/behavior_lib/FixAction/SelfAcceptTask.py", "        return Status.RUNNING\n")

# ---- delete a mid-file commented-out dead-code block (magrid_env.py) -----
# The reset() method carried ~44 lines of commented-out hardcoded agent
# positions/directions between the rand-placement loop and the
# "# Item picked up" comment.  Drop them, keep the valid comment.
def delete_block_between(path, start_anchor, end_anchor):
    try:
        with io.open(path, encoding="utf-8") as f:
            lines = f.readlines()
    except FileNotFoundError:
        print(f"[C][warn] {path}: not found -> skip block delete", file=sys.stderr)
        return
    si = next((i for i, l in enumerate(lines) if start_anchor in l), None)
    ei = next((i for i, l in enumerate(lines) if end_anchor in l), None)
    if si is None or ei is None or ei <= si:
        print(f"[C][warn] {path}: block anchors not found/ordered -> skip", file=sys.stderr)
        return
    middle = lines[si + 1:ei]
    nonblank = [l for l in middle if l.strip()]
    if not nonblank:
        print(f"[C] {path}: block already removed — skip")
        return
    if not all(l.lstrip().startswith("#") for l in nonblank):
        print(f"[C][warn] {path}: block is NOT all-comment -> skip (safety)", file=sys.stderr)
        return
    new = lines[:si + 1] + ["\n"] + lines[ei:]
    with io.open(path, "w", encoding="utf-8") as f:
        f.writelines(new)
    print(f"[C] {path}: dropped {len(middle)} commented-out lines (hardcoded agent positions)")

delete_block_between(
    "mrbtp/envs/gridenv/minigrid/magrid_env.py",
    "agent.direction = self._rand_int(0, 4)",
    "# Item picked up, being carried, initially nothing",
)

# ---- drop a single commented-out dead line in agent.py -------------------
patch("mrbtp/envs/gridenv/minigrid/agent.py", [
    (
        '            try:\n                # self.env.blackboard["task_agents_queue"].remove(self)  # \u76f4\u63a5\u79fb\u9664\u5bf9\u8c61\n                index = self.env.blackboard["task_agents_queue"].index(self)',
        '            try:\n                index = self.env.blackboard["task_agents_queue"].index(self)',
        "drop commented-out remove(self) dead line",
    ),
])
PY

# --- fix BahaviorNode typo across the package (skip .venv / backups) -------
TYPO_FILES=$(grep -rl "BahaviorNode" mrbtp --include="*.py" 2>/dev/null || true)
if [[ -n "$TYPO_FILES" ]]; then
  while IFS= read -r f; do backup "$f"; sed -i '' 's/BahaviorNode/BehaviorNode/g' "$f" 2>/dev/null \
      || sed -i 's/BahaviorNode/BehaviorNode/g' "$f"; echo "[C] fixed typo BahaviorNode->BehaviorNode in $f"; done <<< "$TYPO_FILES"
else
  echo "[C] no BahaviorNode typo found (already fixed) — skip"
fi

# --- verify ----------------------------------------------------------------
echo ""
echo "[*] Verification:"
LEFT_BASE=$([[ -d "mrbtp/envs/gridenv/base" ]] && echo "EXISTS" || echo "removed")
echo "    gridenv/base ............ $LEFT_BASE   (expected: removed)"
TYPO_LEFT=$( { grep -rl "BahaviorNode" mrbtp --include="*.py" 2>/dev/null || true; } | wc -l | tr -d ' ')
echo "    BahaviorNode typo files . $TYPO_LEFT          (expected: 0)"
STAR_LEFT=$( { grep -rn "babyai.core.verifier import \*" mrbtp --include="*.py" 2>/dev/null || true; } | wc -l | tr -d ' ')
echo "    'import *' from verifier  $STAR_LEFT          (expected: 0)"
# Valid Chinese explanatory comments are intentionally kept; we only ensure
# the commented-out Chinese dead-code blocks were removed.
DEADCN=$(python3 -c "import io,re,sys
n=0
for p in ['mrbtp/behavior_tree/base_nodes/Condition.py',
          'mrbtp/envs/gridenv/minigrid/behavior_lib/FixAction/SelfAcceptTask.py',
          'mrbtp/envs/gridenv/minigrid/magrid_env.py']:
    try: t=io.open(p,encoding='utf-8').read()
    except FileNotFoundError: continue
    # dead-code signatures: commented assignment / commented return / commented direction
    n+=len(re.findall(r'#\s*self\.agents\[\d+\]\.', t))
    n+=len(re.findall(r'#\s*return Status\.RUNNING', t))
    n+=len(re.findall(r'#\s*anytree_root', t))
print(n)")
echo "    commented-out dead-code .. $DEADCN          (expected: 0)"
echo "    algorithm classes intact:"
grep -rn "class MABTP\b\|class MAOBTP\b\|class MRBTP\b" --include="*.py" mrbtp/btp 2>/dev/null | sed 's/^/        /' || true

echo ""
if [[ "$LEFT_BASE" == "removed" && "$TYPO_LEFT" == "0" && "$STAR_LEFT" == "0" && "$DEADCN" == "0" ]]; then
  echo "[OK] Refactor complete.  Backup kept in: $BAK"
  echo ""
  echo "     Re-register the package in your venv, then self-check:"
  echo "       source .venv/bin/activate"
  echo "       pip install -e ."
  echo "       python -m mrbtp_demo.verify --seed 6 --attempts 5"
  echo ""
  echo "     Once you have confirmed everything works, delete the backup:"
  echo "       rm -rf $BAK"
else
  echo "[!] Something looks off — inspect the lines above. Backup is in $BAK" >&2
  exit 1
fi
