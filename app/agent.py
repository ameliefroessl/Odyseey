from __future__ import annotations

import json
from typing import Any

from .config import settings
from .models import Trip, TripMessage
from .tools import execute_tool, tool_definitions

SYSTEM_PROMPT = """
You are a travel planning agent for a collaborative trip app.
Ask concise follow-up questions when essential trip details are missing.
Once you know enough, use tools to propose useful options.
Keep answers short, practical, and easy for a UI to render.
""".strip()

INTEREST_KEYWORDS = {
    "food",
    "shopping",
    "museum",
    "museums",
    "nightlife",
    "hiking",
    "beach",
    "history",
    "art",
    "nature",
    "adventure",
    "restaurants",
}


def build_input(trip: Trip, messages: list[TripMessage]) -> list[dict[str, Any]]:
    trip_context = {
        "title": trip.title,
        "destination": trip.destination,
        "start_date": trip.start_date.isoformat() if trip.start_date else None,
        "end_date": trip.end_date.isoformat() if trip.end_date else None,
        "status": trip.status,
    }
    input_items: list[dict[str, Any]] = [
        {
            "role": "system",
            "content": [{"type": "input_text", "text": SYSTEM_PROMPT}],
        },
        {
            "role": "system",
            "content": [{"type": "input_text", "text": f"Trip context: {json.dumps(trip_context)}"}],
        },
    ]
    for message in messages:
        if message.role not in {"user", "assistant"}:
            continue
        input_items.append(
            {
                "role": message.role,
                "content": [{"type": "input_text", "text": message.content}],
            }
        )
    return input_items


def generate_reply(trip: Trip, messages: list[TripMessage]) -> dict[str, Any]:
    if settings.openai_api_key:
        return _generate_reply_with_openai(trip, messages)
    return _generate_reply_with_mock(trip, messages)


def _generate_reply_with_openai(trip: Trip, messages: list[TripMessage]) -> dict[str, Any]:
    from openai import OpenAI

    client = OpenAI(api_key=settings.openai_api_key)
    input_items = build_input(trip, messages)
    tool_messages: list[dict[str, Any]] = []

    while True:
        response = client.responses.create(
            model=settings.openai_model,
            input=input_items,
            tools=tool_definitions(),
        )
        function_calls = [item for item in response.output if item.type == "function_call"]
        if not function_calls:
            return {
                "assistant_text": response.output_text,
                "tool_messages": tool_messages,
            }

        for call in function_calls:
            args = json.loads(call.arguments)
            output = execute_tool(call.name, args)
            tool_messages.append(
                {
                    "content": output,
                    "tool_name": call.name,
                    "tool_call_id": call.call_id,
                    "metadata": {"arguments": args},
                }
            )
            input_items.append(
                {
                    "type": "function_call_output",
                    "call_id": call.call_id,
                    "output": output,
                }
            )


def _generate_reply_with_mock(trip: Trip, messages: list[TripMessage]) -> dict[str, Any]:
    latest_user = next((message for message in reversed(messages) if message.role == "user"), None)
    prompt = latest_user.content if latest_user else ""
    lowered = prompt.lower()

    missing = []
    if not trip.destination:
        missing.append("destination")
    if not trip.start_date or not trip.end_date:
        missing.append("dates")
    if "from " not in lowered and "flying from" not in lowered:
        missing.append("origin")
    if not any(keyword in lowered for keyword in INTEREST_KEYWORDS):
        missing.append("activities")

    if missing:
        prompts = {
            "destination": "Where are you headed?",
            "dates": "What dates are you considering?",
            "origin": "Where are you flying from?",
            "activities": "What do you want to do on this trip?",
        }
        question_text = " ".join(prompts[item] for item in missing[:3])
        return {
            "assistant_text": question_text,
            "tool_messages": [],
        }

    tool_messages: list[dict[str, Any]] = []

    flight_output = execute_tool(
        "search_flights",
        {
            "origin": _extract_origin(prompt) or "San Francisco",
            "destination": trip.destination or "Tokyo",
            "month": trip.start_date.strftime("%B") if trip.start_date else "March",
            "travelers": 1,
        },
    )
    tool_messages.append(
        {
            "content": flight_output,
            "tool_name": "search_flights",
            "tool_call_id": "mock-flight-call",
            "metadata": {"mock": True},
        }
    )

    hotel_output = execute_tool(
        "lookup_hotel",
        {
            "city": trip.destination or "Tokyo",
            "check_in": trip.start_date.isoformat() if trip.start_date else "2026-03-10",
            "nights": _night_count(trip),
            "rooms": 1,
        },
    )
    tool_messages.append(
        {
            "content": hotel_output,
            "tool_name": "lookup_hotel",
            "tool_call_id": "mock-hotel-call",
            "metadata": {"mock": True},
        }
    )

    weather_output = execute_tool(
        "get_weather",
        {
            "location": trip.destination or "Tokyo",
            "timeframe": (
                f"{trip.start_date.isoformat()} to {trip.end_date.isoformat()}"
                if trip.start_date and trip.end_date
                else "trip dates"
            ),
        },
    )
    tool_messages.append(
        {
            "content": weather_output,
            "tool_name": "get_weather",
            "tool_call_id": "mock-weather-call",
            "metadata": {"mock": True},
        }
    )

    plan_output = execute_tool(
        "update_trip_plan",
        {
            "title": trip.title,
            "summary": f"Built a first-pass plan for {trip.destination or 'the destination'} with flights, stay options, and activity guidance.",
            "next_step": "Confirm departure airport, budget, and top two activity preferences.",
        },
    )
    tool_messages.append(
        {
            "content": plan_output,
            "tool_name": "update_trip_plan",
            "tool_call_id": "mock-plan-call",
            "metadata": {"mock": True},
        }
    )

    return {
        "assistant_text": (
            f"I pulled together a first pass for {trip.destination or 'your trip'}: a flight option, a hotel option, "
            "and a weather-aware next step. If you want, I can narrow it down by budget or focus on specific activities."
        ),
        "tool_messages": tool_messages,
    }


def _extract_origin(text: str) -> str | None:
    marker = "from "
    lowered = text.lower()
    if marker not in lowered:
        return None
    start = lowered.index(marker) + len(marker)
    remainder = text[start:].strip()
    if not remainder:
        return None
    return remainder.split(",")[0].split(" and ")[0].split(" to ")[0].strip().title()


def _night_count(trip: Trip) -> int:
    if trip.start_date and trip.end_date:
        return max((trip.end_date - trip.start_date).days, 1)
    return 4
