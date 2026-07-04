"""Crawler agentique borné — le Locator de Mira.

Le CODE tient la mémoire (file des liens à visiter, set des visités, limites) ;
le Computer Use fait ce qu'il fait de mieux : explorer chaque page (login, scroll,
imprévu). On découvre les liens same-domain de chaque page et on les enfile.

Garde-fous (sinon ça explose) :
  - MAX_PAGES  : plafond global de pages visitées (borne le temps ET le coût) ;
  - MAX_DEPTH  : profondeur d'exploration depuis l'URL de départ ;
  - MAX_LINKS  : liens suivis par page (anti-explosion combinatoire) ;
  - same_domain: on ne quitte jamais l'hôte de départ (= G-2 de Mira).
"""

from __future__ import annotations

import time
from collections import deque
from collections.abc import AsyncIterator
from dataclasses import replace

from google import genai
from google.genai import types
from playwright.async_api import async_playwright

from .agent import _api_key, _config, _run_cu_loop
from .browser import open_page
from .scraper import _resolve_creds, _validate_url, extract_images, extract_links, normalize_url

# Curseurs par défaut calibrés démo (chaque page ≈ 20-40 s en Computer Use).
_MAX_PAGES = 6
_MAX_DEPTH = 2
_MAX_LINKS = 8
_STEPS_PER_PAGE = 8


_DESCRIBE_MODEL = "gemini-2.5-flash"


async def _describe_page(client: genai.Client, page) -> str:
    """Décrit en une phrase française les images de la page — appel vision dédié
    (modèle rapide), séparé de la navigation Computer Use pour un rendu propre."""
    shot = await page.screenshot(type="png")
    prompt = (
        "Décris en UNE phrase courte, en français, la ou les image(s) principale(s) "
        "visible(s) sur cette page. Si la page ne contient pas d'image de contenu, "
        "réponds par une chaîne vide."
    )
    response = await client.aio.models.generate_content(
        model=_DESCRIBE_MODEL,
        contents=[
            types.Content(
                role="user",
                parts=[
                    types.Part.from_bytes(data=shot, mime_type="image/png"),
                    types.Part(text=prompt),
                ],
            )
        ],
    )
    return (response.text or "").strip()[:220]


def _crawl_task(email: str, password: str) -> str:
    """Consigne par page : explorer (login éventuel + défilement), sans cliquer les
    liens soi-même — c'est le crawler qui enchaîne les pages, l'agent explore."""
    return (
        "Explore la page actuelle. Si un formulaire de connexion apparaît, connecte-toi "
        f"avec l'e-mail '{email}' et le mot de passe '{password}'. Fais défiler la page "
        "jusqu'en bas pour révéler tout le contenu (images, vignettes, liens). Quand tu "
        "vois une image, décris-la en une courte phrase en français. Ne clique sur aucun "
        "lien de navigation. Quand la page est entièrement affichée, considère la tâche "
        "terminée et n'émets plus aucune action."
    )


async def stream_crawl(
    start_url: str,
    *,
    max_pages: int = _MAX_PAGES,
    max_depth: int = _MAX_DEPTH,
    max_links: int = _MAX_LINKS,
) -> AsyncIterator[dict]:
    """Explore une surface bornée. Événements : crawl_start · page · (loop) · images ·
    links · done · error. Toute erreur devient un event `error` (jamais silencieux)."""
    _validate_url(start_url)
    start_url = normalize_url(start_url)
    yield {
        "type": "crawl_start",
        "url": start_url,
        "limits": {"pages": max_pages, "depth": max_depth, "links": max_links},
    }

    key = _api_key()
    if not key:
        yield {"type": "error", "message": "Clé Gemini absente (.env.local)."}
        return

    email, password = _resolve_creds(None, None)
    started = time.perf_counter()

    frontier: deque[tuple[str, int]] = deque([(start_url, 0)])
    queued: set[str] = {start_url}          # dans la file ou déjà traitée (anti-doublon)
    visited: set[str] = set()
    seen_images: set[str] = set()
    collected: list = []

    try:
        client = genai.Client(api_key=key)
        config = _config()
        async with async_playwright() as pw:
            page, close_browser = await open_page(pw)
            try:
                while frontier and len(visited) < max_pages:
                    url, depth = frontier.popleft()
                    if url in visited:
                        continue
                    visited.add(url)
                    yield {
                        "type": "page",
                        "url": url,
                        "depth": depth,
                        "n": len(visited),
                        "total": max_pages,
                    }

                    await page.goto(url, wait_until="domcontentloaded", timeout=20_000)
                    async for event in _run_cu_loop(
                        client, config, page, _crawl_task(email, password),
                        email, password, _STEPS_PER_PAGE,
                    ):
                        yield event
                    note = await _describe_page(client, page)

                    images = await extract_images(page)
                    fresh_imgs = [
                        replace(img, note=note) for img in images if img.url not in seen_images
                    ]
                    for img in fresh_imgs:
                        seen_images.add(img.url)
                    collected.extend(fresh_imgs)
                    yield {"type": "images", "new": len(fresh_imgs), "total": len(collected)}

                    if depth < max_depth:
                        links = await extract_links(page, start_url)
                        fresh_links = [link for link in links if link not in queued][:max_links]
                        for link in fresh_links:
                            queued.add(link)
                            frontier.append((link, depth + 1))
                        yield {
                            "type": "links",
                            "found": len(links),
                            "queued": len(fresh_links),
                        }

                yield {
                    "type": "done",
                    "count": len(collected),
                    "pages": len(visited),
                    "elapsed": round(time.perf_counter() - started, 2),
                    "screenshot": None,
                    "images": [
                        {
                            "url": i.url, "alt": i.alt, "width": i.width,
                            "height": i.height, "note": i.note,
                        }
                        for i in collected
                    ],
                }
            finally:
                await close_browser()
    except Exception as exc:  # noqa: BLE001 — toute erreur remonte à l'UI
        yield {"type": "error", "message": f"{type(exc).__name__}: {exc}"}
