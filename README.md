<img width="1792" height="592" alt="image" src="https://github.com/user-attachments/assets/4e248cd0-d80b-446d-b7c4-b694e92d92e2" />


# Mira — a consent-first takedown agent for non-consensual intimate imagery

**Mira is an assistive AI agent that helps a victim of non-consensual intimate imagery (NCII / sexual deepfakes) get the content removed under EU law — without ever having to look at the material, hunt down the host, or write a single line of legal text.**

The core idea: being a victim *and* having to run the takedown process yourself is a second trauma. An AI has no feelings — so it does the dirty work in the victim's place. The victim drops a URL and signs a mandate; a chain of agents does the rest.

## What it does

Mira runs a four-stage pipeline where **consent unlocks autonomy** — no stage runs without an active, signed mandate:

```
Mandate  →  Locate  →  Analyze  →  Notify
consent     computer   face match   DSA notice +
gate        use        + minor      victim gate
            (in-scope   pre-check    + host filing
             URLs only)
```

1. **Mandate** — the victim submits a URL and signs a consent mandate (KYC face scan, with facial embeddings generated **client-side** — the image never leaves their device). Without an active mandate, nothing runs.
2. **Locate** — a computer-use agent visits **only the in-scope URLs**, behaves like a human (scroll, captcha), and collects candidate media. Read-only; it never judges the content or follows links off-scope.
3. **Analyze** — runs a **minor pre-check first** (suspected minor → immediate halt + escalation, zero storage), then compares the victim's facial embeddings against the collected media and scores for deepfakes. Stores minimal proof (perceptual hash + URL + timestamp), never raw images.
4. **Notify** — resolves the host, drafts a **DSA Article 16** takedown notice with a good-faith declaration and an AI-transparency line, then — **after the victim reviews and approves it** — files the report or emails the host. A re-check runs 7 days later to confirm the content is gone.

What the victim *does*: paste a URL, sign, click "approve." What they **never** do: scroll the content, find the host, write legal text, or repeat it for every site.

## How it's built

- **Brain:** Gemini 2.5 Computer Use decides the on-screen action from a screenshot.
- **Body:** Playwright (Chromium) executes the clicks/typing/scrolling inside an isolated, ephemeral browser sandbox — never on the victim's device.
- **Runtime:** an async orchestrator enforces the consent gate once, spawns one sandbox per case, streams live agent state to the frontend, and tears everything down on completion or mandate revocation.
- **Surfaces:** a Next.js frontend (`frontend/`) for the victim-facing flow and a FastAPI SSE backend (`mira/api.py`) that bridges the workflow to the UI.

The `mira/` package runs the full `Mandate → Locate → Analyze → Notify` pipeline end-to-end on **mocks**, behind frozen interfaces in `mira/types.py` — so each stage can swap its mock for the real implementation without breaking the others.

## Run it

```bash
# Skeleton — runs on the Python stdlib, zero install:
python3.11 -m mira.demo        # plays the 3 demo beats, fully mocked

# Full environment:
bash setup.sh && source .venv/bin/activate
python -m mira.demo ; pytest -q ; ruff check .

# Everything locally, one command:
bash dev.sh                    # pipeline API :8000 · locator CU :8001 · face-verifier :3001

# Frontend only:
cd frontend && npm install && npm run dev   # http://localhost:3000
```

## Safety guardrails (non-negotiable)

- No agent runs without an active mandate — consent is the legal basis for processing the image at all (GDPR).
- The Locator stays **strictly within the mandate's scope** — no open-web crawling.
- Suspected minor → **halt and escalate**, never download / hash / store (potential CSAM is detected and reported, never handled).
- Store URLs + perceptual hashes + client-side embeddings, **never raw images**; encrypt what little is kept.
- A victim confirmation gate precedes every external send; every notice cites the exact legal basis and never invents a penalty.
- The demo targets a **mock host and a demo inbox only** — no real victim, no real content, no live hostile platform.

Full engineering standard and guardrail list: [`CLAUDE.md`](CLAUDE.md). Agentic engine, infra, and legal framework: [`ARCHITECTURE.md`](ARCHITECTURE.md).

> ⚠️ Not legal advice. References to GDPR, the DSA, and the French SREN law are indicative and must be re-verified before any real deployment. No real victim data flows through the demo.

---

Event details: https://cerebralvalley.ai/e/raise-summit-hackathon/details
