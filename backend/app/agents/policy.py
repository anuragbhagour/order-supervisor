from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

TERMINAL_EVENTS = {"delivered", "cancelled", "refunded"}
IMPORTANT_EVENTS = {
    "payment_failed",
    "shipment_delayed",
    "refund_requested",
    "customer_message_received",
    "no_update_for_n_hours",
    "delivered",
}


def classify_event(event: dict[str, Any], wake_guidance: str = "") -> dict[str, Any]:
    event_type = event.get("event_type", "")
    importance = event.get("importance", "normal")
    should_wake = event_type in IMPORTANT_EVENTS or importance == "high"
    reason = "Matches wake policy" if should_wake else "Stored for next scheduled review"
    return {"should_wake": should_wake, "reason": reason, "wake_guidance_used": wake_guidance}


def run_agent(state: dict[str, Any]) -> dict[str, Any]:
    trigger = state["trigger"]
    event = state.get("event") or {}
    event_type = event.get("event_type", trigger)
    instructions = state.get("instructions", [])
    memory_summary = state.get("memory_summary") or ""
    order_id = state.get("order_id")
    default_wake_minutes = int(state.get("default_wake_minutes") or 30)

    actions: list[dict[str, Any]] = []
    reasoning = f"Reviewed order {order_id} because of {trigger}."
    final_output = None
    status = "running"
    sleep_minutes = default_wake_minutes

    if trigger == "workflow_start":
        actions.append(_note("Supervisor started and baseline order context captured."))
        reasoning = "Initial pass completed; no risk yet, so the workflow can sleep on the default cadence."
    elif event_type == "payment_failed":
        actions.append(_action("message_payments_team", "Payment failed. Please investigate and advise recovery options."))
        actions.append(_note("Payment failure requires immediate payments-team review."))
        sleep_minutes = 10
    elif event_type == "payment_confirmed":
        actions.append(_note("Payment confirmed. Continue monitoring fulfillment."))
    elif event_type == "shipment_created":
        actions.append(_action("message_fulfillment_team", "Shipment was created. Confirm handoff and tracking readiness."))
    elif event_type == "shipment_delayed":
        actions.append(_action("message_logistics_team", "Shipment delayed. Please provide ETA and mitigation plan."))
        if _allows_customer_contact(instructions):
            actions.append(_action("message_customer", "Your shipment is delayed. We are checking the ETA and will update you soon."))
        actions.append(_note("Delay detected; logistics follow-up scheduled."))
        sleep_minutes = 15
    elif event_type == "customer_message_received":
        actions.append(_note(f"Customer message received: {event.get('payload', {}).get('message', 'No message text provided')}"))
        if _allows_customer_contact(instructions):
            actions.append(_action("message_customer", "Thanks for reaching out. We are reviewing your order and will follow up shortly."))
        sleep_minutes = 10
    elif event_type == "refund_requested":
        actions.append(_action("message_payments_team", "Refund requested. Review payment status and refund eligibility."))
        actions.append(_note("Refund request needs payments review before closure."))
        sleep_minutes = 10
    elif event_type == "no_update_for_n_hours":
        actions.append(_action("message_fulfillment_team", "No recent order update. Please confirm current status."))
        sleep_minutes = 20
    elif event_type == "delivered":
        status = "completed"
        actions.append(_note("Terminal delivery event received. Preparing final summary."))
        final_output = _final_summary(memory_summary, "Order delivered successfully.")
    elif trigger == "scheduled_wake":
        actions.append(_note("Scheduled review completed. No new high-risk signal found."))
    elif trigger == "manual_instruction":
        actions.append(_note("Run-specific instruction added and incorporated into future decisions."))

    if status != "completed" and _instruction_requires_speed(instructions):
        sleep_minutes = min(sleep_minutes, 10)

    next_wake_at = datetime.now(UTC) + timedelta(minutes=sleep_minutes)
    updated_memory = compact_memory(memory_summary, event_type, reasoning, actions)

    return {
        "reasoning": reasoning,
        "actions": actions,
        "memory_summary": updated_memory,
        "sleep_minutes": sleep_minutes,
        "next_wake_at": next_wake_at.isoformat(),
        "status": status,
        "final_output": final_output,
    }


def compact_memory(memory_summary: str, event_type: str, reasoning: str, actions: list[dict[str, Any]]) -> str:
    action_names = ", ".join(action["action_type"] for action in actions) or "no actions"
    new_line = f"{datetime.now(UTC).strftime('%Y-%m-%d %H:%M')} UTC: {event_type}; {reasoning}; actions: {action_names}."
    lines = [line for line in (memory_summary or "").split("\n") if line.strip()]
    lines.append(new_line)
    return "\n".join(lines[-8:])


def _action(action_type: str, message: str) -> dict[str, Any]:
    return {"action_type": action_type, "message": message}


def _note(message: str) -> dict[str, Any]:
    return {"action_type": "create_internal_note", "message": message}


def _allows_customer_contact(instructions: list[str]) -> bool:
    joined = " ".join(instructions).lower()
    return "do not contact the customer" not in joined and "without human review" not in joined


def _instruction_requires_speed(instructions: list[str]) -> bool:
    joined = " ".join(instructions).lower()
    return "prioritize speed" in joined or "speed over cost" in joined


def _final_summary(memory_summary: str, completion_reason: str) -> dict[str, Any]:
    return {
        "summary": completion_reason,
        "important_actions": "See activity log for all business actions and internal notes.",
        "key_learnings": "Risky order events should wake the workflow immediately; routine updates can wait for scheduled review.",
        "feedback": "Tune wake guidance based on which events caused useful interventions during the run.",
        "memory_snapshot": memory_summary,
    }
