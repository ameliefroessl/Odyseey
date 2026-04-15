from __future__ import annotations

import json
from typing import Any

from .config import settings
from .models import Trip, TripMessage
from .tools import execute_tool, get_weather, lookup_hotel, search_flights, tool_definitions, update_trip_plan

SYSTEM_PROMPT = """
You are a travel planning agent for a collaborative trip app.
Your personality is sharp, practical, and mildly cynical about travel prices.
Assume most travel options are annoyingly expensive unless proven otherwise.
Be helpful, not rude: call out overpriced options, steer people toward better value,
and sound like a competent friend who refuses to romanticize bad deals.
Ask concise follow-up questions when essential trip details are missing.
Prefer at most 2 short questions at a time.
Once you know enough, use tools to propose useful options.
When you answer, be concrete:
- mention the cheapest or best-value option first
- call out anything expensive or wasteful
- end with one clear next step
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

BUDGET_KEYWORDS = {
    "budget",
    "cheap",
    "cheapest",
    "affordable",
    "expensive",
    "luxury",
    "premium",
    "balling",
    "splurge",
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
    if not any(keyword in lowered for keyword in BUDGET_KEYWORDS):
        missing.append("budget")

    if missing:
        prompts = {
            "destination": "Where are you headed?",
            "dates": "What dates are you considering?",
            "origin": "Where are you flying from?",
            "activities": "What do you actually want to do on this trip?",
            "budget": "What budget are we pretending is reasonable here?",
        }
        question_text = " ".join(prompts[item] for item in missing[:3])
        return {
            "assistant_text": question_text,
            "tool_messages": [],
        }

    tool_messages: list[dict[str, Any]] = []

    flight_data = search_flights(
        origin=_extract_origin(prompt) or "San Francisco",
        destination=trip.destination or "Tokyo",
        month=trip.start_date.strftime("%B") if trip.start_date else "March",
        travelers=1,
    )
    flight_output = json.dumps(flight_data)
    tool_messages.append(
        {
            "content": flight_output,
            "tool_name": "search_flights",
            "tool_call_id": "mock-flight-call",
            "metadata": {"mock": True},
        }
    )

    hotel_data = lookup_hotel(
        city=trip.destination or "Tokyo",
        check_in=trip.start_date.isoformat() if trip.start_date else "2026-03-10",
        nights=_night_count(trip),
        rooms=1,
    )
    hotel_output = json.dumps(hotel_data)
    tool_messages.append(
        {
            "content": hotel_output,
            "tool_name": "lookup_hotel",
            "tool_call_id": "mock-hotel-call",
            "metadata": {"mock": True},
        }
    )

    weather_data = get_weather(
        location=trip.destination or "Tokyo",
        timeframe=(
            f"{trip.start_date.isoformat()} to {trip.end_date.isoformat()}"
            if trip.start_date and trip.end_date
            else "trip dates"
        ),
    )
    weather_output = json.dumps(weather_data)
    tool_messages.append(
        {
            "content": weather_output,
            "tool_name": "get_weather",
            "tool_call_id": "mock-weather-call",
            "metadata": {"mock": True},
        }
    )

    cheapest_flight = min(flight_data["options"], key=lambda option: option["price_usd"])
    best_value_hotel = min(hotel_data["options"], key=lambda option: option["nightly_rate_usd"])

    plan_data = update_trip_plan(
        title=trip.title,
        summary=(
            f"Built a first-pass plan for {trip.destination or 'the destination'} with a cheaper flight angle, "
            f"a sane hotel option, and weather notes so nobody packs like an optimist."
        ),
        next_step="Confirm total budget, deal-breakers, and whether you want cheapest or least painful.",
    )
    plan_output = json.dumps(plan_data)
    tool_messages.append(
        {
            "content": plan_output,
            "tool_name": "update_trip_plan",
            "tool_call_id": "mock-plan-call",
            "metadata": {"mock": True},
        }
    )

    return {
        "assistant_text": _build_mock_summary(
            destination=trip.destination or "your destination",
            cheapest_flight=cheapest_flight,
            best_value_hotel=best_value_hotel,
            weather_data=weather_data,
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


def _build_mock_summary(
    *,
    destination: str,
    cheapest_flight: dict[str, Any],
    best_value_hotel: dict[str, Any],
    weather_data: dict[str, Any],
) -> str:
    flight_price = cheapest_flight["price_usd"]
    hotel_price = best_value_hotel["nightly_rate_usd"]
    flight_tone = "still annoyingly expensive" if flight_price >= 600 else "not completely insulting"
    hotel_tone = "which is at least vaguely defensible" if hotel_price < 170 else "which is honestly pushing it"

    return (
        f"For {destination}, the least offensive flight I found is {cheapest_flight['airline']} at ${flight_price} "
        f"with {cheapest_flight['stops']} stop(s), which is {flight_tone}. "
        f"Hotel-wise, {best_value_hotel['name']} is ${hotel_price}/night in {best_value_hotel['neighborhood']}, "
        f"{hotel_tone}. Weather looks like {weather_data['forecast_summary'].lower()} "
        f"Next step: tell me your real budget and I’ll cut the overpriced nonsense."
    )
