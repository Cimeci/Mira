"""Surface HTTP L2 — pilote le pipeline Mira et streame chaque transition en SSE.

Lane L2 (backend). On ne touche PAS au cœur : ce module ne fait qu'exposer
`orchestrator.run_until_gate` / `orchestrator.dispatch` derrière HTTP + SSE, en
réutilisant le contrat d'événements (`mira.events.StageEvent`) comme colonne
vertébrale temps réel. Le nom `mira/api.py` suit PLAN.local (Δ3), et reste distinct
de `mira/web/` (surface scraper/CU, lane Ilan) pour éviter toute collision de merge.

Pourquoi couper le pipeline en deux (run_until_gate / dispatch) côté HTTP :
le gate G-7 (confirmation victime) doit tenir OUVERT entre deux requêtes — la notice
s'affiche, puis un humain décide. On lance donc le pipeline en tâche de fond ; il se
bloque au gate sur un `asyncio.Future` que `POST /confirm` vient résoudre.

Flux de démo (beat 2/3, sur mocks) :
  POST /cases                    -> crée un case, lance le pipeline en tâche de fond
  GET  /cases/{id}/events (SSE)  -> timeline temps réel : un message par transition
  POST /cases/{id}/confirm       -> résout le gate G-7 (verdict victime) -> dispatch
  GET  /healthz                  -> sonde de vie

Contrat SSE (un objet JSON par `data:`), discriminé par `kind` :
  {"kind":"stage",  "event": StageEvent.to_dict()}      — transition d'état (rendu L3)
  {"kind":"notice", "case_id","url","text"}             — notice DSA à valider (gate G-7)
  {"kind":"done",   "case_id","statuses":{url:status}}  — pipeline terminé, flux fermé
  {"kind":"error",  "case_id","message"}                — exception -> event terminal

La notice DSA ne transite JAMAIS dans un `StageEvent` (règle G-6, cf. mira/events.py) :
elle passe par le canal du gate (`kind:"notice"`), fourni par le Notifier au callback
`confirm`. Aucun octet d'image ni PII ne circule ici — uniquement url / statut / notice.
"""

from __future__ import annotations

import asyncio
import json
import os
import secrets
from collections.abc import AsyncIterator
from dataclasses import dataclass, field

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from .events import StageEvent
from .mandate import capture_consent, create_demo_mandate
from .orchestrator import ConsentError, dispatch, run_until_gate
from .types import Mandate, Status

app = FastAPI(title="Mira — API pipeline (L2)")

