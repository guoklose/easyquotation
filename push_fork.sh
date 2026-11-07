#!/usr/bin/env bash
# 把 easyquotation 的本机 fork 推到 GitHub。
#
# 前置：
#   1) 已完成 gh 登录（`gh auth status` 显示已登录）
#   2) 本仓库已配好 remote：
#        origin   -> https://github.com/<user>/easyquotation.git   （本 fork）
#        upstream -> https://github.com/shidenggui/easyquotation.git
#
# 用法： ./push_fork.sh
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_DIR"

export PATH="/opt/homebrew/bin:$PATH"

if ! gh auth status >/dev/null 2>&1; then
  echo "ERROR: gh 未登录。先跑：gh auth login --web" >&2
  exit 1
fi

GH_USER="$(gh api user --jq '.login')"
echo "GitHub 用户：$GH_USER"

FORK_REPO="$GH_USER/easyquotation"

# 1) 在 GitHub 上创建 fork（已存在则跳过）
if gh repo view "$FORK_REPO" >/dev/null 2>&1; then
  echo "fork 已存在：$FORK_REPO"
else
  echo "创建 fork：shidenggui/easyquotation -> $FORK_REPO"
  gh api -X POST repos/shidenggui/easyquotation/forks -f name=easyquotation >/dev/null
  for _ in $(seq 1 20); do
    gh repo view "$FORK_REPO" >/dev/null 2>&1 && break
    sleep 3
  done
  gh repo view "$FORK_REPO" >/dev/null 2>&1 || { echo "ERROR: fork 创建失败" >&2; exit 1; }
fi

# 2) 确保 origin 指向自己的 fork
git remote set-url origin "https://github.com/$FORK_REPO.git"

# 3) 推 master
git push -u origin master

# 4) 核验远端确实有我们的提交
REMOTE_SHA="$(git ls-remote origin refs/heads/master | cut -f1)"
LOCAL_SHA="$(git rev-parse master)"
echo "远端 master: $REMOTE_SHA"
echo "本地 master: $LOCAL_SHA"
[ "$REMOTE_SHA" = "$LOCAL_SHA" ] || { echo "ERROR: 远端 SHA 与本地不一致" >&2; exit 1; }

echo
echo "OK — fork 已就位：https://github.com/$FORK_REPO"
