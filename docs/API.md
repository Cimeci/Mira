# API Mira — surface HTTP L2 (`mira/api.py`)

Backend qui pilote le pipeline (`mira.orchestrator`) et streame chaque transition en SSE.
Sur **mocks** de bout en bout — aucun vrai host, aucune vraie image (G-12).

Lancer : `python -m mira.api` (ou `uvicorn mira.api:app --reload`) → `http://127.0.0.1:8000`.

> Distinct de `mira/web/` (surface scraper/Computer Use, lane Ilan). Les deux
> cohabitent sans se marcher dessus : `api` = pipeline, `web` = locator CU.

## Endpoints

| Méthode | Route | Rôle |
|--------|-------|------|
| `GET`  | `/healthz` | sonde de vie → `{"status":"ok"}` |
| `POST` | `/cases` | crée un case, lance le pipeline en tâche de fond |
| `GET`  | `/cases/{id}` | **état courant** du case (à lire au montage du front) |
| `GET`  | `/cases/{id}/events` | flux **SSE**, rejoué du début à chaque (re)connexion |
| `POST` | `/cases/{id}/confirm` | verdict victime au gate G-7 |

### `GET /cases/{id}`

État à consulter au montage de la page (ou après un F5) pour se resynchroniser sans
attendre le SSE :

```json
{ "case_id":"…", "finished":false, "current_status":"AWAITING_CONFIRM",
  "statuses":{}, "awaiting_confirm":["https://…/x.jpg"],
  "pending_notice":{"url":"https://…/x.jpg","text":"Objet : …"},
  "events_url":"…", "confirm_url":"…" }
```

`pending_notice` est non-null uniquement quand le gate G-7 est ouvert (à afficher +
proposer Approuver/Refuser). `statuses` se remplit à la fin (`done`).

### `POST /cases`

Corps **optionnel** (sans corps → mandat de démo pré-autorisé sur le mock host) :

```json
{ "case_id": "case-…", "requester_role": "victim",
  "scope_urls": ["https://mock-host.local/target"], "attestation": true }
```

`requester_role` ∈ `victim | legal_rep | authorized_ngo`. Scope invalide / attestation
manquante → **400** (fail-fast, cf. `mandate.capture_consent`). Réponse :

```json
{ "case_id":"case-ab12cd34",
  "events_url":"/cases/case-ab12cd34/events",
  "confirm_url":"/cases/case-ab12cd34/confirm" }
```

### `GET /cases/{id}/events` (SSE)

Un objet JSON par `data:`, discriminé par `kind` :

```
{"kind":"stage",  "event": <StageEvent.to_dict()>}       # transition d'état (rendu timeline)
{"kind":"notice", "case_id":"…","url":"…","text":"…"}    # notice DSA à valider (gate G-7)
{"kind":"done",   "case_id":"…","statuses":{url:status}} # terminé → le flux se ferme
{"kind":"error",  "case_id":"…","message":"…"}           # exception → event terminal
```

`StageEvent.to_dict()` = `{case_id, stage, from_status, to_status, ts_utc, detail, payload}`
(schéma gelé dans `mira/events.py`). La **notice DSA ne transite jamais dans un `stage`**
(règle G-6) : elle arrive via `kind:"notice"`, au moment où le gate s'ouvre.

Séquence nominale (happy path) :
`MANDATED → LOCATED → VERIFIED → AWAITING_CONFIRM → [notice] → CONFIRMED → NOTIFIED → [done]`

### `POST /cases/{id}/confirm`

```json
{ "approved": true, "url": "https://mock-host.local/target/synthetic_test.jpg" }
```

`url` optionnelle (par défaut : première confirmation en attente). `approved:false` ou
silence > `MIRA_CONFIRM_TIMEOUT_S` → **DECLINED**, rien n'est envoyé (fail-closed, G-7).

## Exemple (curl)

```bash
CID=$(curl -s -XPOST localhost:8000/cases | python -c 'import sys,json;print(json.load(sys.stdin)["case_id"])')
curl -N localhost:8000/cases/$CID/events &          # timeline SSE
curl -s -XPOST localhost:8000/cases/$CID/confirm -H 'content-type: application/json' -d '{"approved":true}'
```

## Limites connues (assumées — hackathon)

- État **en mémoire, mono-process** : redémarrage = reset ; pas de purge des cases.
- SSE **multi-consumer avec replay** : chaque (re)connexion rejoue l'historique complet
  puis suit le live (F5 / 2ᵉ écran OK). L'historique n'est pas borné (mono-process, démo).
- `MIRA_DEMO_MODE=1` plancher le timeout du gate à 900 s (la notice reste à l'écran).
- **CORS** ouvert par défaut (dev) pour qu'un front sur une autre origine (Next.js :3000)
  puisse appeler l'API. Restreindre au besoin : `MIRA_CORS_ORIGINS="https://mon-front"`.
