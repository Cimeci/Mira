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
  GET  /cases/{id}               -> état courant du case (pour un montage propre du front)
  GET  /cases/{id}/events (SSE)  -> timeline, REJOUÉE du début à chaque (re)connexion
  POST /cases/{id}/confirm       -> résout le gate G-7 (verdict victime) -> dispatch
  GET  /healthz                  -> sonde de vie

Reconnexion / F5 (robustesse démo) : chaque case garde l'historique append-only de ses
messages et le rejoue à toute nouvelle connexion SSE, puis diffuse le live à CHAQUE
abonné (fan-out — plusieurs onglets/écrans sans se voler d'events). Un rafraîchissement
de page ne repart donc pas d'une timeline vide.

Contrat SSE (un objet JSON par `data:`), discriminé par `kind` :
  {"kind":"stage",  "event": StageEvent.to_dict()}      — transition d'état (rendu L3)
  {"kind":"notice", "case_id","url","text"}             — notice DSA à valider (gate G-7)
  {"kind":"done",   "case_id","statuses":{url:status}}  — pipeline terminé, flux fermé
  {"kind":"error",  "case_id","message"}                — exception -> event terminal

Canal de la notice DSA : elle passe par le gate (`kind:"notice"`, fourni par le Notifier
au callback `confirm`). La pile L1 (PR #12) ajoute AUSSI un StageEvent stage='notice'
pré-gate portant notice_text — exception unique documentée dans mira/events.py ; les
deux canaux portent le MÊME texte (une seule rédaction, notifier.draft). Aucun octet
d'image ni PII ne circule ici — uniquement url / statut / notice.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import secrets
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from urllib.parse import urlparse

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from . import store
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

# Sentinelle de fin de flux : marqueur de contrôle poussé aux abonnés (jamais dans
# l'historique), pour distinguer « le case est terminé » d'un message vide.
_STREAM_END = object()

# Statuts au-delà desquels le gate n'est plus ouvert : la notice en attente est purgée.
_GATE_CLOSED = frozenset({"CONFIRMED", "DECLINED", "NOTIFIED"})


@dataclass
class CaseRun:
    """État en mémoire d'un case. Mono-process, suffisant pour la démo.

    Modèle pub/sub minimal pour survivre à un F5 :
      `history`     — tous les messages publiés (append-only), rejoués à la connexion ;
      `subscribers` — une file par flux SSE actif (fan-out : plusieurs écrans possibles) ;
      `confirmations` — un Future par média au gate G-7, clé = source_url (inchangé) ;
      `pending_notice` / `last_status` / `statuses` — état courant, exposé par GET /cases/{id}.
    """

    case_id: str
    history: list[dict] = field(default_factory=list)
    subscribers: set[asyncio.Queue] = field(default_factory=set)
    confirmations: dict[str, asyncio.Future[bool]] = field(default_factory=dict)
    finished: bool = False
    last_status: str | None = None
    pending_notice: dict | None = None
    statuses: dict[str, str] = field(default_factory=dict)


# Registre des cases. Pas de purge (hackathon, mono-process) : à remettre à plat au
# redémarrage. Le case_id est opaque (aucune PII, cf. contrat types.Mandate).
_RUNS: dict[str, CaseRun] = {}

# Références fortes sur les pipelines de fond : asyncio ne garde qu'une référence
# faible sur les Tasks — sans ce set, un case peut être garbage-collecté en plein vol
# (bloqué à jamais, sans log). Retiré automatiquement à la fin de chaque run.
_BACKGROUND_TASKS: set[asyncio.Task] = set()

# Le case_id vient du client et finit dans un chemin fichier (.mira_consent/<id>.json) :
# format strict à la frontière, tout le reste est un 400 (path traversal sinon).
_CASE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")

# G-2/G-12 à la frontière API : seuls les hosts de démo peuvent entrer dans un scope.
# Aujourd'hui le locator est un mock ; dès qu'il devient réel (PR #17), cette allow-list
# est la seule chose qui empêche POST /cases de faire crawler un vrai site.
_ALLOWED_SCOPE_HOSTS = frozenset(
    h.strip().lower()
    for h in os.getenv("MIRA_ALLOWED_SCOPE_HOSTS", "mock-host.local").split(",")
    if h.strip()
)


def _publish(run: CaseRun, msg: dict) -> None:
    """Ajoute un message à l'historique du case et le diffuse à tous les abonnés SSE.

    Sync (pas d'await) : appelable depuis l'emit du pipeline (contrat events.Emit).
    Met aussi à jour l'état courant lu par GET /cases/{id}.
    """
    run.history.append(msg)
    # Miroir durable (Supabase) — fire-and-forget : no-op sans clés, jamais bloquant.
    store.event_published(run.case_id, len(run.history) - 1, msg)
    kind = msg["kind"]
    if kind == "stage":
        run.last_status = msg["event"]["to_status"]
        if run.last_status in _GATE_CLOSED:
            run.pending_notice = None  # le gate s'est refermé (accepté/refusé)
    elif kind == "notice":
        run.pending_notice = {"url": msg["url"], "text": msg["text"]}
    elif kind == "done":
        run.statuses = msg["statuses"]
        run.pending_notice = None
    for q in run.subscribers:
        q.put_nowait(msg)


def _close(run: CaseRun) -> None:
    """Signale la fin du flux à tous les abonnés actifs (marqueur hors historique)."""
    for q in run.subscribers:
        q.put_nowait(_STREAM_END)


def _sse(msg: dict) -> str:
    return f"data: {json.dumps(msg, ensure_ascii=False)}\n\n"


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
    for url in req.scope_urls:
        host = (urlparse(url).hostname or "").lower()
        if host not in _ALLOWED_SCOPE_HOSTS:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"scope hors allow-list démo (G-2/G-12) : {host or url!r} — "
                    "hosts autorisés via MIRA_ALLOWED_SCOPE_HOSTS"
                ),
            )
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

    Il publie la notice (canal du gate) puis attend le verdict humain via un Future
    résolu par POST /confirm. Le timeout fail-closed est géré côté notifier
    (config.CONFIRM_TIMEOUT_S) : ici on attend simplement.
    """
    fut: asyncio.Future[bool] = asyncio.get_running_loop().create_future()
    run.confirmations[source_url] = fut

    async def confirm(notice: str) -> bool:
        _publish(run, {"kind": "notice", "case_id": run.case_id, "url": source_url, "text": notice})
        return await fut

    return confirm


async def _run_pipeline(run: CaseRun, mandate: Mandate) -> None:
    """Tâche de fond : déroule le pipeline et diffuse chaque transition aux abonnés SSE."""

    def emit(event: StageEvent) -> None:
        _publish(run, {"kind": "stage", "event": event.to_dict()})

    try:
        gate_result = await run_until_gate(mandate, emit=emit)
        # Compat transitoire : la pile L1 (PR #12) fait renvoyer (records, notices) à
        # run_until_gate — avant son merge c'est encore une simple liste. Accepter les
        # deux formes garde main déployable quel que soit l'ordre d'atterrissage ;
        # à simplifier en dépaquetage direct une fois la pile L1 sur main.
        if isinstance(gate_result, tuple):
            records, notices = gate_result
        else:
            records, notices = gate_result, {}
        statuses: dict[str, str] = {r.source_url: r.status.value for r in records}
        for record in records:
            if record.status is Status.VERIFIED:
                confirm = _confirm_for(run, record.source_url)
                notice = notices.get(record.source_url)
                if notice is None:
                    result = await dispatch(record, mandate, confirm=confirm, emit=emit)
                else:
                    # La notice pré-rédigée passe TELLE QUELLE (positionnel, compat
                    # signature pré-pile) : aperçu == envoyé, octet pour octet.
                    result = await dispatch(record, mandate, notice, confirm=confirm, emit=emit)
                statuses[result.source_url] = result.status.value
        _publish(run, {"kind": "done", "case_id": run.case_id, "statuses": statuses})
    except Exception as exc:  # noqa: BLE001 — toute panne devient un event SSE terminal, jamais un silence
        _publish(
            run,
            {"kind": "error", "case_id": run.case_id, "message": f"{type(exc).__name__}: {exc}"},
        )
    finally:
        run.finished = True
        _close(run)


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/cases")
async def create_case(req: CaseRequest | None = None) -> dict[str, str]:
    """Crée un case, lance le pipeline en tâche de fond, renvoie ses URLs de suivi."""
    req = req or CaseRequest()
    case_id = req.case_id or _new_case_id()
    if not _CASE_ID_RE.fullmatch(case_id):
        # Fail-fast AVANT toute écriture : le case_id finit dans un chemin fichier.
        raise HTTPException(
            status_code=400,
            detail="case_id invalide : ^[A-Za-z0-9_-]{1,64}$ attendu",
        )
    if case_id in _RUNS:
        raise HTTPException(status_code=409, detail=f"case_id déjà utilisé : {case_id}")
    mandate = _build_mandate(req, case_id)
    run = CaseRun(case_id=case_id)
    _RUNS[case_id] = run
    store.case_created(mandate)
    task = asyncio.create_task(_run_pipeline(run, mandate))
    _BACKGROUND_TASKS.add(task)
    task.add_done_callback(_BACKGROUND_TASKS.discard)
    return {
        "case_id": case_id,
        "state_url": f"/cases/{case_id}",
        "events_url": f"/cases/{case_id}/events",
        "confirm_url": f"/cases/{case_id}/confirm",
    }


@app.get("/cases/{case_id}")
async def get_case(case_id: str) -> dict[str, object]:
    """État courant d'un case — ce que le front lit au montage pour se synchroniser."""
    run = _RUNS.get(case_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"case inconnu : {case_id}")
    return {
        "case_id": run.case_id,
        "finished": run.finished,
        "current_status": run.last_status,
        "statuses": run.statuses,
        # Gate ouvert ? La notice à afficher est dans pending_notice (None sinon).
        "awaiting_confirm": [url for url, fut in run.confirmations.items() if not fut.done()],
        "pending_notice": run.pending_notice,
        "events_url": f"/cases/{case_id}/events",
        "confirm_url": f"/cases/{case_id}/confirm",
    }


@app.get("/cases/{case_id}/events")
async def stream_events(case_id: str) -> StreamingResponse:
    """Flux SSE : rejoue l'historique complet à la connexion, puis suit le live.

    Fan-out : chaque connexion a sa PROPRE file (pas de vol d'events entre onglets/F5).
    """
    run = _RUNS.get(case_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"case inconnu : {case_id}")

    async def gen() -> AsyncIterator[str]:
        queue: asyncio.Queue = asyncio.Queue()
        # S'abonner AVANT de figer le backlog : aucun await entre les deux -> pas de
        # course (mono-loop), donc ni event perdu ni doublon (le live va dans `queue`).
        run.subscribers.add(queue)
        backlog = list(run.history)
        already_done = run.finished
        try:
            for msg in backlog:
                yield _sse(msg)
            if already_done:
                return
            while True:
                msg = await queue.get()
                if msg is _STREAM_END:
                    break
                yield _sse(msg)
        finally:
            run.subscribers.discard(queue)

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
