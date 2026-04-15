from __future__ import annotations

import logging
import threading
from dataclasses import dataclass

from .agent import generate_reply
from .config import settings
from .models import Trip, TripMessage
from .odyssey_client import OdysseyAPIError, OdysseyClient, create_odyssey_client

logger = logging.getLogger(__name__)


@dataclass
class WatcherStatus:
    enabled: bool
    running: bool
    trip_count: int
    trip_ids: list[str]
    trip_titles: list[str]
    filter_trip_id: str | None
    filter_trip_title: str | None
    last_handled_user_ids: dict[str, str | None]
    last_reply_preview: str | None
    last_error: str | None


class OdysseyAutoReplyWatcher:
    def __init__(self) -> None:
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._initialized_trip_ids: set[str] = set()
        self._filter_trip_id: str | None = settings.odyssey_autoreply_trip_id
        self._filter_trip_title: str | None = settings.odyssey_autoreply_trip_title
        self._known_trips: dict[str, str] = {}
        self._last_handled_user_ids: dict[str, str | None] = {}
        self._last_reply_preview: str | None = None
        self._last_error: str | None = None

    def start(self) -> None:
        if not settings.odyssey_autoreply_enabled:
            logger.info("Odyssey auto-reply watcher is disabled.")
            return
        if self._thread and self._thread.is_alive():
            return

        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run_loop,
            name="odyssey-auto-reply",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=max(settings.odyssey_autoreply_poll_seconds, 1.0) + 1.0)

    def status(self) -> WatcherStatus:
        trip_items = sorted(self._known_trips.items(), key=lambda item: item[1].casefold())
        return WatcherStatus(
            enabled=settings.odyssey_autoreply_enabled,
            running=bool(self._thread and self._thread.is_alive()),
            trip_count=len(trip_items),
            trip_ids=[trip_id for trip_id, _ in trip_items],
            trip_titles=[title for _, title in trip_items],
            filter_trip_id=self._filter_trip_id,
            filter_trip_title=self._filter_trip_title,
            last_handled_user_ids=dict(self._last_handled_user_ids),
            last_reply_preview=self._last_reply_preview,
            last_error=self._last_error,
        )

    def _run_loop(self) -> None:
        logger.info("Starting Odyssey auto-reply watcher.")
        try:
            client = create_odyssey_client()
        except OdysseyAPIError as exc:
            self._last_error = str(exc)
            logger.warning("Odyssey auto-reply watcher could not start: %s", exc)
            return

        while not self._stop_event.is_set():
            try:
                trips = self._resolve_trips(client)
                self._known_trips = {trip.id: trip.title for trip in trips}
                if not trips:
                    self._last_error = "No Odyssey trips matched the current auto-reply filters."
                    self._wait_for_next_poll()
                    continue
                for trip in trips:
                    self._handle_trip(client, trip)
                self._last_error = None
            except Exception as exc:  # pragma: no cover - runtime safety net
                self._last_error = str(exc)
                logger.exception("Odyssey auto-reply watcher failed: %s", exc)

            self._wait_for_next_poll()

    def _wait_for_next_poll(self) -> None:
        self._stop_event.wait(settings.odyssey_autoreply_poll_seconds)

    def _resolve_trips(self, client: OdysseyClient) -> list[Trip]:
        trip_rows = client.list_trips()
        rows = trip_rows.get("trips", []) if isinstance(trip_rows, dict) else trip_rows
        trips = [Trip.model_validate(row) for row in rows]

        if self._filter_trip_id:
            return [trip for trip in trips if trip.id == self._filter_trip_id]

        if self._filter_trip_title:
            wanted = self._filter_trip_title.casefold()
            return [trip for trip in trips if trip.title.casefold() == wanted]

        return trips

    def _handle_trip(self, client: OdysseyClient, trip: Trip) -> None:
        messages = self._load_messages(client, trip.id)
        latest_user = next((message for message in reversed(messages) if message.role == "user"), None)

        if trip.id not in self._initialized_trip_ids:
            self._last_handled_user_ids[trip.id] = latest_user.id if latest_user else None
            self._initialized_trip_ids.add(trip.id)
            logger.info(
                "Odyssey auto-reply watcher baseline set for trip %s (%s).",
                trip.title,
                trip.id,
            )
            return

        latest_message = messages[-1] if messages else None
        if latest_message is None or latest_message.role != "user":
            return
        if latest_message.id == self._last_handled_user_ids.get(trip.id):
            return

        reply_text = self._build_reply_text(trip, messages)
        client.create_message(
            trip.id,
            content=f"[{settings.odyssey_autoreply_persona}] {reply_text}",
            role="assistant",
        )
        self._last_handled_user_ids[trip.id] = latest_message.id
        self._last_reply_preview = f"{trip.title}: {reply_text[:140]}"
        logger.info(
            "Posted %s auto-reply to trip %s for remote message %s.",
            settings.odyssey_autoreply_persona,
            trip.id,
            latest_message.id,
        )

    def _load_messages(self, client: OdysseyClient, trip_id: str) -> list[TripMessage]:
        message_rows = client.list_messages(trip_id, limit=settings.odyssey_autoreply_history_limit)
        rows = message_rows.get("messages", []) if isinstance(message_rows, dict) else message_rows
        return [TripMessage.model_validate(row) for row in rows]

    def _build_reply_text(self, trip: Trip, messages: list[TripMessage]) -> str:
        try:
            reply = generate_reply(trip, messages)
        except Exception:
            logger.exception("Generating an Odyssey auto-reply failed for trip %s.", trip.id)
            return "I hit an error while processing that request. Please try again."

        assistant_text = (reply.get("assistant_text") or "").strip()
        if assistant_text:
            return assistant_text
        return "I could not generate a useful reply yet. Please try again."
