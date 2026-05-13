#!/bin/sh
# Briefing 컨테이너 진입점.
# - /app/vault 이 git repo가 아니면 init + 브랜치/사용자 구성
# - BRIEFING_GIT_REMOTE_URL 환경변수가 있으면 remote 등록 (없으면 사용자가 docker exec로 직접)
set -e

VAULT="${BRIEFING_VAULT_PATH:-/app/vault}"
BRANCH="${BRIEFING_GIT_BRANCH:-main}"
REMOTE="${BRIEFING_GIT_REMOTE:-origin}"
USER_NAME="${BRIEFING_GIT_USER_NAME:-briefing-bot}"
USER_EMAIL="${BRIEFING_GIT_USER_EMAIL:-briefing@example.com}"

if [ ! -d "$VAULT/.git" ]; then
    echo "[briefing] init vault repo at $VAULT (branch=$BRANCH)"
    git init -b "$BRANCH" "$VAULT" >/dev/null
fi

git -C "$VAULT" config user.name "$USER_NAME"
git -C "$VAULT" config user.email "$USER_EMAIL"

# Trust the directory regardless of owning UID (named volume / bind mount).
git config --global --add safe.directory "$VAULT" >/dev/null 2>&1 || true

if [ -n "${BRIEFING_GIT_REMOTE_URL:-}" ]; then
    if ! git -C "$VAULT" remote get-url "$REMOTE" >/dev/null 2>&1; then
        echo "[briefing] adding remote $REMOTE = $BRIEFING_GIT_REMOTE_URL"
        git -C "$VAULT" remote add "$REMOTE" "$BRIEFING_GIT_REMOTE_URL"
    fi
fi

if ! git -C "$VAULT" rev-parse HEAD >/dev/null 2>&1; then
    echo "[briefing] empty initial commit"
    git -C "$VAULT" commit --allow-empty -m "init" >/dev/null
fi

exec "$@"
