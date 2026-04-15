from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from .temporal_activities import draft_trip_follow_up


@dataclass
class TripPlanningInput:
    trip_id: str
    message: str


@workflow.defn
class TripPlanningWorkflow:
    @workflow.run
    async def run(self, payload: TripPlanningInput) -> dict[str, object]:
        return await workflow.execute_activity(
            draft_trip_follow_up,
            payload.message,
            schedule_to_close_timeout=timedelta(seconds=30),
        )
