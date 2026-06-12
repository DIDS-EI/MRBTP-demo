#!/usr/bin/env bash
# =============================================================================
#  P0 重构脚本 · 可插拔仿真后端（mrbtp-demo）
# =============================================================================
#  设计文档：docs/PLUGGABLE_BACKEND_DESIGN.html  （§9 实施路线 P0）
#
#  这个脚本做什么
#  --------------
#  P0 的目标是「让抽象成立、MiniGrid 平等归位」，且证明旧 demo 行为不变。
#  脚本按风险从低到高分成 4 段，每段都有独立产出、可单独跑、可回滚：
#
#    [段0] 安全网    : tar 全量备份 + git init 首次提交（没有 git 就建一个）
#    [段1] 基准      : 用现成的 verify.py 跑通现有 demo，存一份回归基准
#    [段2] 抽象骨架  : 新建 core/interfaces.py（两个协议）+ backends/scenes/themes
#                      骨架目录与 README —— 纯新增，不碰任何现有代码，零风险
#    [段3] 改名归位  : （高风险，需显式 --with-rename）把 mrbtp/ 物理改名为
#                      core/，批量改 237 处 import，再跑 verify.py 回归；
#                      回归失败则 git 自动回滚到段0 的提交。
#
#  为什么默认不做段3
#  -----------------
#  `mrbtp` 改名牵动 237 处 import，是 P0 里唯一的高风险动作。默认只跑
#  段0–段2（全部零风险），让你先看到「安全网 + 基准 + 抽象骨架」落地、
#  确认无误后，再用 --with-rename 触发改名，且改名全程 git 兜底。
#
#  用法
#  ----
#    bash scripts/p0_refactor.sh                  # 段0–段2（默认，安全）
#    bash scripts/p0_refactor.sh --with-rename    # 段0–段3（含 mrbtp→core 改名）
#    bash scripts/p0_refactor.sh --baseline-only  # 只跑段0+段1（仅备份+基准）
#    bash scripts/p0_refactor.sh --dry-run        # 只打印将要做什么，不动文件
#
#  环境
#  ----
#  在 repo 根目录（含 pyproject.toml 的那层）执行；需要项目 .venv。
# =============================================================================

set -euo pipefail

# ---- 0. 前置检查与参数 ------------------------------------------------------
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

WITH_RENAME=0
BASELINE_ONLY=0
DRY_RUN=0
for arg in "$@"; do
  case "$arg" in
    --with-rename)   WITH_RENAME=1 ;;
    --baseline-only) BASELINE_ONLY=1 ;;
    --dry-run)       DRY_RUN=1 ;;
    *) echo "未知参数: $arg"; exit 2 ;;
  esac
done

PY=".venv/bin/python"
TS="$(date +%Y%m%d_%H%M%S)"
BACKUP_DIR=".p0_backups"
BASELINE_DIR=".p0_baseline"

c() { printf '\033[%sm%s\033[0m\n' "$1" "$2"; }   # 上色
hr() { printf '%s\n' "────────────────────────────────────────────────────────"; }
step() { hr; c "1;36" "▶ $1"; hr; }
ok()   { c "1;32" "  ✓ $1"; }
warn() { c "1;33" "  ! $1"; }
die()  { c "1;31" "  ✗ $1"; exit 1; }
run()  { if [ "$DRY_RUN" = 1 ]; then c "0;90" "  [dry-run] $*"; else eval "$@"; fi; }

[ -f pyproject.toml ] || die "未在 repo 根目录（找不到 pyproject.toml）"
[ -d mrbtp ] || die "找不到 mrbtp/ 包"
[ -x "$PY" ] || die "找不到项目 venv：${PY}（先 python -m venv .venv && pip install -e .）"

c "1;37" "P0 重构 · 起点检查通过"
echo "  repo      : $REPO_ROOT"
echo "  python    : $PY"
echo "  with-rename : $([ $WITH_RENAME = 1 ] && echo 是 || echo 否（默认安全段）)"
echo "  dry-run     : $([ $DRY_RUN = 1 ] && echo 是 || echo 否)"
echo

# =============================================================================
#  段0 · 安全网：tar 备份 + git 首次提交
# =============================================================================
step "段0 · 安全网（备份 + git 兜底）"

