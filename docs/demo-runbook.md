# Demo Runbook

Use this when you need a reliable local demo even if the live Odyssey bridge is
not available.

## Goal

Show that the backend:

- creates a trip
- accepts a user message
- queues processing
- runs the agent/tool logic
- returns an assistant reply through polling

## Start the backend

```bash
cd "/Users/eltsit/Documents/New project/Odyseey"
HOST=127.0.0.1 PORT=8000 ../.venv/bin/python -m app.server
```

## Run the demo flow

In a second terminal:

```bash
cd "/Users/eltsit/Documents/New project/Odyseey"
bash scripts/demo_local_flow.sh
```

## What to say during the demo

1. "We create a trip with destination and dates."
2. "The frontend sends a user message to our backend."
3. "Our backend returns `202 Accepted` immediately so the UI can poll."
4. "The backend runs the agent logic and tools in the background."
5. "The UI polls `GET /messages?last=true` until the assistant reply appears."

## Suggested demo prompt

```text
I am flying from San Francisco and want food and shopping.
```

## What the audience should see

- trip creation response with a real `trip.id`
- message post response with:
  - `status: queued`
  - `poll_path`
- latest assistant message from polling
- recent tool + assistant messages from `limit=5`

## If someone asks about the live UI

Say:

- Lovable can call the same `POST /api/trips/{trip_id}/messages`
- then poll `GET /api/trips/{trip_id}/messages?last=true`
- the current blocker on the hosted Odyssey bridge is upstream API key auth, not the polling backend
