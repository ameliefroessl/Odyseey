from __future__ import annotations

import asyncio
import uuid

from .config import settings
from .temporal_client import get_temporal_client
from .temporal_workflows import TripPlanningInput, TripPlanningWorkflow


async def main() -> None:
    client = await get_temporal_client()
    result = await client.execute_workflow(
        TripPlanningWorkflow.run,
        TripPlanningInput(
            trip_id=f"trip-{uuid.uuid4()}",
            message="Help me plan a Tokyo trip.",
        ),
        id=f"trip-planning-{uuid.uuid4()}",
        task_queue=settings.temporal_task_queue,
    )
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
