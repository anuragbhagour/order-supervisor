from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from supabase import Client, create_client

from app.config import get_settings


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


class SupabaseStore:
    def __init__(self) -> None:
        settings = get_settings()
        self.client: Client = create_client(settings.supabase_url, settings.supabase_service_role_key)

    def create_supervisor(self, payload: dict[str, Any]) -> dict[str, Any]:
        data = {
            **payload,
            "created_at": utc_now_iso(),
            "updated_at": utc_now_iso(),
        }
        return self.client.table("supervisors").insert(data).execute().data[0]

    def list_supervisors(self) -> list[dict[str, Any]]:
        return self.client.table("supervisors").select("*").order("created_at", desc=True).execute().data

    def get_supervisor(self, supervisor_id: str) -> dict[str, Any] | None:
        data = self.client.table("supervisors").select("*").eq("id", supervisor_id).limit(1).execute().data
        return data[0] if data else None

    def create_run(self, payload: dict[str, Any]) -> dict[str, Any]:
        data = {
            **payload,
            "status": payload.get("status", "starting"),
            "sleep_state": "awake",
            "memory_summary": "Run initialized. Awaiting first supervisor pass.",
            "created_at": utc_now_iso(),
            "updated_at": utc_now_iso(),
        }
        return self.client.table("runs").insert(data).execute().data[0]

    def list_runs(self) -> list[dict[str, Any]]:
        return self.client.table("runs").select("*").order("created_at", desc=True).execute().data

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        data = self.client.table("runs").select("*").eq("id", run_id).limit(1).execute().data
        return data[0] if data else None

    def update_run(self, run_id: str, patch: dict[str, Any]) -> dict[str, Any]:
        data = {**patch, "updated_at": utc_now_iso()}
        return self.client.table("runs").update(data).eq("id", run_id).execute().data[0]

    def add_activity(self, payload: dict[str, Any]) -> dict[str, Any]:
        data = {**payload, "created_at": utc_now_iso()}
        return self.client.table("activity_log").insert(data).execute().data[0]

    def list_activities(self, run_id: str) -> list[dict[str, Any]]:
        return (
            self.client.table("activity_log")
            .select("*")
            .eq("run_id", run_id)
            .order("created_at")
            .execute()
            .data
        )


_store: SupabaseStore | None = None


def get_store() -> SupabaseStore:
    global _store
    if _store is None:
        _store = SupabaseStore()
    return _store
