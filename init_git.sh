#!/usr/bin/env bash
#
# init_git.sh — one-shot git initialisation for the standalone mrbtp-demo project.
#
# WorkBuddy could not run `git init` itself (the sandbox blocks writing the
# `.git/` directory under ~/mywork), so just run this script locally:
#
#     cd ~/mywork/mrbtp-demo
#     bash init_git.sh
#
# It is idempotent: if the repo is already initialised it will skip `git init`
# and only stage + commit whatever is new.

set -euo pipefail

# Always operate from the directory this script lives in.
cd "$(dirname "$0")"

echo "==> Working directory: $(pwd)"

# 1. init (skip if already a repo)
if [ -d .git ]; then
    echo "==> .git already exists — skipping 'git init'."
else
    echo "==> git init"
    git init -q
fi

# 2. sanity-check git identity
if ! git config user.name >/dev/null 2>&1 && ! git config --global user.name >/dev/null 2>&1; then
    echo "!!  No git user.name/email configured. Set them first, e.g.:"
    echo "      git config --global user.name  \"Yishuai Cai\""
    echo "      git config --global user.email \"1274775234@qq.com\""
    exit 1
fi

# 3. stage everything (respecting .gitignore)
echo "==> git add -A"
git add -A

# 4. show what is about to be committed, and guard against junk
echo "==> Files staged: $(git diff --cached --name-only | wc -l | tr -d ' ')"
if git diff --cached --name-only | grep -E "__pycache__|\.venv/|/output/|\.pyc$" >/dev/null 2>&1; then
    echo "!!  Warning: some ignorable files slipped into the index:"
    git diff --cached --name-only | grep -E "__pycache__|\.venv/|/output/|\.pyc$"
    echo "    Check your .gitignore before committing."
    exit 1
fi

# 5. commit (only if there is something staged)
if git diff --cached --quiet; then
    echo "==> Nothing to commit — working tree clean."
else
    echo "==> git commit"
    git commit -q -m "Initial commit: standalone minimal mrbtp-demo

Three-stage multi-robot BT planning demo (plan / execute / visualize)
on a trimmed mrbtp subset (MiniGrid-only, ~752KB).

- Cut virtualhome / numerical_env / computation_env / llm_client
- Slimmed deps from ~30 to 10
- pyproject.toml with mrbtp-demo / mrbtp-verify console scripts
- README.md, TUTORIAL.html, headless verify with auto-retry
- MIT licensed"
    echo "==> Done. Latest commit:"
    git log --oneline -1
fi

# 6. optional: push to a remote
cat <<'EOF'

----------------------------------------------------------------------
To push to GitHub / 工蜂, add a remote and push:

    git remote add origin <your-repo-url>
    git branch -M main
    git push -u origin main
----------------------------------------------------------------------
EOF
