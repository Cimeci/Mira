"""API + surface de démo du locator d'images (100% Computer Use).

Routes :
  GET  /            → formulaire (une ligne d'URL, préremplie sur le mock host)
  GET  /live        → live view : écran de l'agent en direct pendant le scan
  GET  /stream      → flux SSE (captures + décisions de l'agent Gemini)
  POST /scrape      → variante non-streamée (rend la page résultats d'un coup)
  GET  /mockhost/*  → sert la cible de démo (galerie de profil factice)

Dépendance structurante pour l'équipe : FastAPI + uvicorn + jinja2 + google-genai.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from mira.cu.agent import scrape_images_cu, stream_scrape_cu
from mira.cu.models import ScrapeResult

_BASE = Path(__file__).resolve().parent
_MOCKHOST = _BASE.parent / "mockhost"
_SHOTS = _BASE / "static" / "shots"
_SHOTS.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Mira — Locator (Computer Use)")
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
    return templates.TemplateResponse(request, "index.html", {"default_url": default_url})


@app.post("/scrape", response_class=HTMLResponse)
async def scrape(request: Request, url: str = Form(...)) -> HTMLResponse:
    """Scan non-streamé : agrège la boucle Computer Use en une page résultats."""
    url = url.strip()
    shot_path, shot_url = _shot_paths(url)
    try:
        result = await scrape_images_cu(url, screenshot_path=shot_path, screenshot_url=shot_url)
    except ValueError as exc:
        # URL structurellement invalide → page résultats en mode erreur.
        result = ScrapeResult(source_url=url, error=str(exc))
    return templates.TemplateResponse(request, "results.html", {"result": result})


@app.get("/live", response_class=HTMLResponse)
async def live(request: Request, url: str) -> HTMLResponse:
    """Page live view : ouvre un flux SSE et affiche l'écran de l'agent en direct."""
    return templates.TemplateResponse(request, "live.html", {"url": url})


@app.get("/stream")
async def stream(url: str) -> StreamingResponse:
    """Flux SSE : chaque étape de l'agent (capture + décision) est poussée au front."""
    url = url.strip()
    shot_path, shot_url = _shot_paths(url)
    generator = stream_scrape_cu(url, screenshot_path=shot_path, screenshot_url=shot_url)

    async def _events():
        try:
            async for event in generator:
                yield f"data: {json.dumps(event)}\n\n"
        except Exception as exc:  # noqa: BLE001 — toute erreur devient un event SSE
            payload = {"type": "error", "message": f"{type(exc).__name__}: {exc}"}
            yield f"data: {json.dumps(payload)}\n\n"

    return StreamingResponse(_events(), media_type="text/event-stream")
