"""Surface de démo du locator d'images (100% Computer Use) — BANC D'ESSAI isolé.

⚠️ Périmètre (G-1/G-2/G-12) : cette surface fait tourner le Locator SANS passer par
l'orchestrateur ni un Mandate.active — c'est un banc d'essai du Stage 1, pas le
pipeline consenti. L'intégration réelle passera par `orchestrator.locate(mandate)`.
En attendant, le garde-fou concret est l'allow-list de `mira.cu.guard` : par défaut
seule la cible de démo locale (mock host) est atteignable ; toute autre URL est
refusée en amont. On ne peut donc pas lancer un crawl sur une cible arbitraire ici.

Routes :
  GET  /            → formulaire (URL préremplie sur le mock host, G-12)
  GET  /live        → live view : écran de l'agent en direct pendant le scan
  GET  /stream      → flux SSE (captures + décisions de l'agent Gemini)
  POST /scrape      → variante non-streamée (rend la page résultats d'un coup)
  GET  /mockhost/*  → sert la cible de démo (galerie de profil factice)

Dépendance structurante pour l'équipe : FastAPI + uvicorn + jinja2 + google-genai.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from mira.cu.agent import scrape_images_cu
from mira.cu.crawler import stream_crawl
from mira.cu.models import ScrapeResult

_BASE = Path(__file__).resolve().parent
_MOCKHOST = _BASE.parent / "mockhost"
_SHOTS = _BASE / "static" / "shots"
_SHOTS.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Mira — Locator (Computer Use)")

# CORS : le dashboard (L3, ex. Next.js :3000) ouvre le flux SSE /stream en direct
# (EventSource cross-origin) — le proxy Next bufferisait le flux, le direct stream
# frame par frame. Même politique que mira/api : permissif par défaut (dev/démo),
# restreignable via MIRA_CORS_ORIGINS. Pas de cookie ici -> credentials désactivé.
_origins = os.getenv("MIRA_CORS_ORIGINS", "*").strip()
_cors_origins = ["*"] if _origins == "*" else [o.strip() for o in _origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
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
    base = str(request.base_url).rstrip("/")
    mock_url = f"{base}/mockhost/profil.html"
    # G-12 : cible de démo (mock host) préremplie par défaut — jamais une vraie
    # plateforme. Toute autre URL est de toute façon refusée par mira.cu.guard.
    return templates.TemplateResponse(
        request,
        "index.html",
        {"default_url": mock_url},
    )


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


def _format_event(ev: dict) -> str | None:
    """Une ligne de trace lisible par event du crawl — None = ignoré (frames)."""
    t = ev.get("type")
    if t == "crawl_start":
        lim = ev.get("limits", {})
        return f"▸ crawl {ev.get('url')} · max {lim.get('pages')} pages / depth {lim.get('depth')}"
    if t == "page":
        return f"→ page {ev.get('n')}/{ev.get('total')} (depth {ev.get('depth')}) {ev.get('url')}"
    if t == "action":
        return f"🖱 {ev.get('name')} {ev.get('args')}"
    if t == "reasoning":
        return f"🧠 {ev.get('text', '')[:140]}"
    if t == "safety":
        return f"🔒 action sensible : {ev.get('action')} — {ev.get('text')}"
    if t == "note":
        return f"· {ev.get('text')}"
    if t == "images":
        return f"🖼 +{ev.get('new')} images (total {ev.get('total')})"
    if t == "links":
        return f"🔗 {ev.get('found')} liens, {ev.get('queued')} mis en file"
    if t == "done":
        return (
            f"✅ done · {ev.get('count')} images · "
            f"{ev.get('pages')} pages · {ev.get('elapsed')}s"
        )
    if t == "error":
        return f"⚠️ {ev.get('message')}"
    return None


def _log_event(ev: dict) -> None:
    """Trace serveur du crawl (→ .dev-logs/web.log) pour suivre où va l'agent en
    parallèle du live view. On saute les frames (images base64, illisibles en log)."""
    if ev.get("type") == "frame":
        return
    line = _format_event(ev)
    if line:
        print(f"[cu] {line}", file=sys.stderr, flush=True)


@app.get("/stream")
async def stream(url: str) -> StreamingResponse:
    """Flux SSE du crawler agentique : l'agent explore une surface bornée, suit les
    liens same-domain, et pousse au front chaque page + capture + décision."""
    generator = stream_crawl(url.strip())

    async def _events():
        try:
            async for event in generator:
                _log_event(event)
                yield f"data: {json.dumps(event)}\n\n"
        except Exception as exc:  # noqa: BLE001 — toute erreur devient un event SSE
            payload = {"type": "error", "message": f"{type(exc).__name__}: {exc}"}
            _log_event(payload)
            yield f"data: {json.dumps(payload)}\n\n"

    return StreamingResponse(_events(), media_type="text/event-stream")
