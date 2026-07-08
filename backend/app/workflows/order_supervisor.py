from __future__ import annotations

import asyncio
from datetime import timedelta
from typing import Any

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
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


TERMINAL_EVENTS = {"delivered", "cancelled", "refunded"}
MAX_RUN_ITERATIONS = 500


@workflow.defn
class OrderSupervisorWorkflow:
    def __init__(self) -> None:
        self.run_id = ""
        self.order_id = ""
        self.supervisor: dict[str, Any] = {}
        self.order_context: dict[str, Any] = {}
        self.memory_summary = ""
        self.instructions: list[str] = []
        self.event_queue: list[dict[str, Any]] = []
        self.paused = False
        self.terminated = False
        self.completed = False
        self.next_wake_minutes = 30
        self.last_reasoning = ""
        self.final_output: dict[str, Any] | None = None

    @workflow.run
    async def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.run_id = payload["run_id"]
        self.order_id = payload["order_id"]
        self.supervisor = payload["supervisor"]
        self.order_context = payload.get("order_context", {})
        self.instructions = [payload["extra_instruction"]] if payload.get("extra_instruction") else []
        self.next_wake_minutes = int(self.supervisor.get("default_wake_minutes") or 30)

        await workflow.execute_activity(
            record_workflow_started,
            payload,
            start_to_close_timeout=timedelta(seconds=20),
        )
        await self._agent_pass("workflow_start")

        iterations = 0
        while not self.completed and not self.terminated and iterations < MAX_RUN_ITERATIONS:
            iterations += 1
            if self.paused:
                await workflow.wait_condition(lambda: self.terminated or not self.paused)
                continue

            try:
                await workflow.wait_condition(
                    lambda: self.terminated or self.paused or len(self.event_queue) > 0,
                    timeout=timedelta(minutes=max(self.next_wake_minutes, 1)),
                    timeout_summary="next-agent-review",
                )
            except asyncio.TimeoutError:
                pass

            if self.terminated or self.paused:
                continue

            if self.event_queue:
                event = self.event_queue.pop(0)
                await self._handle_event(event)
            else:
                await self._agent_pass("scheduled_wake")

        if self.terminated:
            self.final_output = {
                "summary": "Workflow was manually terminated.",
                "important_actions": "Review activity log for actions before termination.",
                "key_learnings": "Manual termination is treated as a workflow-owned lifecycle rule.",
                "feedback": "Use pause/resume for temporary holds; terminate only when the order no longer needs supervision.",
            }
            await self._finalize("terminated")
        elif iterations >= MAX_RUN_ITERATIONS:
            self.final_output = {
                "summary": "Workflow reached the configured maximum iteration count.",
                "important_actions": "Review activity log for the long-running history.",
                "key_learnings": "Very long histories should use continue-as-new in production.",
                "feedback": "Lower wake frequency or add stronger completion rules for this order class.",
            }
            await self._finalize("completed")

        return {"run_id": self.run_id, "status": "closed", "final_output": self.final_output}

    @workflow.signal
    async def add_event(self, event: dict[str, Any]) -> None:
        self.event_queue.append(event)

    @workflow.signal
    async def add_instruction(self, instruction: str) -> None:
        self.instructions.append(instruction)
        await workflow.execute_activity(
            record_manual_instruction,
            {"run_id": self.run_id, "instruction": instruction},
            start_to_close_timeout=timedelta(seconds=20),
        )
        await self._agent_pass("manual_instruction")

    @workflow.signal
    async def pause(self) -> None:
        self.paused = True
        await workflow.execute_activity(
            update_run_state,
            {"run_id": self.run_id, "status": "paused", "sleep_state": "paused", "memory_summary": self.memory_summary},
            start_to_close_timeout=timedelta(seconds=20),
        )

    @workflow.signal
    async def resume(self) -> None:
        self.paused = False
        await workflow.execute_activity(
            update_run_state,
            {"run_id": self.run_id, "status": "running", "sleep_state": "awake", "memory_summary": self.memory_summary},
            start_to_close_timeout=timedelta(seconds=20),
        )

    @workflow.signal
    async def terminate(self) -> None:
        self.terminated = True

    async def _handle_event(self, event: dict[str, Any]) -> None:
        await workflow.execute_activity(
            record_incoming_event,
            {"run_id": self.run_id, "event": event},
            start_to_close_timeout=timedelta(seconds=20),
        )
        decision = await workflow.execute_activity(
            classify_event,
            {
                "run_id": self.run_id,
                "event": event,
                "wake_guidance": self.supervisor.get("wake_guidance", ""),
            },
            start_to_close_timeout=timedelta(seconds=20),
        )
        if decision.get("should_wake"):
            await self._agent_pass("signal", event)
        if event.get("event_type") in TERMINAL_EVENTS:
            self.completed = True
            if not self.final_output:
                await self._agent_pass("signal", event)
            await self._finalize("completed")

    async def _agent_pass(self, trigger: str, event: dict[str, Any] | None = None) -> None:
        result = await workflow.execute_activity(
            run_agent,
            {
                "run_id": self.run_id,
                "order_id": self.order_id,
                "trigger": trigger,
                "event": event,
                "order_context": self.order_context,
                "base_instruction": self.supervisor.get("base_instruction", ""),
                "available_actions": self.supervisor.get("available_actions", []),
                "default_wake_minutes": self.supervisor.get("default_wake_minutes", 30),
                "instructions": self.instructions,
                "memory_summary": self.memory_summary,
            },
            start_to_close_timeout=timedelta(seconds=30),
        )
        self.memory_summary = result["memory_summary"]
        self.next_wake_minutes = int(result.get("sleep_minutes") or 30)
        self.last_reasoning = result.get("reasoning", "")
        self.final_output = result.get("final_output") or self.final_output

        for action in result.get("actions", []):
            await workflow.execute_activity(
                record_business_action,
                {"run_id": self.run_id, "action": action},
                start_to_close_timeout=timedelta(seconds=20),
            )

        if result.get("status") == "completed":
            self.completed = True

        await workflow.execute_activity(
            update_run_state,
            {
                "run_id": self.run_id,
                "status": "completed" if self.completed else "running",
                "sleep_state": "closed" if self.completed else "sleeping",
                "next_wake_at": None if self.completed else result.get("next_wake_at"),
                "memory_summary": self.memory_summary,
                "reasoning": self.last_reasoning,
                "final_output": self.final_output,
            },
            start_to_close_timeout=timedelta(seconds=20),
        )

    async def _finalize(self, status: str) -> None:
        await workflow.execute_activity(
            finalize_run,
            {
                "run_id": self.run_id,
                "status": status,
                "memory_summary": self.memory_summary,
                "final_output": self.final_output,
                "reasoning": self.last_reasoning,
            },
            start_to_close_timeout=timedelta(seconds=20),
        )
