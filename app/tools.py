from __future__ import annotations

import json
from collections.abc import Callable
from datetime import datetime
from typing import Any


def tool_definitions() -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "name": "search_flights",
            "description": "Searches candidate flights for a trip request.",
            "parameters": {
                "type": "object",
                "properties": {
                    "origin": {"type": "string", "description": "Departure city or airport"},
                    "destination": {"type": "string", "description": "Arrival city or airport"},
                    "month": {"type": "string", "description": "Travel month or date range"},
                    "travelers": {"type": "integer", "minimum": 1},
                },
                "required": ["origin", "destination", "month", "travelers"],
                "additionalProperties": False,
            },
            "strict": True,
        },
        {
            "type": "function",
            "name": "lookup_hotel",
            "description": "Finds hotel options for a city and stay window.",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string"},
                    "check_in": {"type": "string", "description": "Approximate start date"},
                    "nights": {"type": "integer", "minimum": 1},
                    "rooms": {"type": "integer", "minimum": 1},
                },
                "required": ["city", "check_in", "nights", "rooms"],
                "additionalProperties": False,
            },
            "strict": True,
        },
        {
            "type": "function",
            "name": "get_weather",
            "description": "Returns a lightweight weather snapshot for a destination.",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {"type": "string"},
                    "timeframe": {"type": "string", "description": "When the traveler cares about the weather"},
                },
                "required": ["location", "timeframe"],
                "additionalProperties": False,
            },
            "strict": True,
        },
        {
            "type": "function",
            "name": "update_trip_plan",
            "description": "Stores a proposed trip plan summary after gathering options.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "summary": {"type": "string"},
                    "next_step": {"type": "string"},
                },
                "required": ["title", "summary", "next_step"],
                "additionalProperties": False,
            },
            "strict": True,
        },
    ]


def execute_tool(name: str, args: dict[str, Any]) -> str:
    tools: dict[str, Callable[..., dict[str, Any]]] = {
        "search_flights": search_flights,
        "lookup_hotel": lookup_hotel,
        "get_weather": get_weather,
        "update_trip_plan": update_trip_plan,
    }
    if name not in tools:
        raise ValueError(f"Unknown tool: {name}")
    return json.dumps(tools[name](**args))


def search_flights(origin: str, destination: str, month: str, travelers: int) -> dict[str, Any]:
    return {
        "origin": origin,
        "destination": destination,
        "month": month,
        "travelers": travelers,
        "options": [
            {
                "airline": "SkyBridge",
                "price_usd": 742,
                "stops": 0,
                "notes": "Fastest option for a demo itinerary.",
            },
            {
                "airline": "NorthLoop",
                "price_usd": 618,
                "stops": 1,
                "notes": "Cheaper option with one short layover.",
            },
        ],
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }


def lookup_hotel(city: str, check_in: str, nights: int, rooms: int) -> dict[str, Any]:
    return {
        "city": city,
        "check_in": check_in,
        "nights": nights,
        "rooms": rooms,
        "options": [
            {
                "name": "Harbor House",
                "nightly_rate_usd": 189,
                "neighborhood": "City Center",
                "notes": "Walkable and good for first-time visitors.",
            },
            {
                "name": "Studio Eight",
                "nightly_rate_usd": 146,
                "neighborhood": "Transit District",
                "notes": "Best value if transport access matters most.",
            },
        ],
    }


def get_weather(location: str, timeframe: str) -> dict[str, Any]:
    return {
        "location": location,
        "timeframe": timeframe,
        "forecast_summary": "Mild weather with a moderate chance of rain on one day.",
        "packing_notes": ["light jacket", "comfortable shoes", "small umbrella"],
    }


def update_trip_plan(title: str, summary: str, next_step: str) -> dict[str, Any]:
    return {
        "saved": True,
        "title": title,
        "summary": summary,
        "next_step": next_step,
    }
