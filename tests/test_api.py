"""Non-régression du chemin de démo exposé par mira/api.py (lane L2).

On teste LA colonne vertébrale : le pipeline branché sur le pub/sub SSE, et le gate G-7
résolu exactement comme le ferait `POST /confirm` (on set le Future de confirmation).
Pas de vrai socket ni de concurrence HTTP — on s'abonne à un case et on pilote
`_run_pipeline` en direct, ce qui rend le test déterministe. C'est le seul chemin qui
doit rester vert : 5 sessions touchent ce repo en parallèle, ce test garde le contrat.

Skip auto si FastAPI n'est pas installé (le squelette tourne stdlib-only ; l'API est
une dépendance de la seule lane L2).
"""

import asyncio

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient  # noqa: E402

import mira.api as api  # noqa: E402
from mira.api import _STREAM_END, CaseRun, _run_pipeline, app  # noqa: E402
from mira.mandate import create_demo_mandate  # noqa: E402
from mira.types import ForensicRecord, NotificationRecord, Status, utcnow  # noqa: E402


async def _drive(approved: bool) -> dict:
    """Déroule un case complet en s'abonnant comme un flux SSE ; répond `approved` au gate."""
    run = CaseRun(case_id="test-drive")
    mandate = create_demo_mandate("test-drive")
    queue: asyncio.Queue = asyncio.Queue()
    run.subscribers.add(queue)  # abonné avant le lancement -> reçoit tous les events
    task = asyncio.create_task(_run_pipeline(run, mandate))
    statuses: dict = {}
    stages: list[str] = []
    while True:
        msg = await queue.get()
        if msg is _STREAM_END:
            break
        if msg["kind"] == "stage":
            stages.append(msg["event"]["to_status"])
        elif msg["kind"] == "notice":
            # Ce que fait POST /confirm : résout le gate avec le verdict humain.
            run.confirmations[msg["url"]].set_result(approved)
        elif msg["kind"] == "done":
            statuses = msg["statuses"]
    await task
    return {"statuses": statuses, "stages": stages, "run": run}


def test_confirm_path_reaches_notified():
    result = asyncio.run(_drive(approved=True))
    assert "NOTIFIED" in result["statuses"].values()
    # La timeline passe bien par le gate AVANT l'envoi, et NOTIFIED est l'état terminal.
    assert "AWAITING_CONFIRM" in result["stages"]
    assert result["stages"][-1] == "NOTIFIED"


def test_decline_path_sends_nothing():
    result = asyncio.run(_drive(approved=False))
    assert "DECLINED" in result["statuses"].values()
    # Fail-closed : sur refus, rien n'est jamais envoyé.
    assert "NOTIFIED" not in result["statuses"].values()


def test_history_replays_full_timeline_after_run():
    """Robustesse F5 : un abonné tardif doit pouvoir rejouer toute la timeline."""
    run = asyncio.run(_drive(approved=True))["run"]
    # L'historique = ce que stream_events rejoue à une (re)connexion tardive.
    stages = [m["event"]["to_status"] for m in run.history if m["kind"] == "stage"]
    assert stages[0] == "MANDATED"
    assert stages[-1] == "NOTIFIED"
    assert run.finished is True
    assert run.statuses  # état final consultable via GET /cases/{id}
    assert run.pending_notice is None  # gate refermé -> plus de notice en attente


def test_case_id_path_traversal_rejected():
    """Frontière API : un case_id porteur de traversée de chemin est rejeté en 400
    AVANT toute écriture d'artefact de consentement (.mira_consent/<case_id>.json)."""
    client = TestClient(app)
    # NB : case_id="" n'est pas ici — falsy, il retombe sur l'id généré (comme None).
    for evil in ("../../../../tmp/pwned", "a/b", "x" * 65, "café", "a\\b"):
        resp = client.post("/cases", json={"case_id": evil, "attestation": True})
        assert resp.status_code == 400, f"case_id {evil!r} aurait dû être rejeté"
        assert evil not in api._RUNS


def test_scope_urls_outside_allowlist_rejected():
    """G-2/G-12 à la frontière API : un scope hors allow-list démo est rejeté en 400 —
    l'API ne doit jamais permettre de viser un vrai host, même quand le locator
    deviendra réel (PR #17)."""
    client = TestClient(app)
    resp = client.post(
        "/cases",
        json={"case_id": "scope-evil", "scope_urls": ["https://vrai-site.example/x"]},
    )
    assert resp.status_code == 400
    assert "scope-evil" not in api._RUNS


def test_scope_urls_on_allowlist_accepted():
    """Le host de démo (mock-host.local) passe l'allow-list : le chemin nominal reste ouvert."""
    # Unitaire (pas de POST) : on valide _build_mandate sans lancer de tâche de fond.
    req = api.CaseRequest(scope_urls=["https://mock-host.local/target/"], attestation=True)
    mandate = api._build_mandate(req, "scope-ok")
    assert mandate.scope_urls == ["https://mock-host.local/target/"]


def test_l1_stack_tuple_contract_passes_prewritten_notice_to_dispatch(monkeypatch):
    """Compat pile L1 (PR #12) : run_until_gate renverra (records, notices) — l'API doit
    dépaqueter le tuple et passer la notice pré-rédigée TELLE QUELLE à dispatch
    (garantie aperçu == envoyé, octet pour octet)."""
    record = ForensicRecord(
        case_id="tuple-case",
        source_url="https://mock-host.local/target/x.jpg",
        deepfake_score=0.94,
        perceptual_hash="phash:x",
        sha256_hash="sha",
        discovery_ts_utc=utcnow(),
        status=Status.VERIFIED,
    )
    prewritten = "NOTICE PRÉ-RÉDIGÉE — doit arriver telle quelle à dispatch"

    async def fake_run_until_gate(mandate, *, emit):
        return [record], {record.source_url: prewritten}

    seen: dict = {}

    async def fake_dispatch(rec, mandate, notice=None, *, confirm, emit):
        seen["notice"] = notice
        return NotificationRecord(
            case_id=rec.case_id,
            source_url=rec.source_url,
            host_contact="abuse@mock-host.local",
            notice_text=notice or "",
            dispatched_ts_utc=utcnow(),
            status=Status.NOTIFIED,
        )

    monkeypatch.setattr(api, "run_until_gate", fake_run_until_gate)
    monkeypatch.setattr(api, "dispatch", fake_dispatch)

    run = CaseRun(case_id="tuple-case")
    asyncio.run(_run_pipeline(run, create_demo_mandate("tuple-case")))

    assert seen["notice"] == prewritten
    assert run.statuses[record.source_url] == "NOTIFIED"
    assert run.finished is True
