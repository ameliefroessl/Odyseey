from __future__ import annotations

from temporalio.client import Client

from .config import settings


async def get_temporal_client() -> Client:
    return await Client.connect(
        settings.temporal_address,
        namespace=settings.temporal_namespace,
    )
