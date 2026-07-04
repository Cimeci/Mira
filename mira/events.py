"""Événements structurés du pipeline — LE contrat entre le core (L1) et le reste du monde.

Lane L1. Chaque transition de la state machine (types.Status) émet un `StageEvent` via un
callback `Emit` injecté dans `orchestrator.run` et dans chaque stage. C'est la colonne
vertébrale du flux temps réel :
  - L2 (backend) sérialise chaque StageEvent en SSE — `event.to_dict()` donne le dict
    JSON-serializable canonique (un seul sérialiseur, pas de divergence entre lanes) ;
  - L3 (UI) affiche la timeline à partir de `to_status` + `payload` (et `detail` en fallback).

Schéma d'un StageEvent
----------------------
  case_id     : str            — id opaque du dossier (aucune PII, cf. types.Mandate).
  stage       : str            — module émetteur : "mandate" | "locator" | "analyzer"
                                 | "notifier" | "notice" (aperçu pré-gate de la notice,
                                 émis par l'orchestrateur). Sert au groupage visuel côté UI.
  from_status : Status | None  — état AVANT la transition ; None uniquement pour MANDATED
                                 (naissance du case, pas d'état antérieur).
  to_status   : Status         — état APRÈS la transition. C'est LA clé de rendu côté L3.
  ts_utc      : datetime       — horodatage UTC (types.utcnow, source de temps unique).
  detail      : str            — la ligne texte historique de la CLI (ex. "[LOCATE] média
                                 in-scope trouvé : …"). Vide ("") pour les transitions qui
                                 n'avaient pas de ligne CLI (MANDATED, AWAITING_CONFIRM,
                                 CONFIRMED) : `print_emitter` ne les imprime pas, ce qui
                                 garantit une sortie `python -m mira.demo` inchangée.
  payload     : dict           — faits structurés de la transition (voir règle ci-dessous).

Transitions émises (ordre nominal d'un run happy path)
------------------------------------------------------
  MANDATED          orchestrator, 1x par run     — payload {requester_role, scope_urls}
  LOCATED           locator, 1x par média émis   — payload {url}
  VERIFIED          analyzer, 1x par média       — payload {url, score, phash, sha256}
  REJECTED          analyzer (score < seuil)     — payload {url, score}
  ESCALATED         analyzer (mineur suspecté)   — payload {reason} — MINIMAL, voir G-6
  AWAITING_CONFIRM  émis 2x au stade VERIFIED (orchestrator.run_until_gate) :
                      1) stage "notice"   — payload {url, notice_text} : l'aperçu de la
                         notice pré-rédigée pour le panneau de confirmation L3 ;
                      2) stage "notifier" — payload {url} : le gate G-7 standard.
                    (en appel DIRECT de notifier.notify, seul le 2) est émis)
  CONFIRMED         notifier, victime approuve   — payload {url}
  DECLINED          notifier, victime refuse     — payload {url} ; run s'arrête là
  NOTIFIED          notifier, après dispatch     — payload {url}
  FAILED            PAS ENCORE ÉMIS — arrive avec la tâche l1-failed-handling
  REVOKED           PAS ENCORE ÉMIS — arrive avec la tâche l1-revoke-purge

Règle de contenu du payload (G-6 / G-12 — non négociable)
---------------------------------------------------------
  JAMAIS d'octets d'image ni de contenu média dans un payload — uniquement des faits :
  url / status / hash (phash, sha256) / score / reason.
  EXCEPTION UNIQUE — l'event stage "notice" porte `notice_text` : c'est NOTRE propre
  texte généré (template déterministe G-9, notifier.draft), jamais du contenu victime
  et jamais d'octets média. Aucun autre event ne transporte le texte de la notice.
  Cas ESCALATED : événement MINIMAL — case_id + reason SEULEMENT ; pas d'URL du média,
  phash/sha absents (rien n'a été téléchargé ni hashé, par design G-6).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime

from .types import Status, utcnow


@dataclass(frozen=True)
class StageEvent:
    """Un fait immuable : « le case X est passé à l'état Y ». Schéma détaillé en tête de module."""

    case_id: str
    stage: str
    from_status: Status | None
    to_status: Status
    ts_utc: datetime
    detail: str = ""
    payload: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Forme JSON-serializable canonique (SSE côté L2). Status -> str, datetime -> ISO."""
        return {
            "case_id": self.case_id,
            "stage": self.stage,
            "from_status": self.from_status.value if self.from_status else None,
            "to_status": self.to_status.value,
            "ts_utc": self.ts_utc.isoformat(),
            "detail": self.detail,
            "payload": self.payload,
        }


# Contrat d'injection : les stages ne savent pas QUI écoute (print, SSE, collecteur de test).
Emit = Callable[[StageEvent], None]


def make_event(
    case_id: str,
    stage: str,
    to_status: Status,
    *,
    from_status: Status | None = None,
    detail: str = "",
    payload: dict | None = None,
) -> StageEvent:
    """Fabrique un StageEvent horodaté — un seul endroit stampe ts_utc (source unique)."""
    return StageEvent(
        case_id=case_id,
        stage=stage,
        from_status=from_status,
        to_status=to_status,
        ts_utc=utcnow(),
        detail=detail,
        payload=payload or {},
    )


def print_emitter(event: StageEvent) -> None:
    """Adaptateur par défaut (rétro-compat CLI exacte) : imprime la ligne texte historique.

    Les événements sans équivalent CLI (detail vide) restent silencieux, donc la sortie
    de `python -m mira.demo` est identique au comportement pré-events.
    """
    if event.detail:
        print(event.detail)
