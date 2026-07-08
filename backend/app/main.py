from __future__ import annotations

from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.db import get_store
from app.schemas import InstructionCreate, RunCreate, RunControlResponse, RunEventCreate, SupervisorCreate
from app.temporal_client import get_temporal_client
from app.workflows.order_supervisor import OrderSupervisorWorkflow

app = FastAPI(title="Order Supervisor API")

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"ok": "true"}


@app.post("/api/supervisors")
async def create_supervisor(payload: SupervisorCreate) -> dict:
    data = payload.model_dump(by_alias=True)
    data["id"] = str(uuid4())
    return get_store().create_supervisor(data)


@app.get("/api/supervisors")
async def list_supervisors() -> list[dict]:
    return get_store().list_supervisors()


@app.get("/api/supervisors/{supervisor_id}")
async def get_supervisor(supervisor_id: str) -> dict:
    supervisor = get_store().get_supervisor(supervisor_id)
    if not supervisor:
        raise HTTPException(status_code=404, detail="Supervisor not found")
    return supervisor


@app.post("/api/runs")
async def create_run(payload: RunCreate) -> dict:
    store = get_store()
    supervisor = store.get_supervisor(payload.supervisor_id)
    if not supervisor:
        raise HTTPException(status_code=404, detail="Supervisor not found")

    run_id = str(uuid4())
    run = store.create_run(
        {
            "id": run_id,
            "supervisor_id": payload.supervisor_id,
            "order_id": payload.order_id,
            "order_context": payload.order_context,
            "extra_instructions": [payload.extra_instruction] if payload.extra_instruction else [],
        }
    )

    client = await get_temporal_client()
    await client.start_workflow(
        OrderSupervisorWorkflow.run,
        {
            "run_id": run_id,
            "order_id": payload.order_id,
            "supervisor": supervisor,
            "order_context": payload.order_context,
            "extra_instruction": payload.extra_instruction,
        },
        id=f"order-supervisor-{run_id}",
        task_queue=settings.temporal_task_queue,
    )
    return run


@app.get("/api/runs")
async def list_runs() -> list[dict]:
    return get_store().list_runs()


@app.get("/api/runs/{run_id}")
async def get_run(run_id: str) -> dict:
    store = get_store()
    run = store.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    run["activities"] = store.list_activities(run_id)
    return run


@app.post("/api/runs/{run_id}/events", response_model=RunControlResponse)
async def add_event(run_id: str, payload: RunEventCreate) -> RunControlResponse:
    await _signal(run_id, "add_event", payload.model_dump())
    return RunControlResponse(ok=True, run_id=run_id, message="Event signaled to workflow")


@app.post("/api/runs/{run_id}/instructions", response_model=RunControlResponse)
async def add_instruction(run_id: str, payload: InstructionCreate) -> RunControlResponse:
    run = get_store().get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    instructions = list(run.get("extra_instructions") or [])
    instructions.append(payload.instruction)
    get_store().update_run(run_id, {"extra_instructions": instructions})
    await _signal(run_id, "add_instruction", payload.instruction)
    return RunControlResponse(ok=True, run_id=run_id, message="Instruction added")


@app.post("/api/runs/{run_id}/interrupt", response_model=RunControlResponse)
async def pause_run(run_id: str) -> RunControlResponse:
    await _signal(run_id, "pause")
    return RunControlResponse(ok=True, run_id=run_id, message="Run paused")


@app.post("/api/runs/{run_id}/resume", response_model=RunControlResponse)
async def resume_run(run_id: str) -> RunControlResponse:
    await _signal(run_id, "resume")
    return RunControlResponse(ok=True, run_id=run_id, message="Run resumed")


@app.post("/api/runs/{run_id}/terminate", response_model=RunControlResponse)
async def terminate_run(run_id: str) -> RunControlResponse:
    await _signal(run_id, "terminate")
    return RunControlResponse(ok=True, run_id=run_id, message="Run terminating")


async def _signal(run_id: str, signal_name: str, arg: object | None = None) -> None:
    if not get_store().get_run(run_id):
        raise HTTPException(status_code=404, detail="Run not found")
    client = await get_temporal_client()
    handle = client.get_workflow_handle(f"order-supervisor-{run_id}")
    if arg is None:
        await handle.signal(signal_name)
    else:
        await handle.signal(signal_name, arg)
