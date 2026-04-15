# Odyseey Trip API

Backend for the Odyssey trip-planning UI.

## What it includes

- FastAPI API for trips and trip messages
- OpenAI tool-calling loop with a mock fallback
- mock trip-planning tools for flights, hotels, and weather
- optional Supabase persistence
- optional Temporal scaffolding for longer workflows later
- Render deployment config

## Local run

1. Create a virtualenv:

```bash
python3 -m venv .venv
```

2. Install dependencies:

```bash
.venv/bin/pip install -r requirements.txt
```

3. Start the API:

```bash
HOST=127.0.0.1 PORT=8000 .venv/bin/python -m app.server
```

4. Open:

```text
http://127.0.0.1:8000/docs
```

## Connection check

After the API is running, you can smoke-test it with:

```bash
cd "/Users/eltsit/Documents/New project/Odyseey"
bash scripts/check_connection.sh
```

If you also want to test the hosted Odyssey bridge, set:

```bash
export ODYSSEY_API_KEY=your_key_here
export TRIP_ID=your_trip_id
bash scripts/check_connection.sh
```

That checks:

- local API health
- local API root endpoint
- hosted Odyssey message fetch via the bridge
- hosted Odyssey test message post via the bridge

## Environment variables

- `HOST` defaults to `0.0.0.0`
- `PORT` defaults to `8000`
- `CORS_ORIGINS`
- `OPENAI_API_KEY`
- `OPENAI_MODEL`
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `SUPABASE_TRIPS_TABLE` defaults to `trips`
- `SUPABASE_MESSAGES_TABLE` defaults to `trip_messages`
- `TEMPORAL_ENABLED`
- `TEMPORAL_ADDRESS`
- `TEMPORAL_NAMESPACE`
- `TEMPORAL_TASK_QUEUE`
- `ODYSSEY_BASE_URL`
- `ODYSSEY_API_KEY`

## Contracts and setup

- API contract: [docs/api-contract.md](/Users/eltsit/Documents/New%20project/Odyseey/docs/api-contract.md:1)
- schema: [docs/schema.sql](/Users/eltsit/Documents/New%20project/Odyseey/docs/schema.sql:1)
- integration notes: [docs/integration-checklist.md](/Users/eltsit/Documents/New%20project/Odyseey/docs/integration-checklist.md:1)
- Temporal notes: [docs/temporal-setup.md](/Users/eltsit/Documents/New%20project/Odyseey/docs/temporal-setup.md:1)

## Expected integration

- Odyssey UI can keep using Supabase for trip CRUD if that is already live.
- The trip chat/assistant should call this API.
- If needed, this API can also proxy the hosted Odyssey trip-message endpoints.
