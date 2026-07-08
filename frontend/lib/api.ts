export const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8000";

export type Supervisor = {
  id: string;
  name: string;
  base_instruction: string;
  available_actions: string[];
  default_wake_minutes: number;
  wake_guidance: string;
};

export type Activity = {
  id: string;
  run_id: string;
  activity_type: string;
  title: string;
  details: Record<string, unknown>;
  created_at: string;
};

export type Run = {
  id: string;
  supervisor_id: string;
  order_id: string;
  status: string;
  sleep_state: string;
  next_wake_at?: string | null;
  memory_summary?: string | null;
  last_reasoning?: string | null;
  final_output?: Record<string, unknown> | null;
  order_context?: Record<string, unknown>;
  extra_instructions?: string[];
  activities?: Activity[];
  created_at: string;
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers || {}),
    },
    cache: "no-store",
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || response.statusText);
  }
  return response.json();
}

export const api = {
  supervisors: () => request<Supervisor[]>("/api/supervisors"),
  createSupervisor: (body: Partial<Supervisor>) =>
    request<Supervisor>("/api/supervisors", { method: "POST", body: JSON.stringify(body) }),
  runs: () => request<Run[]>("/api/runs"),
  run: (id: string) => request<Run>(`/api/runs/${id}`),
  createRun: (body: { supervisor_id: string; order_id: string; order_context: Record<string, unknown>; extra_instruction?: string }) =>
    request<Run>("/api/runs", { method: "POST", body: JSON.stringify(body) }),
  event: (runId: string, body: { event_type: string; importance: string; payload: Record<string, unknown> }) =>
    request(`/api/runs/${runId}/events`, { method: "POST", body: JSON.stringify(body) }),
  instruction: (runId: string, instruction: string) =>
    request(`/api/runs/${runId}/instructions`, { method: "POST", body: JSON.stringify({ instruction }) }),
  control: (runId: string, action: "interrupt" | "resume" | "terminate") =>
    request(`/api/runs/${runId}/${action}`, { method: "POST" }),
};
