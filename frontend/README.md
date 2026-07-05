# Mira — Frontend

Next.js (App Router, TypeScript, Tailwind) implementation of the Mira victim-facing
prototype, built from the Claude Design handoff bundle.

## Run

```bash
cd frontend
npm install
cp .env.example .env.local   # then fill the two NEXT_PUBLIC_SUPABASE_* values
npm run dev      # http://localhost:3000
npm run build    # production build (passes clean: no type/lint errors)
```

## Flow (one route per screen)

| Route | Screen |
|-------|--------|
| `/` | landing — punchline, typed terminal, impact counters, CTA |
| `/login` | sign in / create account (Supabase Auth) |
| `/start` | start case — what happened, url list, discovery chips |
| `/actions` | action options — "do everything" + toggleable paths |
| `/mandate` | sign the mandate — scroll-gated contract + signature pad |
| `/signature` | facial signature — KYC face-scan modal, wired to the real face-verifier (`enroll`/`verify` via the same-origin `app/api/face` proxy), real camera + demo fallback |
| `/case` | case created — confirmation card, status, timeline (post-signature landing) |
| `/cases` | live dashboard — every case, opened from a case, streaming its agent state over SSE |
| `/cases/[caseId]` | live case detail — SSE timeline + the **G-7 approval gate** on the DSA notice (approve / decline) |
| `/legal` | legal hub → `/legal/mentions`, `/legal/privacy`, `/legal/terms` (linked from every footer) |

The five case screens (`/start` → `/case`) are session-only: `SessionGate`
redirects signed-out visits to `/login?next=…`. `/signature` additionally
requires a signed mandate; visiting it unsigned redirects to `/mandate`.

## Session

Auth is Supabase Auth (email + password) through `lib/session-context.tsx`;
the browser only ever holds the anon key (`NEXT_PUBLIC_*`, RLS keeps tables
unreadable). The gate is client-side — fine here because the browser never
reads the DB directly; all case data flows through the backend.

## Structure

- `app/` — one folder per route (App Router)
- `components/ui/` — shared primitives (Button, Input, Chip, Panel, …)
- `components/layout/` — ScreenShell, Header, Footer, ProgressBar, Logo
- `components/{landing,start,actions,mandate,signature,case}/` — page composites
- `components/cases/` — live dashboard (CasesShell, CaseListItem, CaseCard, StatusLabel)
- `components/auth/` — SessionGate, LoginForm, SessionBadge
- `app/api/face/[action]/` — same-origin proxy to the face-verifier (`enroll`/`verify`, no CORS)
- `lib/` — flow context (shared state / mandate gate), session context (Supabase Auth), `faceVerifier` (enroll/verify client), `getCases` / `caseProgress` (dashboard data) + hooks (count-up, reduced-motion)
- Design tokens live in `tailwind.config.ts` + `app/globals.css` (from `design.md`); no motion library — CSS keyframes + rAF only.

## Privacy note

The face-scan runs client-side: frames land in an in-memory canvas, and the single
frame used for identity is forwarded **once** to the local face-verifier through the
same-origin `app/api/face` proxy — never stored, only turned into an embedding. The
media stream is stopped on cancel/error/completion/unmount, matching the design's
client-side-only requirement.
