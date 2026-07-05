<img width="1792" height="592" alt="image" src="https://github.com/user-attachments/assets/4e248cd0-d80b-446d-b7c4-b694e92d92e2" />


# 🏆 Mira — RAISE Hackathon 2026

> Build workspace, team of 5. Ship a demo that **works**. Submission **Sunday 12:00**.
> Repo: `github.com/Cimeci/Mira` · Architecture & engine → `ARCHITECTURE.md` · Team workflow → `CONTRIBUTING.md` · Board → `TASKS.md`

**A large share of the code is written with Claude Code** (not mandatory). If you use it: open it in this folder, it reads `CLAUDE.md` automatically and knows every rule, the git workflow and the coding standard from the start. Just tell it your lane (Core/Backend/UI/Infra/Demo). The same rules apply if you code by hand.

## ▶️ Run the skeleton (runs on the stdlib, zero install)
```bash
python3.11 -m mira.demo      # plays the 3 demo beats (all mocked)
# or, full environment:
bash setup.sh && source .venv/bin/activate
python -m mira.demo ; pytest -q ; ruff check .
```

## 🚀 Run everything locally (one command)
```bash
bash dev.sh                  # pipeline API :8000 · locator CU :8001 · face-verifier :3001
```
Ctrl+C stops everything. Ports overridable via `MIRA_API_PORT` / `MIRA_WEB_PORT` /
`FACE_VERIFIER_PORT`. The (Node) face-verifier only starts if
`services/face-verifier/node_modules` exists (`cd services/face-verifier && npm install`).
The `Mandate → Locate → Analyze → Notify` pipeline runs end-to-end on **mocks**. Each lane swaps its stage's mock for the real thing, behind the frozen interfaces in `mira/types.py`. Mira guardrails in `CLAUDE.md`.

## ⏱️ Timeline (Jul 4–5, venue closes 22:00 Sat / reopens 07:00 Sun)

| Block | Goal |
|------|----------|
| **Sat morning (from 8:30)** | Pick track + problem statement · lock the idea · scaffold + first empty Vercel deploy |
| **Sat afternoon** | **Working end-to-end vertical slice** (the demo path). Nothing else counts until this works. |
| **Sat evening (off-site)** | Widen the demo · wire the sponsor stack fully · harden |
| **Sun morning** | Feature freeze at 10:00. Polish demo · record **1-min video** · rehearse 3-min pitch |
| **Sun 12:00** | **SUBMIT** (form + video + public repo) |

## ✅ Submission checklist
- [ ] **Public** repo + **MIT LICENSE** (already in place)
- [ ] Deployed live demo (Vercel preview URL) that runs without you
- [ ] 1-min video (Loom/YT) — show the result, not the code
- [ ] 3-min pitch ready: problem → demo → why it lands on the sponsor stack
- [ ] Submission form filled in
- [ ] Repo README: what + how to run + which sponsor stack

## 🖥️ Frontend (victim-facing surface, Next.js)
```bash
cd frontend && npm install && npm run dev   # http://localhost:3000
```
Landing → start → actions → mandate → facial signature → case. Details: `frontend/README.md`.

## 📌 Project status
- **Track**: Safety, Compliance & Agentic AI
- **Idea**: Mira — a *consent-first* assistive agent that helps a victim of non-consensual sexual deepfakes get them taken down under EU law (GDPR/DSA/SREN law).
- **Pipeline**: Mandate → Locate → Analyze → Notify (consent unlocks autonomy).
- **Demo path (3 beats)**: (1) no mandate → the agent refuses · (2) full pipeline → DSA notice in the inbox · (3) minor flag → halt + escalate, zero storage.
- **Demo surface**: Next.js (`frontend/`) + FastAPI SSE (`mira/api.py`)
- **Demo URL**: _TBD_

## 🚫 Disqualifying reminders
NEW WORK ONLY (zero Softcallia/pre-existing code) · 100% OSS/MIT · no basic RAG / Streamlit / image analyzer / generic chatbot / CV screener / medical advice.

→ Technical architecture (agents + Gemini computer use + infra + legal): `ARCHITECTURE.md`
→ Ops details + skills playbook: `CHEATSHEET.md`
