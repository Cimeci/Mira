# CONTRIBUTING — Team workflow (5 people, hackathon mode)

Goal: **5 people shipping in parallel without stepping on each other, with a `main` that always runs**. Quality = it doesn't break the demo. No bureaucracy.

## 1. Golden rule
**`main` is always deployable.** We never push broken code to `main`. Everything goes through a branch + a short PR (even a 10-min review is enough). Vercel auto-deploys `main` → if `main` breaks, the demo breaks.

## 2. Split into 5 lanes (zero collision)
Each person **owns** a folder/surface. Don't touch someone else's lane without telling them (→ avoids 90% of merge conflicts).

| Lane | Owner | Scope | Folder |
|------|-------|-----------|---------|
| **L1 — Core / Agent** | _TBD_ | The agentic/technical engine = the "wow" | `src/core/`, `src/agent/` |
| **L2 — Backend / API / Data** | _TBD_ | Endpoints, DB, sponsor-stack integration | `src/app/api/`, `src/lib/` |
| **L3 — Frontend / UI** | _TBD_ | The demo surface | `src/app/(ui)/`, `src/components/` |
| **L4 — Infra / Deploy / DX** | _TBD_ | Vercel, CI, env, keeps `main` green, unblocks the others | `.github/`, config, `setup.sh` |
| **L5 — Integration / Demo / Pitch** | _TBD_ | Glues it all together, writes the demo script, video, pitch. Owner of "does it run end-to-end" | `demo/`, `DEMO.md` |

Fill in the owners on Saturday morning in `TASKS.md`.

## 3. Git flow (trunk-based, short branches)
```bash
git checkout main && git pull            # always start from an up-to-date main
git checkout -b l3/hero-section          # branch = <lane>/<slug>, short-lived
# ... code ...
pnpm check                               # typecheck + lint + format BEFORE pushing (see §4)
git add -A && git commit -m "feat(ui): hero section"
git push -u origin l3/hero-section
gh pr create --fill                      # PR → 1 quick review → merge
```
- **Short branches**: merge within 1-2h max. A branch that lives a whole day = conflict hell.
- **Rebase on main often** (`git pull --rebase origin main`) to stay up to date.
- **Small commits** with a prefix: `feat() fix() chore() refactor()` + lane scope.
- **Never commit secrets** → see `.env.example`.

## 4. Quality gates (automated, fast)
- **Pre-commit** (husky + lint-staged): formats + lints staged files automatically. Invisible, fast.
- **`pnpm check`** before pushing: `tsc --noEmit && eslint . && prettier --check`.
- **GitHub Actions CI** (`.github/workflows/ci.yml`): re-runs typecheck + lint + build on every PR. A red PR does not merge.
- **Strict TypeScript**: no wild `any`, no `@ts-ignore` without a comment.

→ Enable all of this at once after picking the track: **`bash setup.sh`** (scaffolds Next.js + quality tooling + husky).

## 5. Coding standard (hackathon = pragmatic but clean)
- **Explicit naming**, short functions, one file = one responsibility.
- **No over-engineering**: no speculative abstraction, no exhaustive tests. We test **the demo path**, period.
- **Throwaway code OK** in `scratch/` — but what lands on `main` is readable by the other 4.
- **Comment only when the "why" is not obvious.**
- The PR review checks one thing: **does it work and does it not break the others' demo?**

## 6. Comms
- A decision that impacts another lane → say it out loud / on the team Discord **before** coding.
- Broken `main` = **L4's (Infra) absolute priority** to fix. Nobody builds on a red main.
