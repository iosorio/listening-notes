#!/usr/bin/env bash
set -euo pipefail

REMOTE_HOST="${LISTENING_NOTES_REMOTE_HOST:-MacPro}"
REMOTE_ROOT="${LISTENING_NOTES_REMOTE_ROOT:-/Users/Israel/Code/ior-listening-notes}"

if [[ $# -eq 0 ]]; then
  echo "usage: $0 command [args ...]" >&2
  exit 2
fi

printf -v quoted_root '%q' "$REMOTE_ROOT"
printf -v quoted_command '%q ' "$@"
ssh "$REMOTE_HOST" "cd $quoted_root && ${quoted_command% }"
