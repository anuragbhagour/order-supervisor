# Order Supervisor

## Project Overview

Order Supervisor is a working proof-of-concept for a long-running AI agent that oversees a single order from creation through completion. The system uses a Next.js frontend, a FastAPI backend, a Temporal workflow per order, and Supabase persistence to track run state, event history, compact memory, and final output.

The project is designed to demonstrate the core assignment requirements:

- one long-running Temporal workflow per order
- event-driven wake/sleep behavior
- agent reasoning and tool-like actions
- compact memory and activity history
- UI-based control over runs and instructions
- workflow-owned completion when the order reaches a terminal state

## Prerequisites

Before running the project, make sure you have:

- Python 3.11+
- Node.js 20+
- A Temporal dev server or Temporal CLI
- A Supabase project

## Installation

### 1. Clone and open the project

```powershell
cd d:\order supervisor
```

### 2. Backend setup

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

### 3. Frontend setup

```powershell
cd ..\frontend
npm install
Copy-Item .env.example .env.local
```

## Environment Variables

Create a backend environment file at `backend/.env`:

```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
TEMPORAL_ADDRESS=localhost:7233
TEMPORAL_NAMESPACE=default
TEMPORAL_TASK_QUEUE=order-supervisor-task-queue
API_CORS_ORIGINS=http://localhost:3000
```

Create a frontend environment file at `frontend/.env.local`:

```env
NEXT_PUBLIC_API_BASE=http://localhost:8000
```

Use the Supabase service-role key only on the backend. Do not expose it to the browser.

## Database Setup

1. Create a Supabase project.
2. Open the SQL editor.
3. Run the SQL from `supabase/schema.sql`.
4. Confirm that the following tables exist:
   - `supervisors`
   - `runs`
   - `activity_log`

## Running the Application

### 1. Start Temporal

Option A: Temporal CLI

```powershell
& 'C:\Users\manis\Downloads\temporal_cli_1.7.2_windows_amd64\temporal.exe' server start-dev
```

Option B: Docker

```powershell
docker compose -f docker-compose.temporal.yml up
```

The Temporal UI will be available at `http://localhost:8233`.

### 2. Start the Temporal worker

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m app.worker
```

### 3. Start the FastAPI backend

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8000
```

### 4. Start the frontend

```powershell
cd frontend
npm run dev
```

Open `http://localhost:3000`.

## API Surface

The backend exposes the following endpoints:

- `POST /api/supervisors`
- `GET /api/supervisors`
- `GET /api/supervisors/{id}`
- `POST /api/runs`
- `GET /api/runs`
- `GET /api/runs/{run_id}`
- `POST /api/runs/{run_id}/events`
- `POST /api/runs/{run_id}/instructions`
- `POST /api/runs/{run_id}/interrupt`
- `POST /api/runs/{run_id}/resume`
- `POST /api/runs/{run_id}/terminate`

The API documentation is available at:

- `http://localhost:8000/docs`
- `http://localhost:8000/redoc`

## Demo Walkthrough

A simple user flow for the demo is:

1. Create a supervisor template.
2. Start a workflow for an order.
3. Inject `payment_confirmed` and confirm it is recorded.
4. Inject `shipment_delayed` and observe the wake decision, reasoning, logistics action, and internal note.
5. Add a live instruction such as `Do not contact the customer without human review.`
6. Inject `customer_message_received` and confirm that customer contact is blocked by the instruction.
7. Pause and resume the run.
8. Inject `delivered` to trigger workflow-owned completion and final output.

## Notes

The agent runtime is intentionally deterministic so the demo remains stable. It is isolated in `backend/app/agents/policy.py`, which makes it easy to replace later with an LLM-backed planner while keeping the same action contract.