run "mkdir -p '$BACKUP_DIR'"
BACKUP_TAR="$BACKUP_DIR/pre_p0_$TS.tar.gz"
# 备份源码，排除大/无关目录
run "tar --exclude='./.venv' --exclude='./.git' --exclude='./$BACKUP_DIR' \
        --exclude='*/__pycache__' --exclude='*.egg-info' \
        -czf '$BACKUP_TAR' ."
ok "全量备份 → $BACKUP_TAR"

if [ ! -d .git ]; then
  warn "当前不是 git 仓库 —— 初始化一个，作为可回滚的安全网"
  run "git init -q"
  # 最小 .gitignore，避免把 venv/缓存/备份纳入版本管理
  if [ ! -f .gitignore ]; then
    run "printf '%s\n' '.venv/' '__pycache__/' '*.egg-info/' '$BACKUP_DIR/' '$BASELINE_DIR/' 'mrbtp_demo/output/' > .gitignore"
    ok "已生成 .gitignore"
  fi
  run "git add -A"
  run "git commit -q -m 'chore(p0): snapshot before pluggable-backend refactor' --no-verify || true"
  ok "git 首次提交完成（P0 基线）"
else
  ok "已是 git 仓库"
  if [ -n "$(git status --porcelain 2>/dev/null)" ]; then
    run "git add -A"
    run "git commit -q -m 'chore(p0): snapshot before refactor ($TS)' --no-verify || true"
    ok "已提交当前改动作为 P0 基线"
  else
    ok "工作区干净，当前 HEAD 即 P0 基线"
  fi
fi
P0_BASE_COMMIT="$([ "$DRY_RUN" = 1 ] && echo '<dry-run>' || git rev-parse --short HEAD 2>/dev/null || echo '<none>')"
ok "P0 基线提交：$P0_BASE_COMMIT"
echo

# =============================================================================
#  段1 · 基准：跑通现有 demo，存回归基准
# =============================================================================
step "段1 · 回归基准（现有 demo 必须能跑通）"

run "mkdir -p '$BASELINE_DIR'"
BASE_LOG="$BASELINE_DIR/verify_baseline_$TS.log"
c "0;37" "  跑 verify.py（自带多次重试，对付 planner 固有 flaky）..."
if [ "$DRY_RUN" = 1 ]; then
  c "0;90" "  [dry-run] PYTHONPATH=. $PY -m mrbtp_demo.verify --both --attempts 6 2>&1 | tee $BASE_LOG"
  BASELINE_OK=1
else
  set +e
  PYTHONPATH=. "$PY" -m mrbtp_demo.verify --both --attempts 6 2>&1 | tee "$BASE_LOG"
  BASELINE_RC=${PIPESTATUS[0]}
  set -e
  if [ "$BASELINE_RC" = 0 ]; then
    BASELINE_OK=1
    ok "基准通过 → 日志 $BASE_LOG"
    grep -E "RESULT|SUMMARY|PASSED" "$BASE_LOG" | sed 's/^/    /' || true
  else
    BASELINE_OK=0
    die "现有 demo 基准就没跑通（rc=${BASELINE_RC}）。先修好现状再谈重构，已停在段1。"
  fi
fi
echo

if [ "$BASELINE_ONLY" = 1 ]; then
  c "1;32" "✓ --baseline-only：已完成段0+段1（备份 + 基准）。"
  echo "  备份 : $BACKUP_TAR"
  echo "  基准 : $BASE_LOG"
  exit 0
fi

# =============================================================================
#  段2 · 抽象骨架：新建协议 + 目录骨架（纯新增，零风险）
# =============================================================================
step "段2 · 抽象骨架（core/interfaces.py + backends/scenes/themes 骨架）"
c "0;37" "  纯新增文件，不碰任何现有代码 —— 即使全删也不影响现有 demo。"

