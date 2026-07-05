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


def _headless() -> bool:
    """Headed (visible window) when MIRA_CU_HEADFUL is truthy; headless otherwise (default)."""
    return os.getenv("MIRA_CU_HEADFUL", "").strip().lower() not in {"1", "true", "yes"}


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
    if PROFILE_DIR.is_dir():
        context = await pw.chromium.launch_persistent_context(
            str(PROFILE_DIR), headless=_headless(), viewport=VIEWPORT
        )
        page = context.pages[0] if context.pages else await context.new_page()
        await page.route("**/*", _abort_out_of_scope)
        return page, context.close
    browser = await pw.chromium.launch(headless=_headless())
    page = await browser.new_page(viewport=VIEWPORT)
    await page.route("**/*", _abort_out_of_scope)
    return page, browser.close
