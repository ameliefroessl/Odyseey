from __future__ import annotations

import asyncio

from temporalio.worker import Worker

from .config import settings
from .temporal_activities import draft_trip_follow_up
from .temporal_client import get_temporal_client
from .temporal_workflows import TripPlanningWorkflow


async def main() -> None:
    client = await get_temporal_client()
    worker = Worker(
        client,
        task_queue=settings.temporal_task_queue,
        workflows=[TripPlanningWorkflow],
        activities=[draft_trip_follow_up],
    )
    print(
        "Temporal worker listening",
        {
            "address": settings.temporal_address,
            "namespace": settings.temporal_namespace,
            "task_queue": settings.temporal_task_queue,
        },
    )
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
