"""Stage 1 — Le Locator. Trouve le média DANS le périmètre du mandat, uniquement.

Lane L1. Deux implémentations derrière la MÊME interface `locate()` :
  - MOCK (défaut) : candidat déterministe, aucun réseau, démo stable (premortem T3) ;
  - RÉEL (`MIRA_LOCATOR_REAL` truthy, hors `MIRA_DEMO_MODE`) : Gemini 2.5 Computer Use
    (cerveau) + Playwright (bras), read-only strict — voir `mira/locator_cu.py`.

`is_in_scope` est LE point d'enforcement de G-2 pour les DEUX chemins : chaque candidat
(mock ou renvoyé par le LLM) passe par ici avant émission — hors-scope = rejeté et loggé,
jamais mis en queue. `locator_cu` IMPORTE cette fonction, il ne la réimplémente pas.
"""

from __future__ import annotations

import asyncio
import os
from urllib.parse import urlparse

from .events import Emit, make_event, print_emitter
from .types import Mandate, MediaItem, Status

# Génère un candidat hors-scope pour rendre le rejet G-2 visible en démo (beat 2).
SHOW_SCOPE_ENFORCEMENT = True
_OUT_OF_SCOPE_DECOY = "https://evil-mirror.example/leak.jpg"

# Valeurs env considérées comme « désactivé » pour un flag booléen (aligné sur config._FALSY).
_FALSY = {"", "0", "false", "no"}


def _real_locator_enabled() -> bool:
    """Vrai si le Locator RÉEL (Gemini CU + Playwright) doit tourner à la place du mock.

    Fail-safe pour la démo : `MIRA_DEMO_MODE` truthy FORCE le mock quoi qu'il arrive
    (le chemin de démo live ne doit jamais dépendre d'un appel réseau, cf. go/no-go).
    Le réel ne s'active donc QUE si `MIRA_LOCATOR_REAL` est truthy ET qu'on n'est pas
    en mode démo.
    """
    if os.getenv("MIRA_DEMO_MODE", "").strip().lower() not in _FALSY:
        return False
    return os.getenv("MIRA_LOCATOR_REAL", "").strip().lower() not in _FALSY


def _path_segments(path: str) -> list[str]:
    """Découpe un path en segments non vides (gère trailing slash et path vide)."""
    return [segment for segment in path.split("/") if segment]


def is_in_scope(candidate_url: str, scope_urls: list[str]) -> bool:
    """Vrai si l'URL candidate est couverte par au moins une URL de scope (G-2).

    Couverte = même scheme + même host (netloc exact, insensible à la casse) ET
    path candidat préfixe de SEGMENTS du scope : `/target-evil` ne matche pas un
    scope `/target`, mais `/target/sub/x.jpg` oui.
    """
    candidate = urlparse(candidate_url)
    candidate_segments = _path_segments(candidate.path)
    for scope_url in scope_urls:
        scope = urlparse(scope_url)
        if candidate.scheme.lower() != scope.scheme.lower():
            continue
        if candidate.netloc.lower() != scope.netloc.lower():
            continue
        scope_segments = _path_segments(scope.path)
        if candidate_segments[: len(scope_segments)] == scope_segments:
            return True
    return False


async def locate(
    mandate: Mandate,
    out: asyncio.Queue[MediaItem],
    *,
    log=print,
    emit: Emit = print_emitter,
) -> None:
    """Point d'entrée du Stage 1 (interface gelée, appelée par l'orchestrateur).

    Aiguille vers le Locator RÉEL (Gemini CU + Playwright) si `MIRA_LOCATOR_REAL` est
    activé hors mode démo, sinon vers le mock déterministe. Le réel retombe LUI-MÊME
    proprement sur le mock en cas d'échec (réseau/API/navigateur) — voir `locator_cu` :
    ce point d'entrée reste donc toujours non-bloquant pour la démo.
    """
    if _real_locator_enabled():
        # Import différé : les deps lourdes (google-genai, playwright) ne sont chargées
        # QUE sur le chemin réel — le mock reste 100 % stdlib et sans effet de bord.
        from . import locator_cu

        await locator_cu.locate_real(mandate, out, log=log, emit=emit)
        return
    await _locate_mock(mandate, out, log=log, emit=emit)


async def _locate_mock(
    mandate: Mandate,
    out: asyncio.Queue[MediaItem],
    *,
    log=print,
    emit: Emit = print_emitter,
) -> None:
    """MOCK déterministe — émet des MediaItem in-scope. Hors-scope = rejeté, jamais émis.

    C'est aussi le FILET du chemin réel : `locator_cu.locate_real` rappelle cette
    fonction si la navigation Computer Use échoue, pour que la démo ne casse jamais.
    """
    # G-1 garanti en amont : orchestrator._require_active est le SEUL point de contrôle
    # (un assert ici serait strippé sous `python -O` — fausse sécurité).
    # rstrip évite `host//fichier` si le scope a un trailing slash.
    candidates = [f"{url.rstrip('/')}/synthetic_test.jpg" for url in mandate.scope_urls]
    if SHOW_SCOPE_ENFORCEMENT:
        candidates.append(_OUT_OF_SCOPE_DECOY)  # doit être rejeté ci-dessous, preuve vivante de G-2
    for media_url in candidates:
        if not is_in_scope(media_url, mandate.scope_urls):
            # Pas une transition d'état (rien n'entre dans le pipeline) -> log, pas d'event.
            log(f"[LOCATE] hors-scope rejeté (G-2): {media_url}")
            continue
        emit(make_event(
            mandate.case_id,
            "locator",
            Status.LOCATED,
            from_status=Status.MANDATED,
            detail=f"[LOCATE] média in-scope trouvé : {media_url}",
            payload={"url": media_url},
        ))
        await out.put(MediaItem(case_id=mandate.case_id, url=media_url, status=Status.LOCATED))
        await asyncio.sleep(0)  # yield au runtime async
