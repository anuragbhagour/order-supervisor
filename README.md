# Order Supervisor

Order Supervisor is a proof-of-concept assignment project that demonstrates a long-running order supervision workflow using Temporal, FastAPI, Next.js, and Supabase.

It is designed to show:

- one Temporal workflow per order
- event-driven wake/sleep behavior
- agent reasoning and business actions
- activity history and compact memory
- UI-based run control and instruction injection
- final workflow summaries with learnings and feedback

## 1. Prerequisites

Install the following before you begin:

- Python 3.11+
- Node.js 20+
- npm
- Docker (recommended for Temporal) or the Temporal CLI
- A Supabase account

If you are on Windows, use PowerShell. If you are on macOS/Linux, use the terminal equivalent of the commands below.

## 2. Clone the project

```powershell
git clone <your-repo-url>
cd "order supervisor"
```

## 3. Backend setup

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Create the backend environment file:

```powershell
Copy-Item .env.example .env
```

Edit the new file and fill in your values:

```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
TEMPORAL_ADDRESS=localhost:7233
TEMPORAL_NAMESPACE=default
TEMPORAL_TASK_QUEUE=order-supervisor-task-queue
API_CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

> Use the Supabase service-role key only on the backend. Do not expose it to the frontend.

## 4. Frontend setup

```powershell
cd ..\frontend
npm install
Copy-Item .env.local.example .env.local
```

Edit the frontend environment file:

```env
NEXT_PUBLIC_API_BASE=http://127.0.0.1:8000
```

## 5. Supabase setup

1. Create a Supabase project.
2. Open the SQL editor.
3. Run the SQL from [supabase/schema.sql](supabase/schema.sql).
4. Confirm these tables exist:
   - supervisors
   - runs
   - activity_log

## 6. Start Temporal

### Option A: Docker (recommended)

```powershell
docker compose -f docker-compose.temporal.yml up
```

### Option B: Temporal CLI

If you prefer the CLI, start it with:

```powershell
temporal server start-dev --db-filename .\temporal.db
```

The Temporal UI should be available at:

- http://localhost:8233

## 7. Start the worker

In a separate terminal:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m app.worker
```

## 8. Start the backend API

In another terminal:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

## 9. Start the frontend

In another terminal:

```powershell
cd frontend
npm run dev -- --hostname 127.0.0.1 --port 3000
```

Open the app at:

- http://127.0.0.1:3000

## 10. Demo flow

A simple walkthrough for the assignment demo is:

1. Create a supervisor template from the UI.
2. Start a workflow for a new order.
3. Inject an event such as `shipment_delayed`.
4. Observe the wake decision, reasoning, and business actions.
5. Add a live instruction such as `Do not contact the customer without human review.`
6. Inject a customer event and see how the instruction changes behavior.
7. Pause and resume the run.
8. Inject `delivered` to trigger workflow completion and final output.

## 11. API endpoints

The backend exposes the following routes:

- POST /api/supervisors
- GET /api/supervisors
- GET /api/supervisors/{supervisor_id}
- POST /api/runs
- GET /api/runs
- GET /api/runs/{run_id}
- POST /api/runs/{run_id}/events
- POST /api/runs/{run_id}/instructions
- POST /api/runs/{run_id}/interrupt
- POST /api/runs/{run_id}/resume
- POST /api/runs/{run_id}/terminate

Swagger docs are available at:

- http://127.0.0.1:8000/docs
- http://127.0.0.1:8000/redoc

## 12. Troubleshooting

### “Failed to fetch” in the frontend

This usually means the backend is not running or the frontend is pointing to the wrong API base.

Check:

```powershell
curl http://127.0.0.1:8000/health
```

You should receive:

```json
{"ok":"true"}
```

If it does not work, start the backend and confirm that [frontend/.env.local](frontend/.env.local) points to the same host.

### Temporal worker is not processing runs

Make sure:

- Temporal is running
- the worker process is still active
- the backend can reach Temporal at `localhost:7233`

### Supabase errors

Make sure:

- the Supabase URL and service-role key are correct
- the SQL from [supabase/schema.sql](supabase/schema.sql) has been applied
- the backend `.env` file exists and is loaded

## 13. Notes

The agent runtime is intentionally deterministic so the demo is stable and easy to understand. The policy logic lives in [backend/app/agents/policy.py](backend/app/agents/policy.py), which makes it straightforward to replace with an LLM-backed planner later while keeping the same workflow contract.
