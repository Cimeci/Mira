"""Stage 1 — Le Locator. Trouve le média DANS le périmètre du mandat, uniquement.

Lane L1. Le vrai : browser-use (LLM) + Playwright, contexte read-only, aucune
navigation hors scope (G-2). Ici : mock déterministe pour une démo stable (premortem T3).
"""

from __future__ import annotations

import asyncio

from .types import Mandate, MediaItem, Status


async def locate(mandate: Mandate, out: asyncio.Queue[MediaItem], *, log=print) -> None:
    """Émet des MediaItem in-scope dans la queue partagée."""
    # G-1 garanti en amont : orchestrator._require_active est le SEUL point de contrôle
    # (un assert ici serait strippé sous `python -O` — fausse sécurité).
    for url in mandate.scope_urls:
        media_url = f"{url}/synthetic_test.jpg"  # MOCK : on prétend avoir trouvé un média
        log(f"[LOCATE] média in-scope trouvé : {media_url}")
        await out.put(MediaItem(case_id=mandate.case_id, url=media_url, status=Status.LOCATED))
        await asyncio.sleep(0)  # yield au runtime async
