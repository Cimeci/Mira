# 🧠 ARCHITECTURE — Mira: computer use, agents, infra, product & legal frame

> This file freezes **what the team decided** about Mira's engine: how we use _computer use_, how the agents chain together to reach a URL's site and **fill the forms / send the takedown emails**, in which **infra** (agents in isolated Dockers), with which **product surfaces** (frontend, backend, branding), and where the legal line runs (URL submission + victim consent).
>
> Sources: `meeting_note#1_Mira_roadmap.md` (meeting #1) + the EU spec (`project-mira-eu-spec.md`). In case of conflict, **this file decides for the hackathon**; the spec remains the detailed legal reference.
>
> ⚠️ **Not legal advice.** Any legal reference (GDPR, DSA, SREN law…) is indicative and must be re-checked on Légifrance / EUR-Lex before any real deployment. No real victim data passes through the demo.

---

## 0. In one sentence

Mira is a **consent-first takedown agent for non-consensual imagery (NCII / sexual deepfakes)**: the victim submits a URL + a signed mandate, and a chain of agents goes to **collect → verify → notify** on their behalf, without them having to scroll the content or write a single line of legalese.

The core principle from the meeting: **AI has no feelings, it does the dirty work in the victim's place.** Being a victim _and_ having to handle the process yourself = double trauma. We remove that.

---

## 1. Two scopes, don't conflate them

| | **V1 — Demo path (reactive)** | **V2 — Stretch goal (proactive, uncertain)** |
|---|---|---|
| **Trigger** | The victim **submits a URL** (received from a friend, found by chance) | The victim **scans their face**, we go crawl for them |
| **Scope** | The surfaces the victim authorizes, period | An **allowlist** of sites known for deepfakes |
| **What we build this weekend** | ✅ **Yes** — this is the judged demo | 🟡 Roadmap / long-term vision (the jury's ~15%) |
| **Computer-use cost** | Bounded, demoable live | Slow + expensive — **the meeting decided NOT to scan the open web in V1** |
| **Legal weight** | Light: the victim points at the content themselves | Heavy: proactive processing of sensitive data → explicit consent + DPIA **mandatory** |

> **Team decision.** We **ship V1**, we **pitch V2**. V2 is only defensible on a precise basis (§8): it's **the victim's own face**, with **their explicit consent**, on a **restricted scope** — never a crawl of the open web on strangers. Without that, V2 is illegal, not just ambitious.

---

## 2. Computer use — the research & the choice

### 2.1 The problem it solves

Every platform has its own reporting mechanism: homegrown web form, DSA portal, `abuse@`, captcha, infinite scroll, required login. No unified API. **Computer use** = an agent that _sees the screen and acts like a human_ (moves the cursor, clicks, types, scrolls), so it absorbs this heterogeneity without us coding one connector per site.

Downside: **it's slow by nature** — a `screenshot → analyze → next action` loop, a few seconds per step. We accept it and isolate it.

### 2.2 We're on the Google track → **Gemini 2.5 Computer Use**

**Frozen decision: Mira's computer-use engine is Gemini 2.5 Computer Use** (`gemini-2.5-computer-use`, available via **Google AI Studio** and **Vertex AI**). It's the choice imposed by the sponsor track, and it's a **pitch asset**: Google claims it beats Claude Sonnet and OpenAI's agents on web/mobile UI-control benchmarks, **with lower latency** — exactly our bottleneck (computer use is slow by nature).

How it works — a **`computer_use` tool** driven in a loop:

```
  request + screenshot + action history
                    │
                    ▼
        Gemini 2.5 Computer Use
                    │  → recommended action (click / type / scroll)
                    │  → may ASK FOR CONFIRMATION on a risky action
                    ▼
        we execute the action (via Playwright / Browserbase)
                    │
                    ▼
        new screenshot sent back to the model → we loop again
                    │
            until task done / halt (error or safety decision)
```

It natively knows how to **fill and submit forms**, manipulate dropdowns/filters, and operate **behind a login** — which is precisely the takedown gesture we automate.

### 2.3 The rest of the stack around Gemini CU

| Piece | Role | Why |
|---|---|---|
| **Gemini 2.5 Computer Use** | The agent's **brain**: decides the UI action from the screenshot | Google track, best UI-control benchmarks, low latency, native form-filling |
| **Playwright** (Chromium) | The **arm**: actually executes clicks/types/scrolls, frozen demo path | Execution substrate recommended by Google for Gemini CU; deterministic and stable on the projector |
| **Browserbase** (sandbox) | Ready-made isolated browser environment | Fast start, isolation, alternative if we don't run the infra ourselves |
| **Gemini / Gemma** (2.5) | Drafting the DSA notice, locator instructions, reasoning | Same Google track; Gemma for light/local tasks |

### 2.4 What we decide

- **Gemini 2.5 Computer Use = brain; Playwright = arm.** The model decides the action, Playwright executes it. For the **critical demo path**, we can freeze the trajectory in pure Playwright (live reliability) and let Gemini CU handle the adaptive part (captcha, unknown UI) on the "wow" cases.
- **Two fronts in parallel** (agreed in the meeting): **scraping browser** + **mobile simulator** — some sites/forms only exist as an app.
- **Everything runs inside Docker containers** (or a Browserbase sandbox), **never on the victim's device**. Isolation, minimal privileges, restricted network access. An agent driving a browser is a risk surface — we sandbox it.
- **Human-in-the-loop at the edge**: Gemini CU already knows how to **ask for confirmation on a risky action** — we wire that into our victim gate (§6). Autonomous drafting and resolution, but **the victim validates before any external send**.

### 2.5 Reliability — what we put in place

Robust action loop (a known headache for browser agents):
- **Context caching** on Gemini + well-sized images + pruning of old screenshots (the token budget explodes on long sessions).
- **Timeouts + backoff** on all I/O, **watchdog** anti-stall (a coroutine that kills stuck loops).
- **Trajectory recording**: we log every action (screenshot + decision) → replayable, debuggable, and it feeds the audit trail.
- Anti-bot (captcha, Cloudflare) = known risk #1 → we rely on Gemini CU's ability to act like a human, and we **cache the response for the demo** (no fragile live dependency on the projector).

---

## 3. Workflow architecture — the agents

Pipeline **Mandate → Locate → Verify → Notify**. Consent unlocks autonomy; without an active mandate, **no agent runs** (hard guardrail at the orchestrator level, not left to each agent).

```
+------------------------------------------------------------------+
|                    ORCHESTRATOR (async runtime)                  |
|        Consent gate: refuses to start if Mandate.active == False |
+--------+------------------+------------------+--------------------+
         |                  |                  |
         v                  v                  v
+----------------+  +----------------+  +--------------------------+
| COLLECT AGENT  |  | VERIFY AGENT   |  | LEGAL / NOTIFIER AGENT   |
| (computer use) |  | (embeddings)   |  |                          |
|                |  |                |  | Resolves the host (RDAP) |
| Goes to the in-|  | Compares the   |  | Drafts the DSA a.16 notice|
| scope URLs,    |  | victim's face  |  | Good-faith + AI statement|
| simulates human|  | to collected   |  | Victim confirmation GATE |
| bypasses captcha| | images         |  | Fills the form /         |
| infinite scroll|  | Minor pre-check|  | sends the mail (takedown)|
| Read-only      |  | (STOP)         |  |                          |
+-------+--------+  +-------+--------+  +------------+-------------+
        |                   |                        |
        +-------------------+------------------------+
                            v
              +-------------------------------+
              |   ENCRYPTED CASE STORE        |
              |   URLs + hash + embeddings    |
              |   (never the raw images)      |
              |   access-logged, retention    |
              +-------------------------------+
```

### 3.1 The three layers (meeting) mapped onto the stages (spec)

| # | Agent (meeting) | Stage (spec) | Concrete role |
|---|---|---|---|
| **0** | — (gate) | **Mandate** | Records identity + consent + scope. Unlocks the rest. Revocable → purge. |
| **1** | **Collect agent** (computer use) | **Locator** | Visits **only the scope URLs**, simulates human actions (infinite scroll, captcha bypass), **read-only** (no login, no submit, doesn't follow out-of-scope links). Doesn't judge the content. Outputs candidate media URLs. |
| **2** | **Verify agent** | **Analyzer** | **Minor pre-check first** (→ STOP + escalate, §7). Then compares the victim's **facial embeddings** to the collected images (handles false positives) + deepfake score. Captures **minimal evidence** (perceptual hash + URL + timestamp), not the raw bytes. |
| **3** | **Legal agent** | **Notifier** | Identifies platform + hosting country + victim's country → **fills the online complaint / sends DMCA·DSA / contacts the host**. In France, the **victim's signature is required** on the mandate. Confirmation gate before any send. |

### 3.2 State machine

```
 MANDATED --> LOCATED --> VERIFIED --> CONFIRMED --> NOTIFIED --> [RE-CHECK D+7]
 consent      URL in-     hash +       victim       DSA notice    checks the
 + scope      scope       embeddings   approves      sent          actual removal
    |            match
    | revoked                 | suspected minor          | score < threshold
    v                         v                          v
 REVOKED                  ESCALATED                   REJECTED
 purge data               authorities + halt          discarded (0 storage)
```

- **Inter-agent communication**: `asyncio.Queue` between each stage (Locator → Analyzer → Notifier). Each agent is an independent async consumer/producer → testable in isolation with mocked APIs.
- **Two product cases covered** (meeting): **targeted** (streamers/celebrities, same images spammed across N sites) and **untargeted** (resemblance arising from a model's training). Same pipeline, the Analyzer handles the nuance.
- **Automatic re-check at D+7** after the takedown: an agent revisits the URL to verify the content is actually gone. That's what makes the product credible ("Mira doesn't just send, it verifies").

---

## 4. Infra & runtime — the brain in a controlled Docker

> Computer use drives a real browser that visits potentially hostile sites: it's **slow** and it's a **risk surface**. We isolate it. The **brain** (Gemini CU) reasons; the **body** (Chromium driven by Playwright) acts in a disposable container, never on the victim's device or the host.

### 4.1 Deployment topology (the Vercel trap to know about)

**Vercel is serverless → short timeouts, no long-running browser. Computer use does NOT run there.** Vercel hosts the **frontend + the light API**; the **orchestrator + workers** run in **containers on Cloud Run** (same cloud as Vertex AI/Gemini → key, network, secrets aligned, zero server to administer), with the **isolated browser at Browserbase**. The backend is the **bridge** between the two. Assumed choice: **managed, no VM stood up by hand** — simpler, cleaner for 15h.

```
        VICTIM (browser)
              │  HTTPS
              ▼
   ┌────────────────────────────┐
   │  FRONTEND + API  (Vercel)  │   ← serverless, light — NO computer use here
   │  Next.js App Router        │
   │  · URL submission + mandate│
   │  · stream agent state      │
   │  · notice preview + gate   │
   └─────────────┬──────────────┘
                 │  job / webhook / SSE
                 ▼
   ┌────────────────────────────┐
   │  ORCHESTRATOR + WORKERS    │   ← Cloud Run (containers, off Vercel)
   │  (async runtime, consent gate)
   │   ┌──────────┐ ┌──────────┐ │
   │   │ browser  │ │ mobile   │ │   ← ephemeral sandbox per case (Browserbase in demo · own container in prod)
   │   │ +Chromium│ │ simulator│ │      Gemini CU = brain (Vertex AI API)
   │   │ Playwright│ │          │ │      Playwright = arm (inside the container)
   │   └──────────┘ └──────────┘ │
   └─────────────┬──────────────┘
                 ▼
     ENCRYPTED CASE STORE (Postgres/Supabase)
     URLs + hash + embeddings — never the images
```

**Where it runs + who owns what** (the app / platform split, to avoid the seam-of-death on the critical path):

| Piece | Where | Owner |
|---|---|---|
| Frontend + L2 API (relay) | **Vercel** | Tech Lead (L2) |
| Cloud Run service (deploy, secrets, network, egress) | **Cloud Run** | **L4 Infra** |
| Container image + job contract + CU code inside it | **Cloud Run** | **Tech Lead** |
| Isolated browser sandbox | **Browserbase** (demo) → **own container** (prod) | L4 provisions, Tech Lead consumes |

> Rule: the Tech Lead doesn't **own** the platform, but must be able to **deploy on it without waiting** (the CU worker is the critical path). `gcloud run deploy` for troubleshooting = OK, but we announce it to L4 (we don't touch another's lane silently).

**🎯 Hackathon decision — Browserbase in demo, own container in prod.** House rule: *demoable now > clean later*.

- **This weekend: browser at Browserbase.** The demo runs on **mock** (synthetic content, mock host, demo mailbox — cf §10) → the "sensitive content passes through a third party" argument **doesn't apply**, and Browserbase removes time-sink #1: **Chromium-in-Docker** (deps, sandbox flags, OOM). **Full vibe code speeds up the *code*** (agent loop, API glue, front), **not** infra debugging — so we go managed where it hurts.
- **The own container remains the prod/roadmap argument**: *"in demo, Browserbase on synthetic; in prod, the browser runs in **our** isolated container so sensitive content never touches a third party."* Reinforces the pitch (data sovereignty / GDPR) at **zero demo cost** — option A isn't dropped, it earns vision points (~15%).
- **Guardrail**: we do **not** yak-shave the Cloud Run deploy **before** the vertical slice works. For the live demo, the orchestrator can run **locally** (the jury watches the result, not the host). Cloud Run = the pitch's clean story + the submission's "it runs without you" → to wire up **after** the end-to-end works.

### 4.2 What the container guarantees

| Constraint | Why |
|---|---|
| **1 ephemeral sandbox per case** | Total isolation between victims; teardown + purge at the end of the case or on mandate revocation |
| **Minimal privileges, ephemeral FS** | A hostile site that exploits the browser touches neither the host nor the other cases |
| **Restricted network egress (allowlist)** | The worker only talks to the scope URLs (+ Gemini/store APIs) — no wild crawl (reinforces G-2) |
| **Brain ≠ body** | Gemini CU reasons via the Google API; only Chromium+Playwright lives in the container → we can kill/replay a container without losing the logic |
| **Two runtimes in parallel** (meeting) | A **scraping browser** container + a **mobile simulator** container — some forms only exist in an app |

### 4.3 Execution robustness

- **Orchestrator**: raises the consent gate, spawns the container with the injected `scope_urls`, relays state to the backend, kills + purges at the end.
- **Watchdog + timeouts + backoff** on each job (cf §2.5) → a stuck container is killed, not left hanging.
- **Trajectory recording** persisted outside the ephemeral container → replayable, debuggable, and feeds the audit trail.
- **Lane owner**: Cloud Run infra + orchestration = **L4** (cf §9); the Tech Lead owns the container image + the job contract.

---

## 5. Product surfaces — Frontend, Backend, Branding

> The agentic engine is the "wow", but the jury scores the **live demo**. We need an **intentional** UI (house rule: no default Tailwind template) and a backend that **connects the workflow to the frontend** cleanly.

### 5.1 Branding (we already have the icon)

- **`icon.png`** (root) = Mira's **visual seed** → to derive into **favicon + app icon + header logo**.
- **Tone**: protective, dignified, serious — **never victimizing nor clinical/anxiety-inducing**. "Mira" evokes *looking / mirror*: we take on the gaze in the victim's place.
- **Before coding the UI** (design-quality house rule): freeze **palette + typography** from the icon. Assumed direction (understated editorial + one accent color), not "clean minimal" by default.
- **Demo deliverable** (meeting): 1 presentation image, **3 elements max** + the derived icon.

### 5.2 Frontend — L3 (the demo surface)

The demo-path screens, in order:

1. **Landing** — the promise: *"you don't have to handle this yourself"*.
2. **Submission** — paste the URL + **KYC** (face scan → embeddings generated **CLIENT-SIDE**, the image never leaves) + **mandate signature**.
3. **Live agent view — THE wow**: we **watch the 3 agents work in real time** (Collect → Verify → Legal), each state lighting up, **blurred** scraping screenshots, facial match (**face only**). ⚠️ Computer use's slowness becomes a **spectacle** instead of dead waiting.
4. **Preview + gate** — the drafted DSA notice appears, the victim **reviews and approves** it (they stay in control, write nothing).
5. **Follow-up** — *sent* status + **D+7 re-check**.

House constraints: **compositor-friendly** animations (`transform`/`opacity`, never `width`/`top`) — a laggy transition shows on the projector. Polished `hover`/`focus`/`active` states, hierarchy through scale contrast.

### 5.3 Backend — L2 (the workflow ↔ frontend bridge)

Next.js API routes (on Vercel) = the glue. Responsibilities:

- **Create** a case + mandate while validating inputs at the boundaries (the handler = boundary, we don't trust the input).
- **Trigger** the orchestrator (a job on the §4 Docker worker).
- **Relay** agent state to the frontend in real time (**SSE / polling**) — this is what feeds the *live agent view*.
- **Serve** the notice draft, **collect** the approval (the §6 gate).
- **Persist** URLs + hash + embeddings (Postgres/Supabase) — **never the images**.
- **What it does NOT do**: computer use itself (serverless timeouts) → it **dispatches and relays**, it doesn't drive the browser.

**Data contract** = the objects in §3/§8 (`Mandate`, `ForensicRecord`, status). **A single source of truth** for the state machine (`MANDATED → … → NOTIFIED`) shared across front / back / agents — that's what keeps the 5 sessions from diverging.

---

## 6. The main V1 flow (what the jury sees)

```
1. The victim lands on Mira, pastes a URL + signs the mandate (KYC: front-facing photo)
        │  (embeddings generated CLIENT-SIDE — the image never leaves their device)
        ▼
2. COLLECT agent (computer use, Docker) goes to the URL, fetches in-scope media
        ▼
3. VERIFY agent: minor pre-check → face embeddings match → deepfake score
        ▼
4. LEGAL agent: resolves the host, drafts the DSA art.16 notice (+ good-faith statement + AI transparency line)
        ▼
5. ⛔ GATE: the victim reviews and APPROVES the notice (they stay in control, write nothing)
        ▼
6. LEGAL agent fills the reporting form / sends the mail to the host
        ▼
7. D+7: automatic re-check → content removed? otherwise re-send / escalate
```

**What the victim does**: paste a URL, sign, click "approve". **What they never do**: scroll the content, find the host, write legalese, repeat for every site.

---

## 7. Minor safety — non-negotiable (overrides everything)

If the Analyzer's age pre-check suggests a **minor**, the content is **potential CSAM**. Mira does **NOT** download, does **NOT** hash, does **NOT** store, does **NOT** process. It **halts** (status `ESCALATED`), **refers** to the competent authority (in France: **PHAROS**) and reports to a human operator. Detection + reporting, **never** manipulation — storing or transmitting CSAM, even "as evidence", is a serious offense.

---

## 8. Legal aspect — URL submission & victim consent

> Mira's legal core. **Without a valid mandate, the agent does nothing.** Consent isn't a courtesy: under GDPR, it's **what makes processing the image lawful at all**.

### 8.1 Why URL submission + consent is the keystone

| Question | Mira's answer |
|---|---|
| **Legal basis for processing?** | Explicit consent of the victim (GDPR Art. 6(1)(a) + Art. 9(2)(a), sensitive data) and/or establishment of legal claims (Art. 9(2)(f)), **bounded to the mandate's scope**. |
| **Targeted offense** | Distribution of non-consensual deepfakes — Penal Code **art. 226-8-1** (SREN law no. 2024-449). For sexual content, the fact that the montage is "obviously fake" **does not exonerate**. |
| **Takedown mechanism** | **DSA art. 16**: every host must offer a notice-and-action mechanism. A compliant notice creates a presumption of knowledge → the host must act "without undue delay". |
| **Signature** | In **France**, the online complaint requires the **victim's signature**. Hence the mandate signed at KYC. |
| **False notice** | The **LCEN** punishes a knowingly false notification (1 year / €15,000) → **every notice carries a good-faith and accuracy statement**. |
| **AI transparency** | The **AI Act** requires stating that the notice is produced by an assistive AI system acting on mandate. Mandatory line in every send. |

### 8.2 The `Mandate` object (the contract)

```
Mandate {
  case_id          : opaque identifier, zero PII inside
  requester_role   : "victim" | "legal_rep" | "authorized_ngo"
  consent_ts_utc   : consent timestamp
  scope_urls       : the authorized surfaces, ONLY
  consent_artifact : encrypted proof of consent (signed mandate)
  active           : false on revocation → purge the case
}
```

### 8.3 Data minimization (anti re-victimization)

- **We store URLs + hash + embeddings, NEVER the images.** The embeddings are generated **client-side** → the image never leaves the victim's device. If Mira's database leaks: **no sensitive image exposed**.
- Raw bytes only if strictly necessary for legal action → **encrypted at rest, access-logged, limited retention**.
- **Revocation = full purge** of the case (right to erasure).

### 8.4 The V2 case (stretch goal) — the red line to hold

Face-scan-then-crawl is **legally defensible only if**:
1. It's **the victim's own face** (not a third party).
2. **Explicit** and informed **consent**, specifically for proactive search (Art. 9(2)(a)).
3. Scope = **restricted allowlist** of known sites, **not the open web**.
4. **DPIA** (Art. 35) carried out before any real processing.

> Without these four conditions, V2 isn't "ambitious", it's **unlawful**. That's exactly why we keep it on the roadmap and don't demo it on real data.

---

## 9. Role split → repo lanes

| Person | Role | Lane |
|---|---|---|
| **Ilan** | **Tech Lead**: backend (relay) + front↔workflow bridge + **Google Computer Use** (architecture / R&D / code integration) + PR resolution | L2 + L5 |
| **Anne-Sal** | **Computer Use** — implementing the collect agent (CU pair with Ilan) | L1 |
| **nada** | **Verify** agent (image comparison / embeddings) + **storage** + **legal aspects** | L1 / L2 |
| **Yue** | **Orchestration** of the agentic flow + **Cloud Run / Docker infra** | L4 |
| **Com** | **Art direction / storytelling** + **frontend UI** | L3 |

Team sync: **every 2-3h**.

---

## 10. Demo strategy (meeting recap)

- **3 demo videos, no slides** (imposed format). 1 project presentation image, 3 elements max.
- **Blurred images** to simulate the scraping — **never real NSFW** shown to the jury. The facial match is demoed by showing **only the face** (body blurred).
- **Mock-only environment**: fake mandate, synthetic test media (adults, no real people), dedicated demo mailbox, RDAP target on a controlled test domain.
- Also show the **minor path** on a separate synthetic case that correctly triggers the halt-and-escalate (logged reference, zero storage).
- **Roadmap to pitch**: 5-6 evolutions (children, comparison, extended scroll, V2 face-scan…). The jury scores ~15% on the long-term vision.

---

## 11. Guardrails never to violate (checklist)

- [ ] **G-1** No agent runs without `Mandate.active` (GDPR legal basis).
- [ ] **G-2** The Locator stays **strictly within scope** — zero open-web surveillance (in V1).
- [ ] **G-3** Computer use **in Docker**, never on the victim's device.
- [ ] **G-4** Minor pre-check **before any storage** → halt + escalate to PHAROS.
- [ ] **G-5** Perceptual hash + embeddings **rather than** raw bytes; we encrypt the little we retain.
- [ ] **G-6** **Victim confirmation gate** before any external send.
- [ ] **G-7** Every notice = **good-faith statement** + **AI transparency line** + exact legal basis (never invent a penalty amount).
- [ ] **G-8** Mandate revocation = **purge** of the case.
- [ ] **G-9** Zero committed secret (`.env.local`, template in `.env.example`).
- [ ] **G-10** Demo = **mock only**, no real victim, no real content, no live hostile platform.
