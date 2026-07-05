# CHEATSHEET — Skills & ops playbook (game day)

## 🎛️ Which skill / command, when

| Moment | Tool | Why |
|--------|-------|-----|
| **Pick + lock the idea** (Sat morning) | `/brainstorming` then `/premortem` | Frames intent before coding, then kills the risks (Tigers/Elephants) before committing 15h to it |
| **Quickly grasp the problem statement / sponsor stack** | `/deep-research` · MCP **context7** (`resolve-library-id` → `query-docs`) · **Explore** agent | Up-to-date docs for a sponsor lib/API without guessing |
| **Scaffold + deploy** | `/vercel:bootstrap` then `/vercel:deploy` · skills `vercel:nextjs`, `vercel:shadcn` | Preview URL = demo from hour one |
| **Wire an LLM** | skill `vercel:ai-sdk` · skill `claude-api` (model ids, streaming, tool use) | Clean, up-to-date agent integration |
| **UI that pops for the demo** | skill `frontend-design` · agent `vercel:ai-architect` | The demo is worth 50% — visuals sell |
| **Does it actually work?** | `/run` · `/verify` | The demo is judged live, not the tests |
| **Stuck on a bug** | `/systematic-debugging` | Avoids random fixes under stress |
| **Charts/dashboards in the demo** | skill `dataviz` | One coherent visual system |
| **Polished 1-min video** | skill `remotion` (if you want motion) otherwise Loom | Mandatory deliverable |
| **Parallelize independent build** | `/dispatching-parallel-agents` · agents `general-purpose` / `Explore` | You + agents in parallel on disjoint slices |
| **Capture a decision/learning** | skill `second-brain` | Post-hackathon, without polluting the build |

## ⚡ Recommended build loop
1. `/brainstorming` → one-liner + 3-step demo path.
2. `/premortem` → if an Elephant shows up, pivot **now**.
3. Scaffold Next.js + `vercel deploy` (empty URL online).
4. **Vertical slice**: the first of the 3 demo steps, end-to-end, deployed.
5. `/verify` → screenshot → next step. Repeat.
6. Sun morning: freeze, polish, video, pitch.

## 📇 Ops facts (source: Second Brain `raise-hackathon-2026.md`)
- **Cerebral Valley / cv.inc** · contact **alex@cv.inc** · Discord `N26eKqmR42`.
- Paris 9th venues: **La Maison** (2 rue des Mathurins, Cursor track) · **Neon Noir** (14 rue Le Peletier, Vultr/DeepMind/Crusoe). On-site = **first come, first served**, be there **8:30**.
- On-site = **exactly 5** per team · remote = max 5.
- R1 judging ~3-min pitch + Q&A → top 3/track on stage.
- **Minor status (17 y/o)**: item to clarify with alex@cv.inc (age/party).

## 🎯 Judging grid (stick it to your mental wall)
**Demo 50 · Impact 25 · Creativity 15 · Pitch 10.**
Every trade-off → "does this make the live demo more impressive and more reliable?" If not, cut it.

## 🚫 Banned (disqualifying)
Basic RAG · Streamlit · image analyzer · generic chatbot · CV screener · medical advice. Aim for **agentic / technical / infra**.
