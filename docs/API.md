# Mira API — L2 HTTP surface (`mira/api.py`)

Backend that drives the pipeline (`mira.orchestrator`) and streams every transition over SSE.
Fully on **mocks** end-to-end — no real host, no real image (G-12).

Run: `python -m mira.api` (or `uvicorn mira.api:app --reload`) → `http://127.0.0.1:8000`.

> Distinct from `mira/web/` (scraper/Computer Use surface, Ilan's lane). The two
> coexist without stepping on each other: `api` = pipeline, `web` = CU locator.

## Endpoints

| Method | Route | Role |
|--------|-------|------|
| `GET`  | `/healthz` | liveness probe → `{"status":"ok"}` |
| `POST` | `/cases` | creates a case, launches the pipeline in the background |
| `GET`  | `/cases/{id}` | **current state** of the case (read on front mount) |
| `GET`  | `/cases/{id}/events` | **SSE** stream, replayed from the start on every (re)connection |
| `POST` | `/cases/{id}/confirm` | victim verdict at the G-7 gate |

### `GET /cases/{id}`

State to read on page mount (or after an F5) to resync without
waiting for the SSE:

```json
{ "case_id":"…", "finished":false, "current_status":"AWAITING_CONFIRM",
  "statuses":{}, "awaiting_confirm":["https://…/x.jpg"],
  "pending_notice":{"url":"https://…/x.jpg","text":"Subject: …"},
  "events_url":"…", "confirm_url":"…" }
```

`pending_notice` is non-null only when the G-7 gate is open (display it +
offer Approve/Decline). `statuses` fills in at the end (`done`).

### `POST /cases`

Body is **optional** (no body → pre-authorized demo mandate on the mock host):

```json
{ "case_id": "case-…", "requester_role": "victim",
  "scope_urls": ["https://mock-host.local/target"], "attestation": true }
```

`requester_role` ∈ `victim | legal_rep | authorized_ngo`. Invalid scope / missing
attestation → **400** (fail-fast, cf. `mandate.capture_consent`).

Two additional boundary validations (→ **400**):
- `case_id`: strict format `^[A-Za-z0-9_-]{1,64}$` (it ends up in a file path —
  anti path-traversal); omitted or empty → server-generated id.
- `scope_urls`: hosts limited to the demo allow-list (G-2/G-12), default
  `mock-host.local`, extensible via `MIRA_ALLOWED_SCOPE_HOSTS="a.local,b.local"`.

Response:

```json
{ "case_id":"case-ab12cd34",
  "events_url":"/cases/case-ab12cd34/events",
  "confirm_url":"/cases/case-ab12cd34/confirm" }
```

### `GET /cases/{id}/events` (SSE)

One JSON object per `data:`, discriminated by `kind`:

```
{"kind":"stage",  "event": <StageEvent.to_dict()>}       # state transition (timeline render)
{"kind":"notice", "case_id":"…","url":"…","text":"…"}    # DSA notice to validate (G-7 gate)
{"kind":"done",   "case_id":"…","statuses":{url:status}} # finished → the stream closes
{"kind":"error",  "case_id":"…","message":"…"}           # exception → terminal event
```

`StageEvent.to_dict()` = `{case_id, stage, from_status, to_status, ts_utc, detail, payload}`
(schema frozen in `mira/events.py`). The **DSA notice never travels inside a `stage`**
(rule G-6): it arrives via `kind:"notice"`, at the moment the gate opens.

Nominal sequence (happy path):
`MANDATED → LOCATED → VERIFIED → AWAITING_CONFIRM → [notice] → CONFIRMED → NOTIFIED → [done]`

### `POST /cases/{id}/confirm`

```json
{ "approved": true, "url": "https://mock-host.local/target/synthetic_test.jpg" }
```

`url` is optional (default: first pending confirmation). `approved:false` or
silence > `MIRA_CONFIRM_TIMEOUT_S` → **DECLINED**, nothing is sent (fail-closed, G-7).

## Example (curl)

```bash
CID=$(curl -s -XPOST localhost:8000/cases | python -c 'import sys,json;print(json.load(sys.stdin)["case_id"])')
curl -N localhost:8000/cases/$CID/events &          # SSE timeline
curl -s -XPOST localhost:8000/cases/$CID/confirm -H 'content-type: application/json' -d '{"approved":true}'
```

## Known limits (assumed — hackathon)

- State is **in-memory, single-process**: restart = reset; no case purge.
- SSE is **multi-consumer with replay**: every (re)connection replays the full history
  then follows the live stream (F5 / 2nd screen OK). History is unbounded (single-process, demo).
- `MIRA_DEMO_MODE=1` floors the gate timeout to 900s (the notice stays on screen).
- **CORS** open by default (dev) so a front on another origin (Next.js :3000)
  can call the API. Restrict as needed: `MIRA_CORS_ORIGINS="https://my-front"`.
