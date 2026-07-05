"""Récolte d'images déterministe (Playwright pur, SANS LLM) — le Locator « fiable ».

Alternative rapide et déterministe au crawler agentique (`mira.cu.crawler`, Gemini
Computer Use) pour alimenter le pipeline : mêmes garde-fous G-2 (allow-list `guard` en
entrée, `is_in_scope` en aval côté locator), zéro coût API, zéro flakiness LLM. Le
crawler agentique reste le différenciateur du pitch (live view) ; celui-ci est le
chemin sûr pour un run end-to-end reproductible en démo.

Exploration bornée same-domain, mêmes curseurs que le crawler agentique :
  - MAX_PAGES  : plafond de pages visitées ;
  - MAX_DEPTH  : profondeur depuis l'URL de départ ;
  - MAX_LINKS  : liens suivis par page (anti-explosion combinatoire).
"""

from __future__ import annotations

from collections import deque

from playwright.async_api import async_playwright

from .browser import open_page
from .models import ScrapedImage
from .scraper import (
    _validate_url,
    extract_images,
    extract_links,
    normalize_url,
)

# Mêmes plafonds que le crawler agentique (mira.cu.crawler) — un crawl déterministe
# n'a pas de latence LLM, mais on borne quand même temps et coût réseau.
_MAX_PAGES = 6
_MAX_DEPTH = 2
_MAX_LINKS = 8
_GOTO_TIMEOUT_MS = 20_000


async def crawl_images(
    start_url: str,
    *,
    max_pages: int = _MAX_PAGES,
    max_depth: int = _MAX_DEPTH,
    max_links: int = _MAX_LINKS,
) -> list[ScrapedImage]:
    """Explore une surface bornée same-domain et renvoie les images de contenu, dédupliquées.

    `_validate_url` applique le verrou d'entrée G-2/G-12 (host allow-listé) AVANT
    d'ouvrir quoi que ce soit ; `open_page` pose en plus le garde-fou réseau qui avorte
    toute navigation de document hors périmètre. Le filtrage `is_in_scope` final reste
    la responsabilité de l'appelant (locator) — ici on récolte, on ne juge pas le scope.
    """
    _validate_url(start_url)
    start_url = normalize_url(start_url)

    frontier: deque[tuple[str, int]] = deque([(start_url, 0)])
    queued: set[str] = {start_url}   # dans la file ou déjà traité (anti-doublon)
    visited: set[str] = set()
    seen_images: set[str] = set()
    collected: list[ScrapedImage] = []

    async with async_playwright() as pw:
        page, close_browser = await open_page(pw)
        try:
            while frontier and len(visited) < max_pages:
                url, depth = frontier.popleft()
                if url in visited:
                    continue
                visited.add(url)

                await page.goto(url, wait_until="domcontentloaded", timeout=_GOTO_TIMEOUT_MS)

                for img in await extract_images(page):
                    if img.url in seen_images:
                        continue
                    seen_images.add(img.url)
                    collected.append(img)

                if depth < max_depth:
                    links = await extract_links(page, start_url)
                    fresh_links = [link for link in links if link not in queued][:max_links]
                    for link in fresh_links:
                        queued.add(link)
                        frontier.append((link, depth + 1))
        finally:
            await close_browser()

    return collected
