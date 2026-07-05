"""Dispatch du scout Computer Use, PILOTÉ PAR UN CASE (Step 1 démo).

Le scout ne tourne jamais en standalone : `scout_case` est invoqué pour un `case_id`
donné, et chaque URL d'image extraite REVIENT dans l'état du case via le contrat
d'événements gelé (`mira.events.StageEvent`, transition LOCATED). C'est la seule
source de vérité ; la sortie terminal n'en est qu'un MIROIR (règle : le terminal ne
porte pas d'état caché, il reflète les events loggés).

Deux modes, une seule interface :
  - réel      : réutilise la boucle vision-action existante (`mira.cu.agent`), qui
                ouvre un Chromium Playwright headless, navigue, et récolte les <img>.
  - MIRA_DEMO_MODE : renvoie une liste d'URLs codée en dur SANS ouvrir le navigateur
                → la démo survit à une panne réseau / une absence de clé Gemini.
"""

from __future__ import annotations

import json
import os

from .cu.agent import stream_scrape_cu
from .cu.scraper import _validate_url
from .events import Emit, make_event
from .types import Status

# Valeurs env considérées comme « désactivé » (aligne config._FALSY).
_FALSY = {"", "0", "false", "no"}

# Port par défaut du serveur de fixture locale (voir fixtures/staged_case + README).
_FIXTURE_PORT = os.getenv("MIRA_FIXTURE_PORT", "8100")

# Fallback déterministe (MIRA_DEMO_MODE) : ce que le scout « verrait » sur la fixture,
# codé en dur pour ne dépendre ni du réseau ni de la clé Gemini. Reste ouvrable si le
# serveur de fixture tourne, mais aucune de ces URLs n'est requise pour logger.
DEMO_IMAGE_URLS: list[str] = [
    f"http://localhost:{_FIXTURE_PORT}/photo_01.png",
    f"http://localhost:{_FIXTURE_PORT}/photo_02.png",
    f"http://localhost:{_FIXTURE_PORT}/photo_03.png",
    f"http://localhost:{_FIXTURE_PORT}/photo_04.png",
]


def demo_mode() -> bool:
    """True si MIRA_DEMO_MODE est activé — le scout ne lance alors aucun navigateur."""
    return os.getenv("MIRA_DEMO_MODE", "").strip().lower() not in _FALSY


def _note(case_id: str, event: str, **fields: object) -> None:
    """Ligne structurée (JSON) sur le terminal — miroir des faits, jamais l'inverse.

    Utilisée pour ce qui n'est PAS une transition d'état (start, action de l'agent,
    résumé, erreur) : cohérent avec locator.py qui logge les non-transitions.
    """
    line = {"case_id": case_id, "stage": "scout", "event": event, **fields}
    print(json.dumps(line, ensure_ascii=False))


def _emit_image(case_id: str, url: str, emit: Emit) -> None:
    """Fait remonter UNE image extraite dans l'état du case (transition LOCATED)…

    …et en imprime le miroir structuré sur le terminal (une ligne par image, avec le
    case_id). L'event est la vérité ; `print` n'en est que le reflet.
    """
    ev = make_event(
        case_id,
        "scout",
        Status.LOCATED,
        from_status=Status.MANDATED,
        detail=f"[{case_id}] LOCATED image: {url}",
        payload={"url": url},
    )
    emit(ev)
    print(json.dumps(
        {"case_id": case_id, "stage": "scout", "event": "image_located", "url": url},
        ensure_ascii=False,
    ))


async def scout_case(case_id: str, url: str, *, emit: Emit) -> list[str]:
    """Dispatch le scout pour `case_id` sur `url` et renvoie les URLs d'images extraites.

    Chaque image extraite est repliée dans l'état du case via `emit` (LOCATED) et
    reflétée sur le terminal. En MIRA_DEMO_MODE, renvoie une liste codée en dur sans
    ouvrir de navigateur.
    """
    # Fail fast à l'entrée : http/https + host dans le périmètre autorisé (G-2/G-12).
    # Même verrou que la surface banc d'essai — aucun crawl sur une cible arbitraire.
    _validate_url(url)

    if demo_mode():
        _note(case_id, "start", mode="demo", url=url)
        for image_url in DEMO_IMAGE_URLS:
            _emit_image(case_id, image_url, emit)
        _note(case_id, "done", mode="demo", count=len(DEMO_IMAGE_URLS))
        return list(DEMO_IMAGE_URLS)

    _note(case_id, "start", mode="live", url=url, model_driver="gemini-cu")
    images: list[str] = []
    async for event in stream_scrape_cu(url):
        kind = event["type"]
        if kind == "action":
            # Action de l'agent (clic/scroll/…) : loggée, mais pas une transition d'état.
            _note(case_id, "action", name=event["name"])
        elif kind == "error":
            _note(case_id, "error", message=event["message"])
        elif kind == "done":
            for image in event["images"]:
                images.append(image["url"])
                _emit_image(case_id, image["url"], emit)
            _note(case_id, "done", mode="live", count=len(images), elapsed_s=event["elapsed"])
    return images
