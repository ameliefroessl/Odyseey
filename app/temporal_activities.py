from __future__ import annotations

from temporalio import activity


@activity.defn
async def draft_trip_follow_up(message: str) -> dict[str, object]:
    lowered = message.lower()
    missing = []

    if "from " not in lowered and "flying from" not in lowered:
        missing.append("origin")
    if "march" not in lowered and "april" not in lowered and "date" not in lowered:
        missing.append("dates")
    if "food" not in lowered and "museum" not in lowered and "shopping" not in lowered and "activity" not in lowered:
        missing.append("interests")

    if missing:
        return {
            "needs_follow_up": True,
            "missing_fields": missing,
            "message": (
                "Before I search, tell me where you're flying from, what dates you're considering, "
                "and what kinds of activities you want."
            ),
        }

    return {
        "needs_follow_up": False,
        "missing_fields": [],
        "message": (
            "I have enough detail to start planning. Next I would search flights, hotels, and "
            "activities through the tool layer."
        ),
    }
