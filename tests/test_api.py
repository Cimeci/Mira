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

from mira.api import _STREAM_END, CaseRun, _run_pipeline  # noqa: E402
from mira.mandate import create_demo_mandate  # noqa: E402


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
