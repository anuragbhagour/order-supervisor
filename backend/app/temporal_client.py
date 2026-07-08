from __future__ import annotations

from temporalio.client import Client

from app.config import get_settings


async def get_temporal_client() -> Client:
    settings = get_settings()
    return await Client.connect(settings.temporal_address, namespace=settings.temporal_namespace)