# CORS : le front (L3) tourne sur une autre origine (ex. Next.js :3000) ; sans ça, le
# navigateur bloque tout appel à l'API. Permissif par défaut (dev/démo), restreignable
# via MIRA_CORS_ORIGINS="https://a,https://b". Pas d'auth par cookie ici -> credentials
# désactivé (contrainte : interdit de combiner allow_origins=["*"] et credentials).
_origins = os.getenv("MIRA_CORS_ORIGINS", "*").strip()
_cors_origins = ["*"] if _origins == "*" else [o.strip() for o in _origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Sentinelle de fin de flux : distingue « plus d'événements » d'un message vide.
_STREAM_END = object()


@dataclass
class CaseRun:
    """État en mémoire d'un case en cours. Mono-process, suffisant pour la démo.

    `queue` : messages SSE prêts à pousser (dict, ou _STREAM_END pour fermer le flux).
    `confirmations` : un Future par média en attente du gate G-7, clé = source_url.
    """

    case_id: str
    queue: asyncio.Queue = field(default_factory=asyncio.Queue)
    confirmations: dict[str, asyncio.Future[bool]] = field(default_factory=dict)
    finished: bool = False


# Registre des cases. Pas de purge (hackathon, mono-process) : à remettre à plat au
# redémarrage. Le case_id est opaque (aucune PII, cf. contrat types.Mandate).
_RUNS: dict[str, CaseRun] = {}


class CaseRequest(BaseModel):
    """Corps optionnel de POST /cases. Sans scope_urls -> mandat de démo pré-autorisé."""

    case_id: str | None = None
    requester_role: str = "victim"
    scope_urls: list[str] | None = None
    attestation: bool = True


class Verdict(BaseModel):
    """Corps de POST /confirm : le verdict humain du gate G-7."""

    approved: bool = True
    url: str | None = Field(
        default=None,
        description="média visé ; si absent, résout la première confirmation en attente.",
    )


def _new_case_id() -> str:
    """Id opaque, sans PII, unique par process (secrets -> pas de collision pratique)."""
    return f"case-{secrets.token_hex(4)}"


def _build_mandate(req: CaseRequest, case_id: str) -> Mandate:
    """Construit le mandat depuis la requête, ou retombe sur le mandat de démo (G-12).

    Les erreurs de consentement/scope remontent en 400 (fail-fast aux frontières) :
    un mandat invalide ne doit jamais devenir un case silencieux.
    """
    if req.scope_urls is None:
        return create_demo_mandate(case_id=case_id)
    try:
        return capture_consent(
            case_id=case_id,
            requester_role=req.requester_role,
            scope_urls=req.scope_urls,
            attestation=req.attestation,
        )
    except (ConsentError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _confirm_for(run: CaseRun, source_url: str):
    """Fabrique le callback `confirm` async attendu par le Notifier (gate G-7).

    Il pousse la notice au front (canal du gate) puis attend le verdict humain via un
    Future résolu par POST /confirm. Le timeout fail-closed est géré côté notifier
    (config.CONFIRM_TIMEOUT_S) : ici on attend simplement.
    """
    fut: asyncio.Future[bool] = asyncio.get_running_loop().create_future()
    run.confirmations[source_url] = fut

    async def confirm(notice: str) -> bool:
        await run.queue.put(
            {"kind": "notice", "case_id": run.case_id, "url": source_url, "text": notice}
        )
        return await fut

    return confirm


async def _run_pipeline(run: CaseRun, mandate: Mandate) -> None:
    """Tâche de fond : déroule le pipeline et déverse chaque transition dans la queue SSE."""

    def emit(event: StageEvent) -> None:
        # emit est sync (contrat events.Emit) ; put_nowait sur queue non bornée = sûr.
        run.queue.put_nowait({"kind": "stage", "event": event.to_dict()})

    try:
        records = await run_until_gate(mandate, emit=emit)
        statuses: dict[str, str] = {r.source_url: r.status.value for r in records}
        for record in records:
            if record.status is Status.VERIFIED:
                confirm = _confirm_for(run, record.source_url)
                result = await dispatch(record, mandate, confirm=confirm, emit=emit)
                statuses[result.source_url] = result.status.value
        await run.queue.put({"kind": "done", "case_id": run.case_id, "statuses": statuses})
    except Exception as exc:  # noqa: BLE001 — toute panne devient un event SSE terminal, jamais un silence
        await run.queue.put(
            {"kind": "error", "case_id": run.case_id, "message": f"{type(exc).__name__}: {exc}"}
        )
    finally:
        run.finished = True
        await run.queue.put(_STREAM_END)


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/cases")
async def create_case(req: CaseRequest | None = None) -> dict[str, str]:
    """Crée un case, lance le pipeline en tâche de fond, renvoie ses URLs de suivi."""
    req = req or CaseRequest()
    case_id = req.case_id or _new_case_id()
    if case_id in _RUNS:
        raise HTTPException(status_code=409, detail=f"case_id déjà utilisé : {case_id}")
    mandate = _build_mandate(req, case_id)
    run = CaseRun(case_id=case_id)
    _RUNS[case_id] = run
    asyncio.create_task(_run_pipeline(run, mandate))
    return {
        "case_id": case_id,
        "events_url": f"/cases/{case_id}/events",
        "confirm_url": f"/cases/{case_id}/confirm",
    }


@app.get("/cases/{case_id}/events")
async def stream_events(case_id: str) -> StreamingResponse:
    """Flux SSE des messages du case (single-consumer : un front à la fois en démo)."""
    run = _RUNS.get(case_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"case inconnu : {case_id}")

    async def gen() -> AsyncIterator[str]:
        while True:
            msg = await run.queue.get()
            if msg is _STREAM_END:
                break
            yield f"data: {json.dumps(msg, ensure_ascii=False)}\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")


@app.post("/cases/{case_id}/confirm")
async def confirm_case(case_id: str, verdict: Verdict) -> dict[str, object]:
    """Résout le gate G-7 : transmet le verdict humain au pipeline en attente."""
    run = _RUNS.get(case_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"case inconnu : {case_id}")

    fut = _pick_confirmation(run, verdict.url)
    if fut is None:
        raise HTTPException(status_code=409, detail="aucune confirmation en attente pour ce case")
    if fut.done():
        raise HTTPException(status_code=409, detail="confirmation déjà tranchée")
    fut.set_result(verdict.approved)
    return {"case_id": case_id, "approved": verdict.approved}


def _pick_confirmation(run: CaseRun, url: str | None) -> asyncio.Future[bool] | None:
    """Le Future ciblé par `url`, ou la première confirmation encore en attente."""
    if url is not None:
        return run.confirmations.get(url)
    for fut in run.confirmations.values():
        if not fut.done():
            return fut
    return None


def main() -> None:
    """Lanceur local : `python -m mira.api` (équivalent `uvicorn mira.api:app`)."""
    import uvicorn

    uvicorn.run("mira.api:app", host="127.0.0.1", port=8000, reload=False)


if __name__ == "__main__":
    main()
