"""Ouverture du navigateur Playwright.

Si un profil persistant existe (`.mira_browser_profile/`, créé par
`scripts/browser_login.py`), on le réutilise → l'agent hérite des sessions que
l'humain a ouvertes (X, Insta…), sans jamais retaper de login. Sinon, navigateur
vierge. C'est le pattern « réutilise une session authentifiée » des agents web.
"""

from __future__ import annotations

import os
from collections.abc import Awaitable, Callable
from pathlib import Path

from playwright.async_api import Page, Playwright, Route

from . import guard
from .actions import VIEWPORT

PROFILE_DIR = Path(".mira_browser_profile")

# Valeurs env « désactivé » pour un flag booléen.
_FALSY = {"", "0", "false", "no"}


def _headless() -> bool:
    """Par défaut headless (spec §10 : le worker tourne en conteneur, sans écran).
    Mettre MIRA_CU_HEADLESS=0 pour VOIR la fenêtre Chromium s'ouvrir et naviguer —
    utile en démo locale pour montrer l'agent en action à l'écran."""
    return os.getenv("MIRA_CU_HEADLESS", "1").strip().lower() not in _FALSY

# Flags conteneur (spec §10) : Chromium tourne dans un Docker sans user namespaces
# (--no-sandbox) et avec un /dev/shm réduit → --disable-dev-shm-usage écrit les fichiers
# temp sur disque plutôt que de saturer la mémoire partagée et crasher la page.
# Sans danger hors conteneur : on isole déjà le navigateur au niveau réseau (route guard).
_LAUNCH_ARGS = ["--no-sandbox", "--disable-dev-shm-usage"]


async def _abort_out_of_scope(route: Route) -> None:
    """Défense en profondeur réseau (G-2/G-12) : avorte toute NAVIGATION de document
    vers un host hors allow-list — les sous-ressources (img/css/js) passent.

    C'est le verrou le plus fort : même si le profil persistant porte une session
    réelle (X, Insta…), une navigation vers ce host est avortée au niveau réseau,
    donc la session est inexploitable hors périmètre.
    """
    request = route.request
    if request.is_navigation_request() and not guard.is_allowed(request.url):
        await route.abort()
    else:
        await route.continue_()


async def open_page(pw: Playwright) -> tuple[Page, Callable[[], Awaitable[None]]]:
    """Renvoie (page, closer). Réutilise le profil persistant s'il existe.

    Toute page ouverte ici porte le garde-fou de périmètre réseau (route handler).
    """
    headless = _headless()
    if PROFILE_DIR.is_dir():
        context = await pw.chromium.launch_persistent_context(
            str(PROFILE_DIR), headless=headless, viewport=VIEWPORT, args=_LAUNCH_ARGS
        )
        page = context.pages[0] if context.pages else await context.new_page()
        await page.route("**/*", _abort_out_of_scope)
        return page, context.close
    browser = await pw.chromium.launch(headless=headless, args=_LAUNCH_ARGS)
    page = await browser.new_page(viewport=VIEWPORT)
    await page.route("**/*", _abort_out_of_scope)
    return page, browser.close
