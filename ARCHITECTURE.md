# Order Supervisor Architecture

## Overall Architecture

This project follows a simple but practical three-layer design:

1. A Next.js frontend for supervisor setup, run monitoring, event injection, instruction updates, and workflow controls.
2. A FastAPI backend for API orchestration, persistence, and Temporal workflow management.
3. A Temporal-based workflow engine that runs one long-lived workflow per order and coordinates agent decisions over time.

The backend stores persistent state in Supabase so the system can recover run history, memory, and workflow state without relying on local-only storage.

## Why This Design

The assignment calls for a believable POC rather than a production platform. This design keeps the scope focused while still covering the core requirements:

- long-running workflows with durable state
- signal-driven event processing
- agent wake/sleep behavior
- compact memory and full activity history
- a simple but usable UI

Temporal is used because it is well suited to long-running workflows that need to pause, resume, receive signals, and maintain durable state across time. Supabase provides a lightweight persistence layer for run metadata and timeline data without the overhead of managing a full custom backend store.

## Temporal Workflow Design

Each order gets its own Temporal workflow run, identified by a workflow id such as `order-supervisor-{run_id}`. The workflow is responsible for:

- starting with initial order context and base instructions
- receiving incoming events as signals
- deciding whether an event should wake the main agent immediately
- sleeping until the next scheduled review when no urgent action is needed
- finalizing the run when the order reaches a terminal state or the user terminates it

The workflow is implemented in `backend/app/workflows/order_supervisor.py`. It uses the three required inference triggers:

- workflow start
- important incoming signal
- scheduled wake-up

## Agent Runtime

The agent runtime is intentionally deterministic so the demo is stable and easy to understand. It is implemented in `backend/app/agents/policy.py` and acts like a lightweight policy engine instead of a full LLM orchestration stack.

The runtime:

- inspects the current trigger and event context
- decides whether to act immediately or remain asleep
- emits tool-like actions such as message escalation, internal notes, or workflow closure
- updates compact memory and reasoning output
- returns a final summary when the run finishes

This is a good fit for the assignment because it keeps the behavior predictable while still clearly demonstrating the design pattern.

## Memory Implementation

The system maintains two levels of state:

- a compact memory summary for the current run
- a full timeline in the activity log for auditability

After each agent pass, the workflow updates the memory summary with the most relevant recent information. Older history is compressed into a rolling summary instead of being appended indefinitely. This keeps the system simple while still providing enough context to make future decisions.

The full history remains available in the `activity_log` table through the Supabase integration.

## Database Schema

The database schema is defined in `supabase/schema.sql` and includes three main tables:

- `supervisors`: stores supervisor templates, wake guidance, and available actions
- `runs`: stores run state, order context, memory summary, sleep state, and final output
- `activity_log`: stores all timeline events, wake decisions, business actions, manual instructions, and final results

This split keeps configuration, workflow state, and event history clearly separated while still allowing easy inspection from the UI.

## Event Flow

The typical event flow is:

1. The user creates a supervisor in the UI.
2. The user starts a workflow run for an order.
3. FastAPI creates the run in Supabase and starts the Temporal workflow.
4. The workflow performs an initial agent pass.
5. The UI or API sends order updates as signals into the workflow.
6. The workflow records the event and uses a lightweight classifier/policy to decide whether the main agent should wake immediately.
7. If the event is important, the workflow triggers another agent pass; otherwise it remains asleep until the next scheduled wake-up.
8. The run finalizes once the workflow reaches a terminal state or the user terminates it.

## Tool Execution

The app uses tool-like actions rather than real external integrations, which matches the assignment scope. The supported action types include:

- `message_fulfillment_team`
- `message_payments_team`
- `message_logistics_team`
- `message_customer`
- `create_internal_note`

These actions are emitted by the agent runtime and recorded in the activity log. In a future version, they could be mapped to real messaging systems, CRM actions, or workflow automation tools.

## Trade-offs and Future Improvements

This implementation prioritizes clarity and reliability over production complexity. Some trade-offs include:

- a deterministic policy instead of an LLM planner
- simulated tool execution rather than real integrations
- simple memory compaction rather than a more advanced retrieval system
- no authentication or multi-tenant hardening

Future improvements could include:

- switching the policy runtime to an LLM-backed planner
- adding richer wake guidance generation
- supporting continue-as-new for very long-running histories
- adding better analytics and richer memory strategies
- integrating real customer or fulfillment tooling
