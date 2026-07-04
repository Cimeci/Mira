"""Escalade autorité — sink DÉMO-ONLY vers une inbox mock d'autorité (OFMIN/NCMEC-like).

Lane L1. G-12 : la démo ne cible JAMAIS une vraie plateforme ni une vraie autorité —
ce module écrit une ligne JSON structurée vers un sink mock, point. Le vrai (post-
hackathon) : dépôt via le canal officiel de l'autorité compétente, même interface.

Règle de contenu (G-6) : le signalement ne transporte JAMAIS le contenu ni l'URL du
média — uniquement {case_id, ts_utc, reason, authority}. L'analyzer n'a rien
téléchargé ni stocké sur un cas ESCALATED ; le sink ne doit rien exposer non plus.
"""

from __future__ import annotations

import json

from .events import Emit, print_emitter
from .types import ForensicRecord, Mandate, Status, utcnow

# Identifiant du sink de démo — rend explicite dans chaque log qu'aucune vraie
# autorité n'est contactée (G-12).
AUTHORITY_SINK = "mock-ofmin-inbox"


def escalate(
    record: ForensicRecord,
    mandate: Mandate,
    *,
    log=print,
    emit: Emit = print_emitter,
) -> None:
    """Signale un cas ESCALATED au sink autorité mock. Une ligne JSON, rien d'autre.

    `emit` est dans la signature pour que la surface SSE (L2) puisse brancher le
    signalement plus tard sans changer l'interface ; la transition ESCALATED a déjà
    été émise par l'analyzer, on ne ré-émet pas un état ici (contrat events.py).
    """
    if record.status is not Status.ESCALATED:
        # Fail-fast : escalader un cas non-ESCALATED est un bug d'orchestration.
        raise ValueError(f"escalate() refusé : record {record.case_id} non ESCALATED (G-6).")
    report = {
        "case_id": record.case_id,
        "ts_utc": utcnow().isoformat(),
        "reason": "suspected_minor",
        "authority": AUTHORITY_SINK,
    }
    log(f"[ESCALATE] signalement autorité (démo, G-12) : {json.dumps(report)}")
