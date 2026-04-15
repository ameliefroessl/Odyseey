from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .agent import generate_reply
from .config import cors_config, settings
from .models import (
    CreateTripRequest,
    HealthResponse,
    MessageListResponse,
    SendMessageRequest,
    SendMessageResponse,
    TripListResponse,
    TripResponse,
)
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
def list_messages(trip_id: str) -> MessageListResponse:
    trip = storage.get_trip(trip_id)
    if trip is None:
        raise HTTPException(status_code=404, detail="Trip not found.")
    return MessageListResponse(messages=storage.list_messages(trip_id))


@app.post("/api/trips/{trip_id}/messages", response_model=SendMessageResponse)
def send_message(trip_id: str, payload: SendMessageRequest) -> SendMessageResponse:
    trip = storage.get_trip(trip_id)
    if trip is None:
        raise HTTPException(status_code=404, detail="Trip not found.")

    user_message = storage.create_message(
        trip_id=trip_id,
        role="user",
        content=payload.content,
    )

    history = storage.list_messages(trip_id)
    agent_result = generate_reply(trip, history)

    tool_messages = [
        storage.create_message(
            trip_id=trip_id,
            role="tool",
            content=item["content"],
            tool_name=item["tool_name"],
            tool_call_id=item["tool_call_id"],
            metadata=item.get("metadata", {}),
        )
        for item in agent_result["tool_messages"]
    ]

    assistant_message = storage.create_message(
        trip_id=trip_id,
        role="assistant",
        content=agent_result["assistant_text"],
    )

    refreshed_trip = storage.get_trip(trip_id) or trip
    return SendMessageResponse(
        trip=refreshed_trip,
        user_message=user_message,
        assistant_message=assistant_message,
        tool_messages=tool_messages,
    )
