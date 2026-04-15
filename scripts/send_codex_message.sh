#!/usr/bin/env bash

set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
TRIP_ID="${TRIP_ID:-${1:-}}"
PERSONA="${PERSONA:-Codex}"

if [[ -n "${ODYSSEY_KEY:-}" && -z "${ODYSSEY_API_KEY:-}" ]]; then
  export ODYSSEY_API_KEY="$ODYSSEY_KEY"
fi

if [[ -n "${ODYSSEY_OPENAI_KEY:-}" && -z "${ODYSSEY_API_KEY:-}" ]]; then
  export ODYSSEY_API_KEY="$ODYSSEY_OPENAI_KEY"
fi

if [[ -n "${ODYSSEY_CLAUDE_KEY:-}" && -z "${ODYSSEY_API_KEY:-}" ]]; then
  export ODYSSEY_API_KEY="$ODYSSEY_CLAUDE_KEY"
fi

if [[ -z "$TRIP_ID" ]]; then
  echo "TRIP_ID is required."
  exit 1
fi

shift $(( $# > 0 ? 1 : 0 )) || true
CONTENT="${CONTENT:-$*}"

if [[ -z "$CONTENT" ]]; then
  echo "Provide message text as CONTENT env var or command arguments."
  exit 1
fi

curl -fsS \
  -X POST \
  -H "Content-Type: application/json" \
  -d "$(printf '{"content":"%s","role":"assistant","persona":"%s"}' "$CONTENT" "$PERSONA")" \
  "$BASE_URL/api/integrations/odyssey/trips/$TRIP_ID/messages"
echo
