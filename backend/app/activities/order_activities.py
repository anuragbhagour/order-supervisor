from __future__ import annotations

from typing import Any

from temporalio import activity

from app.agents.policy import classify_event as classify_event_policy
from app.agents.policy import run_agent as run_agent_policy
from app.db import get_store


@activity.defn
async def record_workflow_started(payload: dict[str, Any]) -> dict[str, Any]:
    store = get_store()
    store.update_run(payload["run_id"], {"status": "running", "sleep_state": "awake"})
    return store.add_activity(
        {
            "run_id": payload["run_id"],
            "activity_type": "workflow_started",
            "title": "Workflow started",
            "details": payload,
        }
    )


@activity.defn
async def record_incoming_event(payload: dict[str, Any]) -> dict[str, Any]:
    store = get_store()
    return store.add_activity(
        {
            "run_id": payload["run_id"],
            "activity_type": "incoming_event",
            "title": payload["event"].get("event_type", "event"),
            "details": payload["event"],
        }
    )


@activity.defn
async def classify_event(payload: dict[str, Any]) -> dict[str, Any]:
    decision = classify_event_policy(payload["event"], payload.get("wake_guidance", ""))
    get_store().add_activity(
        {
            "run_id": payload["run_id"],
            "activity_type": "wake_decision",
            "title": "Wake policy decision",
            "details": decision,
        }
    )
    return decision


@activity.defn
async def run_agent(payload: dict[str, Any]) -> dict[str, Any]:
    result = run_agent_policy(payload)
    get_store().add_activity(
        {
            "run_id": payload["run_id"],
            "activity_type": "agent_reasoning",
            "title": f"Agent pass: {payload['trigger']}",
            "details": {
                "reasoning": result["reasoning"],
                "sleep_minutes": result["sleep_minutes"],
                "next_wake_at": result["next_wake_at"],
            },
        }
    )
    return result


@activity.defn
async def record_business_action(payload: dict[str, Any]) -> dict[str, Any]:
    action = payload["action"]
    return get_store().add_activity(
        {
            "run_id": payload["run_id"],
            "activity_type": "business_action",
            "title": action["action_type"],
            "details": action,
        }
    )


@activity.defn
async def record_manual_instruction(payload: dict[str, Any]) -> dict[str, Any]:
    return get_store().add_activity(
        {
            "run_id": payload["run_id"],
            "activity_type": "manual_instruction",
            "title": "Additional instruction",
            "details": {"instruction": payload["instruction"]},
        }
    )


@activity.defn
async def update_run_state(payload: dict[str, Any]) -> dict[str, Any]:
    patch = {
        "status": payload.get("status", "running"),
        "sleep_state": payload.get("sleep_state", "sleeping"),
        "next_wake_at": payload.get("next_wake_at"),
        "memory_summary": payload.get("memory_summary"),
        "last_reasoning": payload.get("reasoning"),
        "final_output": payload.get("final_output"),
    }
    return get_store().update_run(payload["run_id"], patch)


@activity.defn
async def finalize_run(payload: dict[str, Any]) -> dict[str, Any]:
    patch = {
        "status": payload.get("status", "completed"),
        "sleep_state": "closed",
        "next_wake_at": None,
        "memory_summary": payload.get("memory_summary"),
        "final_output": payload.get("final_output"),
        "last_reasoning": payload.get("reasoning", "Workflow closed by lifecycle rule."),
    }
    store = get_store()
    updated = store.update_run(payload["run_id"], patch)
    store.add_activity(
        {
            "run_id": payload["run_id"],
            "activity_type": "final_output",
            "title": "Workflow finalized",
            "details": patch,
        }
    )
    return updated
