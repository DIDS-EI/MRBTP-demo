# scripts/ — 重构与运维脚本

## `p0_refactor.sh` · 可插拔后端 P0 重构

对应设计文档 `docs/PLUGGABLE_BACKEND_DESIGN.html` 的 **§9 实施路线 P0**。
目标：让两个抽象协议成立、MiniGrid 平等归位，并证明旧 demo 行为不变。

### 它分 4 段，风险从低到高

| 段 | 做什么 | 风险 | 产出 |
|----|--------|------|------|
| **段0 安全网** | `tar` 全量备份 + `git init` 首次提交（无 git 就建一个） | 无 | `.p0_backups/pre_p0_*.tar.gz` + git 基线提交 |
| **段1 基准** | 跑现成 `verify.py` 把旧 demo 跑通，存回归基准 | 无 | `.p0_baseline/verify_baseline_*.log` |
| **段2 抽象骨架** | 新建 `interfaces.py`（两个协议）+ `backends/ scenes/ themes/` 骨架与 README | 无（纯新增） | 协议契约 + 骨架目录 |
| **段3 改名归位** | `mrbtp/` → `core/`，批量改 237 处 import，回归校验 | **高** | 改名提交（回归失败自动回滚） |

### 用法

```bash
# 在 repo 根目录（含 pyproject.toml），用项目 .venv
bash scripts/p0_refactor.sh                  # 段0–段2（默认，全程零风险）
bash scripts/p0_refactor.sh --with-rename    # 段0–段3（含 mrbtp→core 改名）
bash scripts/p0_refactor.sh --baseline-only  # 只跑段0+段1（仅备份+基准）
bash scripts/p0_refactor.sh --dry-run        # 只打印将做什么，不动文件
```

**推荐流程**：先 `--dry-run` 看一遍 → 跑默认（段0–段2）确认安全骨架落地 →
确认无误后再 `--with-rename` 触发改名。

### 为什么默认不改名

`mrbtp` 改名牵动 **237 处 import**，是 P0 唯一的高风险动作。默认只跑零风险的
段0–段2；改名做成显式 `--with-rename`，且全程 git 兜底：**改名后回归失败会
自动 `git reset --hard` 回滚到段0 基线**，不会留下半截烂摊子。

### 三个工程安全点

1. **`mrbtp` 是 `mrbtp_demo` 的前缀** —— 改名用 perl 词边界 `\bmrbtp\b`，
   `mrbtp_demo` 中 `mrbtp` 右侧是下划线（单词字符），不构成词边界，**天然不被误伤**。
2. **`ROOT_PATH` 基于 `__file__` 相对定位**（`os.path.join(__file__,"../..")`），
   `importlib` 也是按文件路径加载 —— 包改名后 behavior_lib 仍能自动找到，无需改路径逻辑。
3. **`verify.py` 自带多次重试**（`--attempts 6`）—— planner 是固有 flaky
   （goal 是 set + `PYTHONHASHSEED`，单次 ~70% 成功），重试把误报压到 <1%。

### 出问题怎么回滚

- 段3 自动回滚：脚本内已处理（`git reset --hard <基线>`）。
- 手动整体回滚：`git reset --hard <段0 基线提交>`，或从 `.p0_backups/*.tar.gz` 解包。
