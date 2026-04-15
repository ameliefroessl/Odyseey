# Temporal Setup

This project now includes Temporal scaffolding for future durable trip-planning
workflows.

It does **not** replace the current FastAPI request/response flow yet. Temporal
is wired in as an optional layer you can run locally while the MVP stays simple.

## What was added

- Python SDK dependency: `temporalio`
- workflow: [app/temporal_workflows.py](/Users/eltsit/Documents/New%20project/app/temporal_workflows.py:1)
- activity: [app/temporal_activities.py](/Users/eltsit/Documents/New%20project/app/temporal_activities.py:1)
- worker: [app/temporal_worker.py](/Users/eltsit/Documents/New%20project/app/temporal_worker.py:1)
- sample runner: [app/temporal_runner.py](/Users/eltsit/Documents/New%20project/app/temporal_runner.py:1)

## Why this helps

Temporal is useful later for:

- poll and reminder workflows
- multi-step trip planning
- retries for flaky third-party APIs
- workflows that wait for user input

## Local setup

According to Temporal's official docs, the quickest local path is:

- install the Python SDK with `pip install temporalio`
- install the Temporal CLI
- start the local dev server with `temporal server start-dev`

Sources:

- [Temporal Python quickstart](https://docs.temporal.io/develop/python/set-up-your-local-python)
- [Temporal CLI docs](https://docs.temporal.io/cli)

## Start Temporal locally

If you have the Temporal CLI installed:

```bash
temporal server start-dev
```

That starts:

- Temporal service on `localhost:7233`
- Temporal UI on `http://localhost:8233`

The CLI docs say the development server starts with an in-memory database by
default, and you can persist state locally with:

```bash
temporal server start-dev --db-filename temporal.db
```

## Run the worker

In a second terminal:

```bash
cd "/Users/eltsit/Documents/New project"
.venv/bin/python -m app.temporal_worker
```

## Run a sample workflow

In a third terminal:

```bash
cd "/Users/eltsit/Documents/New project"
.venv/bin/python -m app.temporal_runner
```

## Environment variables

- `TEMPORAL_ENABLED=false`
- `TEMPORAL_ADDRESS=localhost:7233`
- `TEMPORAL_NAMESPACE=default`
- `TEMPORAL_TASK_QUEUE=trip-planning`

## Current status

Temporal is installed in the Python project and scaffolded for local
development, but the main API is still using the direct FastAPI flow for actual
responses.
