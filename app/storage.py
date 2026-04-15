from __future__ import annotations

import json
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any
from urllib import error, parse, request

from .config import settings
from .models import Trip, TripMessage


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Storage(ABC):
    @abstractmethod
    def list_trips(self) -> list[Trip]:
        raise NotImplementedError

    @abstractmethod
    def create_trip(
        self,
        *,
        title: str,
        destination: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> Trip:
        raise NotImplementedError

    @abstractmethod
    def get_trip(self, trip_id: str) -> Trip | None:
        raise NotImplementedError

    @abstractmethod
    def update_trip(self, trip_id: str, **updates: Any) -> Trip | None:
        raise NotImplementedError

    @abstractmethod
    def list_messages(self, trip_id: str) -> list[TripMessage]:
        raise NotImplementedError

    @abstractmethod
    def create_message(
        self,
        *,
        trip_id: str,
        role: str,
        content: str,
        tool_name: str | None = None,
        tool_call_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> TripMessage:
        raise NotImplementedError


class InMemoryStorage(Storage):
    def __init__(self) -> None:
        self.trips: dict[str, Trip] = {}
        self.messages: dict[str, list[TripMessage]] = {}

    def list_trips(self) -> list[Trip]:
        return sorted(self.trips.values(), key=lambda item: item.updated_at, reverse=True)

    def create_trip(
        self,
        *,
        title: str,
        destination: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> Trip:
        from uuid import uuid4

        now = utcnow()
        trip = Trip(
            id=str(uuid4()),
            title=title,
            destination=destination,
            start_date=start_date,
            end_date=end_date,
            status="planning",
            created_at=now,
            updated_at=now,
        )
        self.trips[trip.id] = trip
        self.messages[trip.id] = []
        return trip

    def get_trip(self, trip_id: str) -> Trip | None:
        return self.trips.get(trip_id)

    def update_trip(self, trip_id: str, **updates: Any) -> Trip | None:
        current = self.trips.get(trip_id)
        if current is None:
            return None
        next_trip = current.model_copy(update=updates)
        self.trips[trip_id] = next_trip
        return next_trip

    def list_messages(self, trip_id: str) -> list[TripMessage]:
        return list(self.messages.get(trip_id, []))

    def create_message(
        self,
        *,
        trip_id: str,
        role: str,
        content: str,
        tool_name: str | None = None,
        tool_call_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> TripMessage:
        from uuid import uuid4

        message = TripMessage(
            id=str(uuid4()),
            trip_id=trip_id,
            role=role,
            content=content,
            tool_name=tool_name,
            tool_call_id=tool_call_id,
            metadata=metadata or {},
            created_at=utcnow(),
        )
        self.messages.setdefault(trip_id, []).append(message)
        trip = self.trips.get(trip_id)
        if trip is not None:
            self.trips[trip_id] = trip.model_copy(update={"updated_at": utcnow()})
        return message


class SupabaseStorage(Storage):
    def __init__(self) -> None:
        if not settings.supabase_url or not settings.supabase_service_role_key:
            raise ValueError("Supabase settings are incomplete.")

        self.base_url = settings.supabase_url.rstrip("/")
        self.headers = {
            "apikey": settings.supabase_service_role_key,
            "Authorization": f"Bearer {settings.supabase_service_role_key}",
            "Content-Type": "application/json",
        }

    def list_trips(self) -> list[Trip]:
        rows = self._request(
            "GET",
            f"/{settings.supabase_trips_table}?select=*&order=updated_at.desc",
        )
        return [Trip.model_validate(row) for row in rows]

    def create_trip(
        self,
        *,
        title: str,
        destination: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> Trip:
        from uuid import uuid4

        now = utcnow().isoformat()
        payload = {
            "id": str(uuid4()),
            "title": title,
            "destination": destination,
            "start_date": start_date,
            "end_date": end_date,
            "status": "planning",
            "created_at": now,
            "updated_at": now,
        }
        rows = self._request(
            "POST",
            f"/{settings.supabase_trips_table}",
            payload=[payload],
            prefer="return=representation",
        )
        return Trip.model_validate(rows[0])

    def get_trip(self, trip_id: str) -> Trip | None:
        rows = self._request(
            "GET",
            f"/{settings.supabase_trips_table}?select=*&id=eq.{parse.quote(trip_id)}",
        )
        return Trip.model_validate(rows[0]) if rows else None

    def update_trip(self, trip_id: str, **updates: Any) -> Trip | None:
        payload = dict(updates)
        rows = self._request(
            "PATCH",
            f"/{settings.supabase_trips_table}?id=eq.{parse.quote(trip_id)}",
            payload=payload,
            prefer="return=representation",
        )
        return Trip.model_validate(rows[0]) if rows else None

    def list_messages(self, trip_id: str) -> list[TripMessage]:
        rows = self._request(
            "GET",
            (
                f"/{settings.supabase_messages_table}?select=*&order=created_at.asc"
                f"&trip_id=eq.{parse.quote(trip_id)}"
            ),
        )
        return [TripMessage.model_validate(row) for row in rows]

    def create_message(
        self,
        *,
        trip_id: str,
        role: str,
        content: str,
        tool_name: str | None = None,
        tool_call_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> TripMessage:
        from uuid import uuid4

        payload = {
            "id": str(uuid4()),
            "trip_id": trip_id,
            "role": role,
            "content": content,
            "tool_name": tool_name,
            "tool_call_id": tool_call_id,
            "metadata": metadata or {},
            "created_at": utcnow().isoformat(),
        }
        rows = self._request(
            "POST",
            f"/{settings.supabase_messages_table}",
            payload=[payload],
            prefer="return=representation",
        )
        self.update_trip(trip_id, updated_at=utcnow().isoformat())
        return TripMessage.model_validate(rows[0])

    def _request(
        self,
        method: str,
        path: str,
        payload: Any | None = None,
        prefer: str | None = None,
    ) -> list[dict[str, Any]]:
        headers = dict(self.headers)
        if prefer:
            headers["Prefer"] = prefer
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        req = request.Request(
            url=f"{self.base_url}/rest/v1{path}",
            method=method,
            headers=headers,
            data=body,
        )
        try:
            with request.urlopen(req) as response:
                raw = response.read().decode("utf-8")
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8")
            raise RuntimeError(f"Supabase request failed: {exc.code} {detail}") from exc

        return json.loads(raw) if raw else []


def create_storage() -> Storage:
    if settings.supabase_url and settings.supabase_service_role_key:
        return SupabaseStorage()
    return InMemoryStorage()
