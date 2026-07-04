-- Mira — schéma initial : cases / case_events / notices (lane L2).
-- Miroir durable de l'état en mémoire de mira/api.py (audit trail du pipeline).
-- AUCUN octet média, AUCUNE PII (G-5) : ids opaques, URLs de démo, hashes,
-- texte de notice (G-9). Appliquer : psql "$SUPABASE_DB_URL" -f ce_fichier.

-- Un case = un mandat + l'état courant de sa state machine (spec §10).
create table if not exists public.cases (
  case_id        text primary key check (case_id ~ '^[A-Za-z0-9_-]{1,64}$'),
  requester_role text not null default 'victim',
  scope_urls     jsonb not null default '[]'::jsonb,
  last_status    text,                              -- dernier Status vu (MANDATED..NOTIFIED)
  statuses       jsonb not null default '{}'::jsonb, -- {url: status} en fin de pipeline
  finished       boolean not null default false,
  created_at     timestamptz not null default now(),
  updated_at     timestamptz not null default now()
);

-- Timeline append-only : le message SSE tel quel (contrat en tête de mira/api.py).
-- (case_id, seq) rejoue l'historique dans l'ordre exact du flux.
create table if not exists public.case_events (
  id         bigint generated always as identity primary key,
  case_id    text not null references public.cases(case_id) on delete cascade,
  seq        integer not null,
  kind       text not null check (kind in ('stage', 'notice', 'done', 'error')),
  payload    jsonb not null,
  created_at timestamptz not null default now(),
  unique (case_id, seq)
);

create index if not exists case_events_case_seq_idx
  on public.case_events (case_id, seq);

-- Une notice DSA par média : texte figé au gate G-7, verdict humain, envoi.
create table if not exists public.notices (
  id          bigint generated always as identity primary key,
  case_id     text not null references public.cases(case_id) on delete cascade,
  source_url  text not null,
  notice_text text not null,
  approved    boolean,                      -- verdict G-7 (null = gate encore ouvert)
  dispatched  boolean not null default false, -- true après NOTIFIED (stage 3)
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now(),
  unique (case_id, source_url)
);

-- RLS activé SANS policy : la clé anon ne lit RIEN, seul le backend (service_role)
-- passe. Des policies viendront si le front L3 lit un jour Supabase en direct.
alter table public.cases enable row level security;
alter table public.case_events enable row level security;
alter table public.notices enable row level security;
