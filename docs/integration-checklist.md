# Integration Checklist

Use this when wiring the backend into the Odyssey UI.

## 1. What we provide

- public backend base URL
- OpenAPI docs URL
- API contract in [api-contract.md](/Users/eltsit/Documents/New%20project/docs/api-contract.md:1)
- trip and message endpoints

## 2. What the UI teammate needs from us

- backend base URL
  - example: `https://agent-sprint-api.onrender.com`
- allowed frontend origin added to `CORS_ORIGINS`
  - example: `https://trip-ui.lovable.app`
- confirmation whether the backend is running in:
  - `mock-agent` mode
  - real OpenAI mode

## 3. What we need from the UI teammate

- final frontend domain
- whether they want to show tool/debug messages
- whether the UI will:
  - keep creating trips directly in Supabase
  - or call `POST /api/trips`

## 4. Frontend request flow

1. create or load a trip
2. store `trip.id`
3. `GET /api/trips/{trip_id}/messages`
4. on each send:
   `POST /api/trips/{trip_id}/messages`

## 5. Environment variables for deployment

- `HOST=0.0.0.0`
- `PORT=8000`
- `CORS_ORIGINS=https://your-ui-domain.com`
- `OPENAI_API_KEY=...`
- `OPENAI_MODEL=gpt-5`
- `SUPABASE_URL=...`
- `SUPABASE_SERVICE_ROLE_KEY=...`
- `SUPABASE_TRIPS_TABLE=trips`
- `SUPABASE_MESSAGES_TABLE=trip_messages`

## 6. Deployment targets

Free-friendly options:

- Render for the FastAPI service
- Supabase for Postgres

Temporary sharing option:

- Cloudflare Tunnel for a local backend

## 7. Hosted Odyssey API

Odyssey already exposes:

- `GET /api/trips/{tripId}/messages`
- `GET /api/trips/{tripId}/messages?last=true`
- `POST /api/trips/{tripId}/messages`

This repo now supports an optional bridge to that hosted API using:

- `ODYSSEY_BASE_URL`
- `ODYSSEY_API_KEY`

Do not commit real bearer keys into the repo.
