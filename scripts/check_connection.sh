#!/usr/bin/env bash

set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
TRIP_ID="${TRIP_ID:-}"

echo "==> Checking local backend health"
curl -fsS "$BASE_URL/api/health"
echo

echo "==> Checking local backend root"
curl -fsS "$BASE_URL/"
echo

if [[ -n "$TRIP_ID" ]]; then
  echo "==> Checking Odyssey bridge list-messages for trip: $TRIP_ID"
  curl -fsS "$BASE_URL/api/integrations/odyssey/trips/$TRIP_ID/messages?last=true"
  echo

  echo "==> Posting test user message through Odyssey bridge"
  curl -fsS \
    -X POST \
    -H "Content-Type: application/json" \
    -d '{"content":"Connection smoke test from backend bridge."}' \
    "$BASE_URL/api/integrations/odyssey/trips/$TRIP_ID/messages"
  echo
else
  echo "==> Skipping Odyssey bridge test because TRIP_ID is not set"
fi

echo "==> Done"
