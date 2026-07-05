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

from dotenv import dotenv_values
from playwright.async_api import Page, Playwright, Route

from . import guard
from .actions import VIEWPORT

PROFILE_DIR = Path(".mira_browser_profile")
_ENV_FILE = ".env.local"
# En mode visible, on ralentit chaque geste : sans ça l'agent clique/scrolle trop
# vite pour qu'on puisse suivre à l'œil « ce qu'il fait » pendant le tracking.
_HEADED_SLOWMO_MS = 250
# Flags conteneur (spec §10) : Chromium tourne dans un Docker sans user namespaces
# (--no-sandbox) et avec un /dev/shm réduit (--disable-dev-shm-usage écrit les temp
# sur disque au lieu de saturer la mémoire partagée et crasher la page). Sans effet
# de bord hors conteneur : le navigateur est déjà isolé au niveau réseau (route guard).
_CONTAINER_ARGS = ["--no-sandbox", "--disable-dev-shm-usage"]


def _env(name: str) -> str | None:
    """Lit une variable d'env, puis à défaut dans `.env.local` (même source que la
    clé API) — le toggle marche donc qu'on l'exporte au shell ou qu'on le pose dans
    le fichier d'env local."""
    return os.getenv(name) or dotenv_values(_ENV_FILE).get(name)


def _truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def _launch_kwargs() -> dict:
    """Options de lancement Playwright. Défaut = headless (serveur/démo, Cloud Run).
    `MIRA_HEADED=1` ouvre une vraie fenêtre pour suivre l'agent à l'œil ;
    `MIRA_CU_SLOWMO` (ms) force la vitesse des gestes."""
    headed = _truthy(_env("MIRA_HEADED"))
    slowmo_raw = _env("MIRA_CU_SLOWMO")
    slow_mo = (
        int(slowmo_raw)
        if slowmo_raw and slowmo_raw.isdigit()
        else (_HEADED_SLOWMO_MS if headed else 0)
    )
    return {"headless": not headed, "slow_mo": slow_mo, "args": _CONTAINER_ARGS}


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
            str(PROFILE_DIR), viewport=VIEWPORT, **_launch_kwargs()
        )
        page = context.pages[0] if context.pages else await context.new_page()
        await page.route("**/*", _abort_out_of_scope)
        return page, context.close
    browser = await pw.chromium.launch(**_launch_kwargs())
    page = await browser.new_page(viewport=VIEWPORT)
    await page.route("**/*", _abort_out_of_scope)
    return page, browser.close
