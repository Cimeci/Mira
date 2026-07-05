-- Mira — victim reference face signature (lane L2).
-- The 512-d ArcFace embedding of the victim, used to match candidate media against.
-- Stored as jsonb (a plain float array): cosine similarity is computed in Python
-- (mira/face.py), so pgvector is not required. NO raw photo is ever stored.
-- Apply: psql "$SUPABASE_DB_URL" -f this_file.

create table if not exists public.victim_embeddings (
  case_id    text primary key references public.cases(case_id) on delete cascade,
  embedding  jsonb not null,                 -- 512 floats
  created_at timestamptz not null default now()
);

-- RLS on, no policy: the anon key reads nothing; only the backend (service_role) passes.
alter table public.victim_embeddings enable row level security;
