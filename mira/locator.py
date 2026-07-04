"""Stage 1 — Le Locator. Trouve le média DANS le périmètre du mandat, uniquement.

Lane L1. Le vrai : browser-use (LLM) + Playwright, contexte read-only, aucune
navigation hors scope (G-2). Ici : mock déterministe pour une démo stable (premortem T3).
G-2 est appliqué par du code, pas par une promesse : chaque candidat passe par
`is_in_scope` avant émission — hors-scope = rejeté et loggé, jamais mis en queue.
"""

from __future__ import annotations

import asyncio
from urllib.parse import urlparse

from .types import Mandate, MediaItem, Status

# Génère un candidat hors-scope pour rendre le rejet G-2 visible en démo (beat 2).
SHOW_SCOPE_ENFORCEMENT = True
_OUT_OF_SCOPE_DECOY = "https://evil-mirror.example/leak.jpg"


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


async def locate(mandate: Mandate, out: asyncio.Queue[MediaItem], *, log=print) -> None:
    """Émet des MediaItem in-scope dans la queue partagée. Hors-scope = rejeté, jamais émis."""
    # G-1 garanti en amont : orchestrator._require_active est le SEUL point de contrôle
    # (un assert ici serait strippé sous `python -O` — fausse sécurité).
    # rstrip évite `host//fichier` si le scope a un trailing slash.
    candidates = [f"{url.rstrip('/')}/synthetic_test.jpg" for url in mandate.scope_urls]
    if SHOW_SCOPE_ENFORCEMENT:
        candidates.append(_OUT_OF_SCOPE_DECOY)  # doit être rejeté ci-dessous, preuve vivante de G-2
    for media_url in candidates:
        if not is_in_scope(media_url, mandate.scope_urls):
            log(f"[LOCATE] hors-scope rejeté (G-2): {media_url}")
            continue
        log(f"[LOCATE] média in-scope trouvé : {media_url}")
        await out.put(MediaItem(case_id=mandate.case_id, url=media_url, status=Status.LOCATED))
        await asyncio.sleep(0)  # yield au runtime async
