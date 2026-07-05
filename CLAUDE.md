# CLAUDE.md — Mira (RAISE Hackathon 2026)

You are helping build **Mira** during a ~15h hackathon, as part of a **team of 5**. A large share of the code is written with Claude Code (but not all, and it is not mandatory for the team). Your mission: ship a **demo that works**, keep the code **coherent across several parallel contributors**, and hold a **senior-engineer standard** without slowing anyone down.

Repo: `github.com/Cimeci/Mira` · Detailed human workflow: `CONTRIBUTING.md` · Board: `TASKS.md`.

---

## 🟢 At the start of EVERY session
1. **Ask the dev which lane they own** (L1 Core/Agent · L2 Backend/API · L3 UI · L4 Infra · L5 Demo). Work in the folders of THEIR lane. **Don't modify another lane's code without flagging it** — that's the #1 cause of conflicts.
2. Remember: **`main` must always be deployable**. Never commit directly to `main`. Everything goes through a branch + PR.
3. When in doubt about a rule: it's here or in `CONTRIBUTING.md`. Don't invent it.

## 🎯 How we're judged → your priority function
**Demo 50% · Impact 25% · Creativity 15% · Pitch 10%.**
On every trade-off, ask yourself: *"does this make the live demo more reliable or more impressive?"* If not → cut it. A feature that can't be demoed live is worth nothing this weekend.

## 🚧 The frame (org rules, non-negotiable)
- **100% open source, MIT license** (already in place). Public repo.
- **NEW WORK ONLY, verified**: reusing pre-existing code is forbidden. **Never import/copy Softcallia, ProspAction, Pyralys, prospector-suite.** Everything starts from scratch in this repo.
- **Banned anti-projects (disqualifying)**: basic RAG, Streamlit, image analyzer, generic chatbot, CV screener, medical advice. → aim for **technical / agentic / infra**.
- **Deliverables**: form + **1-min video** + ~3-min R1 pitch.
- The contents of `reference/` are **inspiration only**, never reused as code (new-work-only rule).

---

## 🧠 The engineering standard — "senior, not sloppy"
Senior ≠ slow. Senior = **deliberately choosing what to do well and what to skip**, and never shipping something that fails silently.

- **Types are contracts**: strict TypeScript. No `any` without a `// reason`, no `@ts-ignore` without a comment. Model data with precise types — a bad type = a demo bug waiting to happen.
- **Short, named, single-responsibility functions.** One file = one thing. Name it so a teammate reads it once and understands.
- **No premature abstraction.** Two uses before extracting. Duplicating once is OK; on the third, factor it out.
- **Zero silent failure.** No empty `catch {}`. If it can crash during the demo, it must scream in dev. Validate inputs at the boundaries (API handlers, external data).
- **Fail fast.** An impossible state must crash early and clearly, not produce a wrong result further down.
- **Delete dead code.** No commented-out blocks "just in case". Git keeps the history.
- **Comments explain the WHY, never the WHAT.** The code says the what.

## ✂️ What we deliberately skip (it's a hackathon)
- **Exhaustive tests** → NO. We test **one thing only: the end-to-end demo path**. Nothing else needs coverage.
- **Edge cases outside the demo** → happy path + the 2-3 inputs we'll show live, that's it.
- **Speculative config** (feature flags, i18n, advanced theming, micro-optimizations) → no, unless it serves the demo.
- If you hesitate between "clean" and "demoable now" → **demoable now**, then clean up if time allows.

## 🔁 Coherence across the 5 Claudes (crucial)
5 independent Claude sessions edit this repo. **Coherence beats cleverness:**
- **Grep before writing**: reuse an existing component/util rather than creating a duplicate.
- **Follow the pattern of the file you're editing** rather than your personal preference.
- **Align** with the naming, folder structure and import style already present.
- New dependency or new structural pattern → **flag it** (it impacts the other 4).

---

## 🌿 Git & collaboration (full detail in `CONTRIBUTING.md`)
```bash
git checkout main && git pull              # start from an up-to-date main
git checkout -b l3/my-feature              # branch = <lane>/<slug>, short-lived
# ... code ...
pnpm check                                 # typecheck + lint + format — MUST be green
git add -A && git commit -m "feat(ui): my feature"
git push -u origin l3/my-feature
gh pr create --fill                        # PR → 1 quick review → merge
```
- **Short branches**, merged within 1-2h. `git pull --rebase origin main` often.
- **Commits**: `feat|fix|chore|refactor(scope): message`. Small and frequent.
- **Broken `main` = everyone stops**, L4 (Infra) fixes it first.
- **Never commit a secret** → `.env.local` (gitignored), template in `.env.example`.

## ✅ Verify BEFORE saying it's done
The demo is judged live. "It should work" ≠ "it works".
- **Actually run the flow** (`pnpm dev`, open the route, click the button) and **observe the result** before concluding.
- Modified a deployed surface → check the **Vercel preview**, not just localhost.
- Before pushing: `pnpm check` green. Non-negotiable.

## 🛠️ Stack & commands
- **Core: Python 3.11 + asyncio** (imposed by the Mira spec). `mira/` package: 4 stages (mandate/locator/analyzer/notifier) + `orchestrator` (consent gate) + `types` (frozen contracts). The pipeline runs end-to-end on **mocks**; each lane swaps its stage's mock for the real thing, behind the same interface.
- **Demo surface (front)**: to decide (Next.js+FastAPI SSE, or all-Python FastAPI+SSE). No Streamlit (banned).
- **LLM**: notice drafting / locator instructions. Google track → **Gemini/Gemma**; otherwise **Claude** (`claude-opus-4-8`, `claude-sonnet-5`, `claude-haiku-4-5-20251001`).
- Commands: `bash setup.sh` (venv + deps) · `python -m mira.demo` (the 3 beats, mocks) · `pytest -q` · `ruff check .`. The skeleton runs **with nothing installed** (stdlib): `python3.11 -m mira.demo`.
- Toolchain: python 3.11 (Homebrew), node 24, pnpm 9, vercel CLI, gh, git.

## 🔒 Mira guardrails (from spec §13 — non-negotiable)
- **G-1** no stage runs without `Mandate.active` (checked in the orchestrator, once).
- **G-2** the Locator stays strictly within `scope_urls` (no open web).
- **G-6** minor pre-check BEFORE any storage; suspected minor → **halt + escalate, never download/hash/store**.
- **G-5** perceptual hash preferred over raw bytes; encrypt whatever is retained.
- **G-7** victim confirmation gate before any external send.
- **G-9** the notice cites the exact legal basis, **never invents a penalty**.
- **G-12** the demo targets a mock host + demo inbox only — never real content/platform.
- In the demo, the minor flag is triggered by **metadata/URL**, never by an image of a minor.

## 📂 Repo files
`README.md` cockpit · `ARCHITECTURE.md` agentic engine (Gemini computer use + agent workflow + Cloud Run/Browserbase infra + frontend/backend/branding + legal frame) · `CONTRIBUTING.md` workflow · `TASKS.md` board · `CHEATSHEET.md` skills playbook · `mira/` the code · `tests/` smoke tests · `reference/` inspiration (never reused as code).
