from __future__ import annotations

from fastapi import BackgroundTasks, FastAPI, HTTPException, Query
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
from .storage import create_storage

app = FastAPI(title="Odyseey Trip API", version="0.2.0")
app.add_middleware(
    CORSMiddleware,
    **cors_config(),
)

storage = create_storage()


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


@app.post("/api/trips/{trip_id}/messages", response_model=MessageAcceptedResponse, status_code=202)
def send_message(
    trip_id: str,
    payload: SendMessageRequest,
    background_tasks: BackgroundTasks,
) -> MessageAcceptedResponse:
    trip = storage.get_trip(trip_id)
    if trip is None:
        raise HTTPException(status_code=404, detail="Trip not found.")

    user_message = storage.create_message(
        trip_id=trip_id,
        role=payload.role,
        content=payload.content,
    )

    if payload.role == "user":
        background_tasks.add_task(process_agent_turn, trip_id)

    refreshed_trip = storage.get_trip(trip_id) or trip
    return MessageAcceptedResponse(
        trip=refreshed_trip,
        user_message=user_message,
        status="queued" if payload.role == "user" else "stored",
        poll_path=f"/api/trips/{trip_id}/messages?last=true",
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
        result = client.create_message(trip_id, content=payload.content, role=payload.role)
    except OdysseyAPIError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {
        "provider": "odyssey",
        "trip_id": trip_id,
        "message": result,
    }


def process_agent_turn(trip_id: str) -> None:
    trip = storage.get_trip(trip_id)
    if trip is None:
        return

    try:
        history = storage.list_messages(trip_id)
        agent_result = generate_reply(trip, history)

        for item in agent_result["tool_messages"]:
            storage.create_message(
                trip_id=trip_id,
                role="tool",
                content=item["content"],
                tool_name=item["tool_name"],
                tool_call_id=item["tool_call_id"],
                metadata=item.get("metadata", {}),
            )

        storage.create_message(
            trip_id=trip_id,
            role="assistant",
            content=agent_result["assistant_text"],
        )
    except Exception as exc:
        storage.create_message(
            trip_id=trip_id,
            role="assistant",
            content="I hit an error while processing that request. Please try again.",
            metadata={"error": True, "detail": str(exc)},
        )
