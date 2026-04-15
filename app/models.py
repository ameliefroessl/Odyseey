from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


MessageRole = Literal["user", "assistant", "tool"]
TripStatus = Literal["planning", "confirmed", "archived"]


class Trip(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    title: str
    destination: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    status: TripStatus | str = "planning"
    created_at: datetime
    updated_at: datetime


class TripMessage(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    trip_id: str
    role: MessageRole
    content: str
    tool_name: str | None = None
    tool_call_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class CreateTripRequest(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    destination: str | None = Field(default=None, max_length=120)
    start_date: date | None = None
    end_date: date | None = None


class TripListResponse(BaseModel):
    trips: list[Trip]


class TripResponse(BaseModel):
    trip: Trip


class MessageListResponse(BaseModel):
    messages: list[TripMessage]
    last_message: TripMessage | None = None


class SendMessageRequest(BaseModel):
    content: str = Field(min_length=1, max_length=5000)
    role: MessageRole = "user"
    persona: str | None = Field(default=None, max_length=60)


class MessageAcceptedResponse(BaseModel):
    trip: Trip
    user_message: TripMessage
    status: str = "queued"
    poll_path: str


class HealthResponse(BaseModel):
    status: str
    storage: str
    model: str
