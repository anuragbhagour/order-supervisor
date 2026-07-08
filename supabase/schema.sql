create extension if not exists "pgcrypto";

create table if not exists supervisors (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  base_instruction text not null,
  available_actions jsonb not null default '[]'::jsonb,
  default_wake_minutes integer not null default 30,
  model_config jsonb not null default '{}'::jsonb,
  wake_guidance text not null default '',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists runs (
  id uuid primary key default gen_random_uuid(),
  supervisor_id uuid not null references supervisors(id) on delete cascade,
  order_id text not null,
  order_context jsonb not null default '{}'::jsonb,
  extra_instructions jsonb not null default '[]'::jsonb,
  status text not null default 'starting',
  sleep_state text not null default 'awake',
  next_wake_at timestamptz,
  memory_summary text,
  last_reasoning text,
  final_output jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists activity_log (
  id uuid primary key default gen_random_uuid(),
  run_id uuid not null references runs(id) on delete cascade,
  activity_type text not null,
  title text not null,
  details jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists idx_runs_supervisor_id on runs(supervisor_id);
create index if not exists idx_runs_status on runs(status);
create index if not exists idx_activity_log_run_id_created_at on activity_log(run_id, created_at);
