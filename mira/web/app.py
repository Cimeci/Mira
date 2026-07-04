"""API + surface de démo du locator d'images.

Routes :
  GET  /            → formulaire (une ligne d'URL, préremplie sur le mock host)
  POST /scrape      → lance le scraper, rend la page résultats (galerie)
  GET  /mockhost/*  → sert la cible de démo (galerie de profil factice)

Nouvelle dépendance structurante pour l'équipe : FastAPI + uvicorn + jinja2.
(Déjà pressenti dans le plan : `mira/api.py` + SSE.)
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from mira.cu.scraper import scrape_images

_BASE = Path(__file__).resolve().parent
_MOCKHOST = _BASE.parent / "mockhost"
_SHOTS = _BASE / "static" / "shots"
_SHOTS.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Mira — Locator (image sweep)")
templates = Jinja2Templates(directory=str(_BASE / "templates"))
app.mount("/static", StaticFiles(directory=str(_BASE / "static")), name="static")
app.mount("/mockhost", StaticFiles(directory=str(_MOCKHOST), html=True), name="mockhost")


def _shot_paths(url: str) -> tuple[str, str]:
    """Chemin disque + URL publique de la capture, nommés par hash de l'URL
    (rejouer la même URL écrase la capture au lieu d'en accumuler)."""
    digest = hashlib.sha1(url.encode()).hexdigest()[:12]  # noqa: S324 — nom de fichier, pas de la crypto
    return str(_SHOTS / f"{digest}.png"), f"/static/shots/{digest}.png"


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    default_url = f"{str(request.base_url).rstrip('/')}/mockhost/"
    return templates.TemplateResponse(
        request, "index.html", {"default_url": default_url}
    )


@app.post("/scrape", response_class=HTMLResponse)
async def scrape(request: Request, url: str = Form(...)) -> HTMLResponse:
    url = url.strip()
    shot_path, shot_url = _shot_paths(url)
    try:
        result = await scrape_images(url, screenshot_path=shot_path, screenshot_url=shot_url)
    except ValueError as exc:
        # URL structurellement invalide → on rend une page résultats en mode erreur.
        from mira.cu.models import ScrapeResult

        result = ScrapeResult(source_url=url, error=str(exc))
    return templates.TemplateResponse(request, "results.html", {"result": result})
