from __future__ import annotations

from fastapi import BackgroundTasks, FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware

from .agent import generate_reply
from .config import cors_config, settings
from .models import (
    CreateTripRequest,
    HealthResponse,
    MessageAcceptedResponse,
    MessageListResponse,
    SendMessageRequest,
    TripListResponse,
    TripResponse,
)
from .odyssey_client import OdysseyAPIError, create_odyssey_client
from .odyssey_watcher import OdysseyAutoReplyWatcher
from .storage import create_storage

app = FastAPI(title="Odyseey Trip API", version="0.2.0")
app.add_middleware(
    CORSMiddleware,
    **cors_config(),
)

storage = create_storage()
odyssey_watcher = OdysseyAutoReplyWatcher()


@app.on_event("startup")
def startup() -> None:
    odyssey_watcher.start()


@app.on_event("shutdown")
def shutdown() -> None:
    odyssey_watcher.stop()


@app.get("/")
def root() -> dict[str, str]:
    return {
        "name": "Odyseey Trip API",
        "status": "ok",
        "docs": "/docs",
        "health": "/api/health",
    }


@app.get("/api/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        storage="supabase" if settings.supabase_url and settings.supabase_service_role_key else "in-memory",
        model=settings.openai_model if settings.openai_api_key else "mock-agent",
    )


@app.get("/api/trips", response_model=TripListResponse)
def list_trips() -> TripListResponse:
    return TripListResponse(trips=storage.list_trips())


@app.post("/api/trips", response_model=TripResponse, status_code=201)
def create_trip(payload: CreateTripRequest) -> TripResponse:
    trip = storage.create_trip(
        title=payload.title,
        destination=payload.destination,
        start_date=payload.start_date.isoformat() if payload.start_date else None,
        end_date=payload.end_date.isoformat() if payload.end_date else None,
    )
    return TripResponse(trip=trip)


@app.get("/api/trips/{trip_id}", response_model=TripResponse)
def get_trip(trip_id: str) -> TripResponse:
    trip = storage.get_trip(trip_id)
    if trip is None:
        raise HTTPException(status_code=404, detail="Trip not found.")
    return TripResponse(trip=trip)


@app.get("/api/trips/{trip_id}/messages", response_model=MessageListResponse)
def list_messages(
    trip_id: str,
    last: bool = Query(default=False),
    limit: int | None = Query(default=None, ge=1, le=200),
) -> MessageListResponse:
    trip = storage.get_trip(trip_id)
    if trip is None:
        raise HTTPException(status_code=404, detail="Trip not found.")
    messages = storage.list_messages(trip_id)
    if limit is not None:
        messages = messages[-limit:]
    last_message = messages[-1] if messages else None
    if last:
        messages = [last_message] if last_message is not None else []
    return MessageListResponse(messages=messages, last_message=last_message)


@app.post("/api/trips/{trip_id}/messages", response_model=MessageAcceptedResponse)
def send_message(
    trip_id: str,
    payload: SendMessageRequest,
    background_tasks: BackgroundTasks,
    response: Response,
    wait: bool = Query(default=True),
) -> MessageAcceptedResponse:
    trip = storage.get_trip(trip_id)
    if trip is None:
        raise HTTPException(status_code=404, detail="Trip not found.")

    user_message = storage.create_message(
        trip_id=trip_id,
        role=payload.role,
        content=_format_outbound_content(payload),
        metadata={"persona": payload.persona} if payload.persona else {},
    )

    assistant_message = None
    tool_messages = []

    if payload.role == "user" and wait:
        tool_messages, assistant_message = run_agent_turn(trip_id)
    elif payload.role == "user":
        response.status_code = 202
        background_tasks.add_task(process_agent_turn, trip_id)
    else:
        response.status_code = 200

    refreshed_trip = storage.get_trip(trip_id) or trip
    return MessageAcceptedResponse(
        trip=refreshed_trip,
        user_message=user_message,
        status=(
            "completed"
            if payload.role == "user" and wait
            else "queued"
            if payload.role == "user"
            else "stored"
        ),
        poll_path=f"/api/trips/{trip_id}/messages?last=true",
        assistant_message=assistant_message,
        tool_messages=tool_messages,
    )


@app.get("/api/integrations/odyssey/trips")
def odyssey_trips() -> dict[str, object]:
    try:
        client = create_odyssey_client()
        trips = client.list_trips()
    except OdysseyAPIError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {
        "provider": "odyssey",
        "trips": trips,
    }


@app.get("/api/integrations/odyssey/trips/{trip_id}/messages")
def odyssey_messages(
    trip_id: str,
    last: bool = Query(default=False),
    limit: int | None = Query(default=None, ge=1, le=200),
) -> dict[str, object]:
    try:
        client = create_odyssey_client()
        messages = client.list_messages(trip_id, last=last, limit=limit)
    except OdysseyAPIError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {
        "provider": "odyssey",
        "trip_id": trip_id,
        "last": last,
        "limit": limit,
        "response": messages,
    }


@app.post("/api/integrations/odyssey/trips/{trip_id}/messages")
def odyssey_post_message(trip_id: str, payload: SendMessageRequest) -> dict[str, object]:
    try:
        client = create_odyssey_client()
        result = client.create_message(
            trip_id,
            content=_format_outbound_content(payload),
            role=payload.role,
        )
    except OdysseyAPIError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {
        "provider": "odyssey",
        "trip_id": trip_id,
        "message": result,
    }


@app.get("/api/integrations/odyssey/watcher")
def odyssey_watcher_status() -> dict[str, object]:
    status = odyssey_watcher.status()
    return {
        "provider": "odyssey",
        "watcher": {
            "enabled": status.enabled,
            "running": status.running,
            "trip_count": status.trip_count,
            "trip_ids": status.trip_ids,
            "trip_titles": status.trip_titles,
            "filter_trip_id": status.filter_trip_id,
            "filter_trip_title": status.filter_trip_title,
            "last_handled_user_ids": status.last_handled_user_ids,
            "last_reply_preview": status.last_reply_preview,
            "last_error": status.last_error,
            "poll_seconds": settings.odyssey_autoreply_poll_seconds,
            "persona": settings.odyssey_autoreply_persona,
        },
    }


def process_agent_turn(trip_id: str) -> None:
    run_agent_turn(trip_id)


def run_agent_turn(trip_id: str) -> tuple[list, object | None]:
    trip = storage.get_trip(trip_id)
    if trip is None:
        return [], None

    try:
        history = storage.list_messages(trip_id)
        agent_result = generate_reply(trip, history)
        created_tool_messages = []

        for item in agent_result["tool_messages"]:
            created_tool_messages.append(
                storage.create_message(
                    trip_id=trip_id,
                    role="tool",
                    content=item["content"],
                    tool_name=item["tool_name"],
                    tool_call_id=item["tool_call_id"],
                    metadata=item.get("metadata", {}),
                )
            )

        assistant_message = storage.create_message(
            trip_id=trip_id,
            role="assistant",
            content=agent_result["assistant_text"],
        )
        return created_tool_messages, assistant_message
    except Exception as exc:
        assistant_message = storage.create_message(
            trip_id=trip_id,
            role="assistant",
            content="I hit an error while processing that request. Please try again.",
            metadata={"error": True, "detail": str(exc)},
        )
        return [], assistant_message


def _format_outbound_content(payload: SendMessageRequest) -> str:
    if payload.role == "assistant" and payload.persona:
        return f"[{payload.persona}] {payload.content}"
    return payload.content