# --- core/interfaces.py：两个协议（SimBackend / Renderer）------------------
# 注意：此刻包仍叫 mrbtp/。协议文件先放进 mrbtp/，改名段会随之带到 core/。
mk_interfaces() {
  cat > mrbtp/interfaces.py <<'PYEOF'
"""可插拔仿真后端 —— 两个核心协议（契约定义处）。

设计文档：docs/PLUGGABLE_BACKEND_DESIGN.html  §3 核心架构 / §4 接口契约

这里只定义「形状」，不含任何实现。后端（backends/<name>/）实现 SimBackend，
渲染器实现 Renderer，两者正交组合。规划器 / executor 只依赖这两个协议，
看不到具体后端是 MiniGrid 还是 Pygame。

Python 3.9 兼容：用 typing.Protocol（runtime_checkable 便于 isinstance 自检）。
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Protocol, Tuple, runtime_checkable


# ───────────────────────── 缝① 仿真后端 ──────────────────────────
@runtime_checkable
class SimBackend(Protocol):
    """一个「世界」该长什么样 —— 规划器 / executor 依赖的最小接口。

    现有 MiniGrid env 已经隐式满足其中大部分；P0 的工作是把它显式对齐到
    这个协议（见 backends/minigrid/）。新后端（Pygame…）照此实现即可。
    """

    # --- A 组：世界与智能体 ---
    agents: List[Any]                      # 每个 agent 暴露 B 组接口

    def reset(self, *, seed: Optional[int] = None) -> Any:
        """重置世界到初始状态，返回观测（具体类型由后端定义）。"""
        ...

    def get_initial_state(self) -> set:
        """返回初始谓词集合（如 {IsInRoom(ball,room-0), ...}）供规划器用。"""
        ...

    def create_action_model(self) -> Any:
        """构造该后端的动作模型（可用动作 / 前后条件），供规划器展开。"""
        ...

    # --- C 组：空间查询（谓词求值依赖）---
    def get_room_index(self, pos: Tuple[int, int]) -> int:
        """给定坐标，返回它所属的房间编号（IsInRoom 等谓词依赖）。"""
        ...

    @property
    def width(self) -> int: ...
    @property
    def height(self) -> int: ...


@runtime_checkable
class SimAgent(Protocol):
    """单个智能体的最小接口（SimBackend.agents 里的元素）。"""

    id: int

    @property
    def position(self) -> Tuple[int, int]: ...
    @property
    def front_pos(self) -> Tuple[int, int]: ...

    def step(self, action: Any) -> None:
        """执行一个离散原语动作（left/right/forward/pickup/drop/toggle/done）。"""
        ...


# ───────────────────────── 缝② 渲染器 ──────────────────────────
@runtime_checkable
class Renderer(Protocol):
    """怎么把一个世界「画出来」—— 与后端正交，可单独替换。

    渲染唯一入口经 executor 的 on_step 回调外置（executor 自身从不调渲染），
    所以换渲染 = 换 on_step 里调的对象，不动规划与执行逻辑。
    """

    def render(self, backend: SimBackend) -> Any:
        """把当前世界状态渲染出来（窗口 / 存帧 / headless 由 mode 决定）。"""
        ...

    def close(self) -> None:
        """收尾（关闭窗口、合成 GIF、释放资源等）。"""
        ...


# ───────────────────────── 工厂（占位，P1 实现）──────────────────────────
def make_backend(name: str, *, scene: Any) -> "SimBackend":   # noqa: D401
    """按名字造后端（'minigrid' / 'pygame' / ...）。P1 填实现。"""
    raise NotImplementedError(
        "make_backend 将在 P1 实现；P0 只定义协议契约。"
    )


def make_renderer(name: str, *, theme: str = "default",
                  mode: str = "save_gif") -> "Renderer":      # noqa: D401
    """按名字造渲染器，正交组合（远程默认 save_gif）。P2 填实现。"""
    raise NotImplementedError(
        "make_renderer 将在 P2 实现；P0 只定义协议契约。"
    )
PYEOF
}

# --- 骨架目录 + README（每目录一句话，回答「这里干什么」）----------------
mk_dir_readme() {
  local dir="$1"; local body="$2"
  mkdir -p "$dir"
  if [ ! -f "$dir/README.md" ]; then
    printf '%s\n' "$body" > "$dir/README.md"
  fi
}

if [ "$DRY_RUN" = 1 ]; then
  c "0;90" "  [dry-run] 写 mrbtp/interfaces.py（SimBackend / Renderer 协议）"
  c "0;90" "  [dry-run] 建 backends/ scenes/ themes/ 骨架 + 各自 README.md"
else
  mk_interfaces
  ok "写入 mrbtp/interfaces.py（两个协议，改名段会带到 core/interfaces.py）"

  mk_dir_readme "backends" \
"# backends/ — 仿真后端（每个一个文件夹，自包含「逻辑+渲染+物体」）

想加新仿真器？**复制一个文件夹照着改**，实现 \`core/interfaces.py\` 的
\`SimBackend\`（+ 配套 \`Renderer\`）即可。规划器 / executor 不认具体后端。

- \`minigrid/\` — 现有 MiniGrid，P0 归位到这里（一等后端，与 pygame 平等）
- \`pygame/\`   — 全新 pygame 后端（P1 起逐步填充）

> 设计文档：docs/PLUGGABLE_BACKEND_DESIGN.html §4 接口契约 / §8 目录结构"
  mk_dir_readme "backends/minigrid" \
"# backends/minigrid/ — MiniGrid 后端（占位骨架，P0/P1 归位）

P0 第二步把现有 \`mrbtp/envs/gridenv/minigrid/\` 的 env 对齐到 SimBackend
协议后归位到这里。**当前为占位**，归位前现有 demo 仍走 mrbtp 原路径。"
  mk_dir_readme "backends/pygame" \
"# backends/pygame/ — 全新 Pygame 后端（P1 起实现）

逻辑 + 画面都在这一个文件夹：env.py / grid.py / objects.py / agent.py /
physics.py / render.py。改物体看 objects.py，改画面看 render.py。"

  mk_dir_readme "scenes" \
"# scenes/ — 场景（纯数据声明，想加场景只看这里）

一个场景 = 房间布局 + 物体清单 + 任务目标（用现有谓词 IsInRoom / IsNear 拼）。
**加新场景 = 只动这里一个文件**，照现成的抄。详见设计文档 §8「加新场景 5 步」。

- \`home_service.py\` — 家庭服务（P3）
- \`battlefield.py\`  — 战场（P3）"
  mk_dir_readme "themes" \
"# themes/ — 渲染主题（配色 / 图标，想让画面好看只看这里）

只影响渲染，与规划逻辑无关。home.py 暖色家居 / battle.py 冷色军事。"

  ok "建 backends/ scenes/ themes/ 骨架 + 各自 README"
fi
echo

if [ "$WITH_RENAME" != 1 ]; then
  hr
  c "1;32" "✓ 默认安全段完成（段0–段2）"
  hr
  echo "  已落地："
  echo "    • 备份      : $BACKUP_TAR"
  echo "    • git 基线  : $P0_BASE_COMMIT"
  echo "    • 回归基准  : $BASE_LOG"
  echo "    • 协议契约  : mrbtp/interfaces.py"
  echo "    • 骨架目录  : backends/ scenes/ themes/（含 README）"
  echo
  c "1;37" "下一步（高风险，需你确认后再跑）："
  echo "  把 mrbtp/ 物理改名为 core/ 并批量改 237 处 import + 回归校验："
  echo
  c "1;33" "    bash scripts/p0_refactor.sh --with-rename"
  echo
  echo "  改名全程有 git 兜底：回归失败会自动回滚到基线 ${P0_BASE_COMMIT}。"
  exit 0
fi

# =============================================================================
#  段3 · 改名归位（高风险）：mrbtp/ → core/，批量改 import，回归校验
# =============================================================================
step "段3 · 改名归位 mrbtp/ → core/（高风险，git 兜底）"
warn "将物理改名 mrbtp/ → core/ 并批量修改 237 处 import。回归失败自动回滚。"

# 关键安全点：'mrbtp' 是 'mrbtp_demo' 的前缀。用 perl 词边界 \bmrbtp\b 匹配，
# 'mrbtp_demo' 中 mrbtp 右侧是下划线(单词字符)，不构成词边界，天然不被误伤。
RENAME_FILES() {
  # 在所有 .py 中把独立单词 mrbtp 替换为 core（不碰 mrbtp_demo）
  # 同时修正硬编码路径字符串 'mrbtp/behavior_tree/...' / "mrbtp.behavior_tree"
  find . -type f -name '*.py' \
    -not -path './.venv/*' -not -path './.git/*' \
    -not -path '*/__pycache__/*' -not -path './'"$BACKUP_DIR"'/*' -print0 \
  | xargs -0 perl -0777 -i -pe '
      s/\bmrbtp\b/core/g;                       # import / from / 包名
  '
  # pyproject.toml 的 include 与 package-data 等
  perl -0777 -i -pe 's/\bmrbtp\b/core/g' pyproject.toml
}

if [ "$DRY_RUN" = 1 ]; then
  c "0;90" "  [dry-run] git mv mrbtp core"
  c "0;90" "  [dry-run] perl -i 's/\\bmrbtp\\b/core/g' 所有 .py + pyproject.toml"
  c "0;90" "  [dry-run] 重装包: $PY -m pip install -e . -q"
  c "0;90" "  [dry-run] 回归: verify.py --both --attempts 6；失败则 git reset --hard $P0_BASE_COMMIT"
  c "1;32" "✓ dry-run 结束（未改动任何文件）"
  exit 0
fi

# 1) 物理改名目录（用 git mv 保留历史）
if [ -d core ]; then
  die "core/ 已存在，疑似改名已执行过。请先确认状态（git log / ls core）。"
fi
git mv mrbtp core
ok "git mv mrbtp → core"

# 2) 批量改 import / 包名 / 硬编码路径字符串
RENAME_FILES
ok "批量替换 \\bmrbtp\\b → core（词边界保护 mrbtp_demo 不受影响）"

# 3) 重装可编辑包（包名变了，刷新 egg-info / 入口点）
rm -rf mrbtp_demo.egg-info core.egg-info 2>/dev/null || true
"$PY" -m pip install -e . -q
ok "重装可编辑包（pip install -e .）"

# 4) 静态自检：确保没有残留的独立 mrbtp 引用
RESIDUAL="$(grep -rnE '\bmrbtp\b' --include='*.py' . \
  | grep -v '__pycache__' | grep -v '\.venv/' | grep -v 'mrbtp_demo' || true)"
if [ -n "$RESIDUAL" ]; then
  warn "发现残留的独立 'mrbtp' 引用（非 mrbtp_demo）："
  echo "$RESIDUAL" | sed 's/^/    /' | head -30
  warn "这些可能是注释或文档串；若是 import 会导致下一步回归失败并自动回滚。"
fi

# 5) 回归校验 —— 与段1 基准对照（成功即 exit 0）
step "段3 回归校验（必须与基准同样跑通）"
set +e
PYTHONPATH=. "$PY" -m mrbtp_demo.verify --both --attempts 6 2>&1 \
  | tee "$BASELINE_DIR/verify_after_rename_$TS.log"
AFTER_RC=${PIPESTATUS[0]}
set -e

if [ "$AFTER_RC" = 0 ]; then
  ok "改名后回归通过 —— MiniGrid 平等归位、行为一致 ✓"
  git add -A
  git commit -q -m "refactor(p0): rename package mrbtp -> core (pluggable backend)" --no-verify || true
  c "1;32" "✓ 段3 完成并已提交。P0 全部完成。"
else
  warn "改名后回归失败（rc=${AFTER_RC}）—— 自动回滚到基线 ${P0_BASE_COMMIT}"
  git reset --hard "$P0_BASE_COMMIT"
  git clean -fd -e "$BACKUP_DIR" -e "$BASELINE_DIR" || true
  die "已回滚。请查看 $BASELINE_DIR/verify_after_rename_$TS.log 排查后重试。"
fi

echo
hr
c "1;32" "✓✓ P0 全部完成（段0–段3）"
hr
echo "  备份      : $BACKUP_TAR"
echo "  基线提交  : $P0_BASE_COMMIT"
echo "  改名提交  : $(git rev-parse --short HEAD)"
echo "  基准日志  : $BASE_LOG"
echo "  改名日志  : $BASELINE_DIR/verify_after_rename_$TS.log"
echo
c "1;37" "下一步：P1 实现 backends/pygame/（env/grid/objects/agent/physics）。"
