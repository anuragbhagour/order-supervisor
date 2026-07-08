"use client";

import { useEffect, useMemo, useState } from "react";
import { Bell, CheckCircle2, ClipboardList, Pause, Play, Plus, RefreshCw, Send, Square, Zap } from "lucide-react";
import { Activity, Run, Supervisor, api } from "@/lib/api";

const eventTypes = [
  "order_created",
  "payment_confirmed",
  "payment_failed",
  "shipment_created",
  "shipment_delayed",
  "delivered",
  "refund_requested",
  "customer_message_received",
  "no_update_for_n_hours",
];

export default function Home() {
  const [supervisors, setSupervisors] = useState<Supervisor[]>([]);
  const [runs, setRuns] = useState<Run[]>([]);
  const [selectedRunId, setSelectedRunId] = useState<string>("");
  const [selectedRun, setSelectedRun] = useState<Run | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [supervisorName, setSupervisorName] = useState("Default Order Supervisor");
  const [baseInstruction, setBaseInstruction] = useState("Watch payment, fulfillment, logistics, customer, refund, and delivery risks.");
  const [wakeMinutes, setWakeMinutes] = useState(30);
  const [orderId, setOrderId] = useState(`ORD-${Math.floor(Math.random() * 9000 + 1000)}`);
  const [eventType, setEventType] = useState("shipment_delayed");
  const [eventPayload, setEventPayload] = useState('{"message":"Shipment missed carrier pickup"}');
  const [instruction, setInstruction] = useState("If shipment is delayed, escalate immediately.");

  const activeSupervisor = supervisors[0];
  const statusCounts = useMemo(() => ({
    active: runs.filter((run) => ["running", "starting", "paused"].includes(run.status)).length,
    complete: runs.filter((run) => ["completed", "terminated"].includes(run.status)).length,
  }), [runs]);

  async function refresh(id = selectedRunId) {
    setError("");
    const [supervisorData, runData] = await Promise.all([api.supervisors(), api.runs()]);
    setSupervisors(supervisorData);
    setRuns(runData);
    const nextId = id || runData[0]?.id || "";
    setSelectedRunId(nextId);
    if (nextId) setSelectedRun(await api.run(nextId));
  }

  useEffect(() => {
    refresh().catch((err) => setError(err.message));
  }, []);

  async function createSupervisor() {
    await runBusy(async () => {
      await api.createSupervisor({
        name: supervisorName,
        base_instruction: baseInstruction,
        default_wake_minutes: wakeMinutes,
        wake_guidance: "Wake immediately on payment failures, shipment delays, refunds, customer messages, stale orders, and delivery.",
        available_actions: [
          "message_fulfillment_team",
          "message_payments_team",
          "message_logistics_team",
          "message_customer",
          "create_internal_note",
        ],
      });
      await refresh();
    });
  }

  async function createRun() {
    if (!activeSupervisor) {
      setError("Create a supervisor first.");
      return;
    }
    await runBusy(async () => {
      const run = await api.createRun({
        supervisor_id: activeSupervisor.id,
        order_id: orderId,
        order_context: { channel: "demo", priority: "standard" },
      });
      await refresh(run.id);
    });
  }

  async function sendEvent() {
    if (!selectedRunId) return;
    await runBusy(async () => {
      await api.event(selectedRunId, {
        event_type: eventType,
        importance: ["payment_failed", "shipment_delayed", "refund_requested"].includes(eventType) ? "high" : "normal",
        payload: safeJson(eventPayload),
      });
      await refresh(selectedRunId);
    });
  }

  async function addInstruction() {
    if (!selectedRunId || !instruction.trim()) return;
    await runBusy(async () => {
      await api.instruction(selectedRunId, instruction);
      await refresh(selectedRunId);
    });
  }

  async function control(action: "interrupt" | "resume" | "terminate") {
    if (!selectedRunId) return;
    await runBusy(async () => {
      await api.control(selectedRunId, action);
      await refresh(selectedRunId);
    });
  }

  async function runBusy(fn: () => Promise<void>) {
    setBusy(true);
    setError("");
    try {
      await fn();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Request failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="min-h-screen">
      <section className="border-b border-line bg-[#f7f7f4]">
        <div className="mx-auto flex max-w-7xl flex-col gap-4 px-5 py-5 md:flex-row md:items-center md:justify-between">
          <div>
            <h1 className="text-2xl font-semibold tracking-normal text-ink">Order Supervisor</h1>
            <p className="mt-1 text-sm text-gray-600">Temporal workflow per order, Supabase activity log, event-driven agent wake and sleep.</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Stat label="Active" value={statusCounts.active} />
            <Stat label="Closed" value={statusCounts.complete} />
            <button className="icon-button" onClick={() => refresh()} disabled={busy} title="Refresh">
              <RefreshCw size={17} />
            </button>
          </div>
        </div>
      </section>

      <div className="mx-auto grid max-w-7xl gap-4 px-5 py-5 lg:grid-cols-[360px_1fr]">
        <aside className="space-y-4">
          <Panel title="Supervisor Template" icon={<ClipboardList size={18} />}>
            <label className="field-label">Name</label>
            <input className="field" value={supervisorName} onChange={(e) => setSupervisorName(e.target.value)} />
            <label className="field-label">Base instruction</label>
            <textarea className="field min-h-24" value={baseInstruction} onChange={(e) => setBaseInstruction(e.target.value)} />
            <label className="field-label">Default wake minutes</label>
            <input className="field" type="number" min={1} value={wakeMinutes} onChange={(e) => setWakeMinutes(Number(e.target.value))} />
            <button className="primary-button" onClick={createSupervisor} disabled={busy}>
              <Plus size={16} /> Save template
            </button>
          </Panel>

          <Panel title="Start Run" icon={<Zap size={18} />}>
            <label className="field-label">Order ID</label>
            <input className="field" value={orderId} onChange={(e) => setOrderId(e.target.value)} />
            <button className="primary-button" onClick={createRun} disabled={busy || !activeSupervisor}>
              <Play size={16} /> Start workflow
            </button>
          </Panel>

          <Panel title="Runs" icon={<Bell size={18} />}>
            <div className="max-h-80 space-y-2 overflow-auto pr-1 scrollbar-thin">
              {runs.map((run) => (
                <button
                  key={run.id}
                  className={`run-row ${run.id === selectedRunId ? "run-row-active" : ""}`}
                  onClick={() => refresh(run.id)}
                >
                  <span className="font-medium">{run.order_id}</span>
                  <span className="text-xs text-gray-600">{run.status} · {run.sleep_state}</span>
                </button>
              ))}
              {runs.length === 0 && <p className="text-sm text-gray-600">No runs yet.</p>}
            </div>
          </Panel>
        </aside>

        <section className="space-y-4">
          {error && <div className="border border-risk bg-red-50 px-4 py-3 text-sm text-risk">{error}</div>}
          <div className="grid gap-4 xl:grid-cols-[1fr_360px]">
            <Panel title={selectedRun ? `Run ${selectedRun.order_id}` : "Run Detail"} icon={<CheckCircle2 size={18} />}>
              {selectedRun ? (
                <div className="space-y-4">
                  <div className="grid gap-3 sm:grid-cols-4">
                    <Meta label="Status" value={selectedRun.status} />
                    <Meta label="Sleep" value={selectedRun.sleep_state} />
                    <Meta label="Next Wake" value={formatDate(selectedRun.next_wake_at)} />
                    <Meta label="Activities" value={String(selectedRun.activities?.length || 0)} />
                  </div>
                  <div>
                    <h3 className="section-label">Memory Summary</h3>
                    <pre className="summary-box">{selectedRun.memory_summary || "No memory yet."}</pre>
                  </div>
                  {selectedRun.final_output && (
                    <div>
                      <h3 className="section-label">Final Output</h3>
                      <pre className="summary-box">{JSON.stringify(selectedRun.final_output, null, 2)}</pre>
                    </div>
                  )}
                  <ActivityList activities={selectedRun.activities || []} />
                </div>
              ) : (
                <p className="text-sm text-gray-600">Select or start a run.</p>
              )}
            </Panel>

            <div className="space-y-4">
              <Panel title="Event Generator" icon={<Send size={18} />}>
                <label className="field-label">Event type</label>
                <select className="field" value={eventType} onChange={(e) => setEventType(e.target.value)}>
                  {eventTypes.map((type) => <option key={type}>{type}</option>)}
                </select>
                <label className="field-label">Payload JSON</label>
                <textarea className="field min-h-24" value={eventPayload} onChange={(e) => setEventPayload(e.target.value)} />
                <button className="primary-button" onClick={sendEvent} disabled={busy || !selectedRunId}>
                  <Send size={16} /> Inject event
                </button>
              </Panel>

              <Panel title="Live Instruction" icon={<Plus size={18} />}>
                <textarea className="field min-h-24" value={instruction} onChange={(e) => setInstruction(e.target.value)} />
                <button className="primary-button" onClick={addInstruction} disabled={busy || !selectedRunId}>
                  <Plus size={16} /> Add instruction
                </button>
              </Panel>

              <Panel title="Workflow Controls" icon={<Pause size={18} />}>
                <div className="grid grid-cols-3 gap-2">
                  <button className="secondary-button" onClick={() => control("interrupt")} disabled={busy || !selectedRunId} title="Pause">
                    <Pause size={16} />
                  </button>
                  <button className="secondary-button" onClick={() => control("resume")} disabled={busy || !selectedRunId} title="Resume">
                    <Play size={16} />
                  </button>
                  <button className="danger-button" onClick={() => control("terminate")} disabled={busy || !selectedRunId} title="Terminate">
                    <Square size={16} />
                  </button>
                </div>
              </Panel>
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}

function Panel({ title, icon, children }: { title: string; icon: React.ReactNode; children: React.ReactNode }) {
  return (
    <div className="border border-line bg-panel p-4">
      <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-ink">
        {icon}
        <h2>{title}</h2>
      </div>
      <div className="space-y-3">{children}</div>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return <div className="border border-line bg-white px-3 py-2 text-sm"><span className="text-gray-600">{label}</span> <b>{value}</b></div>;
}

function Meta({ label, value }: { label: string; value: string }) {
  return <div className="border border-line bg-white p-3"><div className="text-xs uppercase text-gray-500">{label}</div><div className="mt-1 text-sm font-medium">{value}</div></div>;
}

function ActivityList({ activities }: { activities: Activity[] }) {
  return (
    <div>
      <h3 className="section-label">Timeline & Activity History</h3>
      <div className="max-h-[480px] overflow-auto border border-line bg-white scrollbar-thin">
        {activities.map((activity) => (
          <div key={activity.id} className="border-b border-line p-3 last:border-b-0">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="text-sm font-semibold">{activity.title}</span>
              <span className="text-xs text-gray-500">{formatDate(activity.created_at)}</span>
            </div>
            <div className="mt-1 text-xs uppercase text-signal">{activity.activity_type}</div>
            <pre className="mt-2 whitespace-pre-wrap break-words text-xs text-gray-700">{JSON.stringify(activity.details, null, 2)}</pre>
          </div>
        ))}
        {activities.length === 0 && <p className="p-3 text-sm text-gray-600">No activity yet.</p>}
      </div>
    </div>
  );
}

function safeJson(value: string) {
  try {
    return JSON.parse(value);
  } catch {
    return { raw: value };
  }
}

function formatDate(value?: string | null) {
  if (!value) return "None";
  return new Date(value).toLocaleString();
}
