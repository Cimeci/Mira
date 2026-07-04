"""Ouverture du navigateur Playwright.

Si un profil persistant existe (`.mira_browser_profile/`, créé par
`scripts/browser_login.py`), on le réutilise → l'agent hérite des sessions que
l'humain a ouvertes (X, Insta…), sans jamais retaper de login. Sinon, navigateur
vierge. C'est le pattern « réutilise une session authentifiée » des agents web.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from pathlib import Path

from playwright.async_api import Page, Playwright

from .actions import VIEWPORT

PROFILE_DIR = Path(".mira_browser_profile")


async def open_page(pw: Playwright) -> tuple[Page, Callable[[], Awaitable[None]]]:
    """Renvoie (page, closer). Réutilise le profil persistant s'il existe."""
    if PROFILE_DIR.is_dir():
        context = await pw.chromium.launch_persistent_context(
            str(PROFILE_DIR), headless=True, viewport=VIEWPORT
        )
        page = context.pages[0] if context.pages else await context.new_page()
        return page, context.close
    browser = await pw.chromium.launch(headless=True)
    page = await browser.new_page(viewport=VIEWPORT)
    return page, browser.close
