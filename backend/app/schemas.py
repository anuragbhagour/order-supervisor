from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


AVAILABLE_ACTIONS = [
    "message_fulfillment_team",
    "message_payments_team",
    "message_logistics_team",
    "message_customer",
    "create_internal_note",
]


class SupervisorCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str = "Default Order Supervisor"
    base_instruction: str = (
        "Oversee one order until completion. Wake for payment, fulfillment, logistics, "
        "customer, refund, and delivery risks. Prefer internal notes before customer contact."
    )
    available_actions: list[str] = Field(default_factory=lambda: AVAILABLE_ACTIONS.copy())
    default_wake_minutes: int = 30
    model_settings: dict[str, Any] = Field(default_factory=lambda: {"mode": "policy"}, alias="model_config")
    wake_guidance: str = "Wake immediately on failures, delays, customer messages, refunds, and terminal events."


class RunCreate(BaseModel):
    supervisor_id: str
    order_id: str
    order_context: dict[str, Any] = Field(default_factory=dict)
    extra_instruction: str | None = None


class RunEventCreate(BaseModel):
    event_type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    importance: Literal["low", "normal", "high"] = "normal"


class InstructionCreate(BaseModel):
    instruction: str


class RunControlResponse(BaseModel):
    ok: bool
    run_id: str
    message: str
