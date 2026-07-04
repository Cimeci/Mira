# mira — frontend

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
| `/signature` | facial signature — KYC face-scan modal (real camera + demo fallback) |
| `/case` | case created — case card, status, timeline |
| `/legal` | legal notice · privacy · terms (linked from every footer) |

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
- `components/auth/` — SessionGate, LoginForm, SessionBadge
- `lib/` — flow context (shared state / mandate gate), session context (Supabase Auth) + hooks (count-up, reduced-motion)
- Design tokens live in `tailwind.config.ts` + `app/globals.css` (from `design.md`); no motion library — CSS keyframes + rAF only.

## Privacy note

The face-scan captures frames to an in-memory canvas only — nothing is uploaded,
and the media stream is stopped on cancel/error/completion/unmount, matching the
design's client-side-only requirement.
