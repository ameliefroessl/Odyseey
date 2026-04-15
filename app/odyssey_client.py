from __future__ import annotations

import json
from typing import Any
from urllib import error, parse, request

from .config import settings


class OdysseyAPIError(RuntimeError):
    pass


class OdysseyClient:
    def __init__(self) -> None:
        if not settings.odyssey_api_key:
            raise OdysseyAPIError("ODYSSEY_API_KEY is not configured.")

        self.base_url = settings.odyssey_base_url.rstrip("/")
        self.headers = {
            "Authorization": f"Bearer {settings.odyssey_api_key}",
            "Content-Type": "application/json",
        }

    def list_trips(self) -> Any:
        return self._request(
            "GET",
            "/api/trips",
        )

    def list_messages(self, trip_id: str, *, last: bool = False, limit: int | None = None) -> Any:
        query_params = []
        if last:
            query_params.append(("last", "true"))
        if limit is not None:
            query_params.append(("limit", str(limit)))
        query = f"?{parse.urlencode(query_params)}" if query_params else ""
        return self._request(
            "GET",
            f"/api/trips/{parse.quote(trip_id)}/messages{query}",
        )

    def create_message(self, trip_id: str, *, content: str, role: str = "user") -> Any:
        return self._request(
            "POST",
            f"/api/trips/{parse.quote(trip_id)}/messages",
            payload={"content": content, "role": role},
        )

    def _request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> Any:
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        req = request.Request(
            url=f"{self.base_url}{path}",
            method=method,
            headers=self.headers,
            data=body,
        )
        try:
            with request.urlopen(req) as response:
                raw = response.read().decode("utf-8")
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8")
            raise OdysseyAPIError(f"Odyssey request failed: {exc.code} {detail}") from exc

        return json.loads(raw) if raw else None


def create_odyssey_client() -> OdysseyClient:
    return OdysseyClient()
