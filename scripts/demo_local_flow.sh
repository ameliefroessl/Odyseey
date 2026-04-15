#!/usr/bin/env bash

set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
TITLE="${TITLE:-Tokyo Spring Trip}"
DESTINATION="${DESTINATION:-Tokyo}"
START_DATE="${START_DATE:-2026-03-10}"
END_DATE="${END_DATE:-2026-03-15}"
PROMPT="${PROMPT:-I am flying from San Francisco and want food and shopping.}"

echo "==> Creating demo trip"
TRIP_RESPONSE="$(curl -fsS \
  -X POST "$BASE_URL/api/trips" \
  -H "Content-Type: application/json" \
  -d "$(printf '{"title":"%s","destination":"%s","start_date":"%s","end_date":"%s"}' "$TITLE" "$DESTINATION" "$START_DATE" "$END_DATE")")"
echo "$TRIP_RESPONSE"
echo

TRIP_ID="$(printf '%s' "$TRIP_RESPONSE" | python3 -c 'import json,sys; print(json.load(sys.stdin)["trip"]["id"])')"
echo "==> Trip ID: $TRIP_ID"
echo

echo "==> Posting user message"
POST_RESPONSE="$(curl -fsS \
  -X POST "$BASE_URL/api/trips/$TRIP_ID/messages?wait=false" \
  -H "Content-Type: application/json" \
  -d "$(printf '{"content":"%s","role":"user"}' "$PROMPT")")"
echo "$POST_RESPONSE"
echo

echo "==> Polling latest message"
for _ in 1 2 3 4 5; do
  LAST_RESPONSE="$(curl -fsS "$BASE_URL/api/trips/$TRIP_ID/messages?last=true")"
  LAST_ROLE="$(printf '%s' "$LAST_RESPONSE" | python3 -c 'import json,sys; d=json.load(sys.stdin); print((d.get("last_message") or {}).get("role",""))')"
  if [[ "$LAST_ROLE" == "assistant" ]]; then
    echo "$LAST_RESPONSE"
    echo
    break
  fi
  sleep 1
done

echo "==> Fetching recent messages"
curl -fsS "$BASE_URL/api/trips/$TRIP_ID/messages?limit=5"
echo

echo "==> Demo complete"
