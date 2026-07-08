from __future__ import annotations

import asyncio

from temporalio.worker import Worker

from app.activities.order_activities import (
    classify_event,
    finalize_run,
    record_business_action,
    record_incoming_event,
    record_manual_instruction,
    record_workflow_started,
    run_agent,
    update_run_state,
)
from app.config import get_settings
from app.temporal_client import get_temporal_client
from app.workflows.order_supervisor import OrderSupervisorWorkflow


async def main() -> None:
    settings = get_settings()
    client = await get_temporal_client()
    worker = Worker(
        client,
        task_queue=settings.temporal_task_queue,
        workflows=[OrderSupervisorWorkflow],
        activities=[
            record_workflow_started,
            record_incoming_event,
            classify_event,
            run_agent,
            record_business_action,
            record_manual_instruction,
            update_run_state,
            finalize_run,
        ],
    )
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
