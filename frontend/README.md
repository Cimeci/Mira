# mira — frontend

Next.js (App Router, TypeScript, Tailwind) implementation of the Mira victim-facing
prototype, built from the Claude Design handoff bundle.

## Run

```bash
cd frontend
npm install
npm run dev      # http://localhost:3000
npm run build    # production build (passes clean: no type/lint errors)
```

## Flow (one route per screen)

| Route | Screen |
|-------|--------|
| `/` | landing — punchline, typed terminal, impact counters, CTA |
| `/start` | start case — what happened, url list, discovery chips |
| `/actions` | action options — "do everything" + toggleable paths |
| `/mandate` | sign the mandate — scroll-gated contract + signature pad |
| `/signature` | facial signature — KYC face-scan modal (real camera + demo fallback) |
| `/case` | case created — case card, status, timeline |

`/signature` requires a signed mandate; visiting it unsigned redirects to `/mandate`.

## Structure

- `app/` — one folder per route (App Router)
- `components/ui/` — shared primitives (Button, Input, Chip, Panel, …)
- `components/layout/` — ScreenShell, Header, Footer, ProgressBar, Logo
- `components/{landing,start,actions,mandate,signature,case}/` — page composites
- `lib/` — flow context (shared state / mandate gate) + hooks (count-up, reduced-motion)
- Design tokens live in `tailwind.config.ts` + `app/globals.css` (from `design.md`); no motion library — CSS keyframes + rAF only.

## Privacy note

The face-scan captures frames to an in-memory canvas only — nothing is uploaded,
and the media stream is stopped on cancel/error/completion/unmount, matching the
design's client-side-only requirement.
