# API Contract

This backend serves the Odyssey trip UI.

The UI can keep using Supabase directly for core trip CRUD if needed, but the
agent/chat flow should call this API.

## Base URL

Local:

```text
http://127.0.0.1:8000
```

Production example:

```text
https://api.your-app.com
```

## Main resources

- `trip`
- `trip_message`

## `trip`

```json
{
  "id": "trip_123",
  "title": "Tokyo Spring Trip",
  "destination": "Tokyo",
  "start_date": "2026-03-10",
  "end_date": "2026-03-15",
  "status": "planning",
  "created_at": "2026-04-15T18:40:00Z",
  "updated_at": "2026-04-15T18:42:11Z"
}
```

## `trip_message`

```json
{
  "id": "msg_123",
  "trip_id": "trip_123",
  "role": "assistant",
  "content": "Where are you flying from, and what do you want to do on this trip?",
  "tool_name": null,
  "tool_call_id": null,
  "metadata": {},
  "created_at": "2026-04-15T18:42:11Z"
}
```

### Message roles

- `user`
- `assistant`
- `tool`

## Endpoints

### `GET /api/health`

```json
{
  "status": "ok",
  "storage": "supabase",
  "model": "mock-agent"
}
```

### `GET /api/trips`

Returns trips ordered by `updated_at desc`.

### `POST /api/trips`

Creates a trip.

Request body:

```json
{
  "title": "Tokyo Spring Trip",
  "destination": "Tokyo",
  "start_date": "2026-03-10",
  "end_date": "2026-03-15"
}
```

### `GET /api/trips/:trip_id`

Returns one trip.

### `GET /api/trips/:trip_id/messages`

Returns the chat history for the trip.

### `POST /api/trips/:trip_id/messages`

Adds a user message, runs the agent, and returns the assistant/tool outputs.

Request body:

```json
{
  "content": "Help me plan this trip. I'm flying from San Francisco and want food and shopping."
}
```

Response shape:

```json
{
  "trip": {
    "id": "trip_123",
    "title": "Tokyo Spring Trip",
    "destination": "Tokyo",
    "start_date": "2026-03-10",
    "end_date": "2026-03-15",
    "status": "planning",
    "created_at": "2026-04-15T18:40:00Z",
    "updated_at": "2026-04-15T18:42:11Z"
  },
  "user_message": {
    "id": "msg_user",
    "trip_id": "trip_123",
    "role": "user",
    "content": "Help me plan this trip.",
    "tool_name": null,
    "tool_call_id": null,
    "metadata": {},
    "created_at": "2026-04-15T18:41:00Z"
  },
  "assistant_message": {
    "id": "msg_assistant",
    "trip_id": "trip_123",
    "role": "assistant",
    "content": "Where are you flying from, and what do you want to do on this trip?",
    "tool_name": null,
    "tool_call_id": null,
    "metadata": {},
    "created_at": "2026-04-15T18:42:11Z"
  },
  "tool_messages": []
}
```

## Recommended frontend flow

1. UI creates or loads a trip.
2. UI opens the trip page.
3. UI calls `GET /api/trips/{trip_id}/messages`.
4. On send, UI calls `POST /api/trips/{trip_id}/messages`.
5. UI renders:
   - `assistant_message`
   - optionally `tool_messages` in a debug panel

## Optional Odyssey bridge

If you want this backend to talk to the hosted Odyssey API directly, configure:

- `ODYSSEY_BASE_URL`
- `ODYSSEY_API_KEY`

Then these proxy endpoints are available:

### `GET /api/integrations/odyssey/trips`

### `GET /api/integrations/odyssey/trips/:trip_id/messages`

Optional query:

- `last=true`
- `limit=1..200`

### `POST /api/integrations/odyssey/trips/:trip_id/messages`

Request body:

```json
{
  "content": "What restaurants should we try?"
}
```
