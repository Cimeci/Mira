"""Driver Computer Use : Gemini pilote la navigation d'UNE page.

`_run_cu_loop` = la boucle vision-action réutilisable (partagée avec le crawler) :
capture → le modèle renvoie une action → on l'exécute → nouvelle capture → reboucle.
`stream_scrape_cu` = scan d'une seule page (ouvre le navigateur, boucle, récolte).
`scrape_images_cu` = variante non-streamée (agrège en ScrapeResult).
"""

from __future__ import annotations

import time
from collections.abc import AsyncIterator

from dotenv import dotenv_values
from google import genai
from google.genai import types
from playwright.async_api import Page, async_playwright

from .actions import VIEWPORT, exec_action
from .live import data_uri
from .models import ScrapedImage, ScrapeResult
from .scraper import _resolve_creds, _validate_url, extract_images

MODEL = "gemini-2.5-computer-use-preview-10-2025"
_MAX_STEPS = 12
_ENV_FILE = ".env.local"
_FRAME_QUALITY = 55  # JPEG : compromis netteté / poids pour le stream


def _api_key() -> str | None:
    return dotenv_values(_ENV_FILE).get("GOOGLE_GENERATIVE_AI_API_KEY")


def _redact(text: str, email: str, password: str) -> str:
    """Ne JAMAIS laisser fuiter les identifiants dans la trace affichée à l'écran."""
    if password:
        text = text.replace(password, "[mot de passe masqué]")
    if email:
        text = text.replace(email, "[identifiant masqué]")
    return text


def _task(email: str, password: str) -> str:
    """Consigne d'un scan simple : login éventuel + défilement de la page."""
    return (
        "Tu es sur un site dont la galerie d'images peut être protégée par un écran "
        "de connexion. Si un formulaire de connexion apparaît, connecte-toi avec "
        f"l'e-mail '{email}' et le mot de passe '{password}'. Ensuite, fais défiler "
        "la page jusqu'en bas pour afficher toutes les images de la galerie. "
        "Quand tu vois une image, décris-la en une courte phrase en français. "
        "Quand la galerie est entièrement visible, considère la tâche terminée et n'émets "
        "plus aucune action."
    )


def _config() -> types.GenerateContentConfig:
    return types.GenerateContentConfig(
        tools=[
            types.Tool(
                computer_use=types.ComputerUse(
                    environment=types.Environment.ENVIRONMENT_BROWSER,
                    enable_prompt_injection_detection=True,  # cohérent avec le pitch Mira
                )
            )
        ],
    )


async def _run_cu_loop(
    client: genai.Client,
    config: types.GenerateContentConfig,
    page: Page,
    task: str,
    email: str,
    password: str,
    max_steps: int,
) -> AsyncIterator[dict]:
    """Boucle vision-action de Gemini sur la page COURANTE (le goto est fait par
    l'appelant). Yield reasoning · action · frame · safety · note. S'arrête quand
    l'agent n'émet plus d'action, sur une action sensible (G-7), ou à la limite."""
    shot = await page.screenshot(type="png")
    yield {
        "type": "frame",
        "label": "page ouverte",
        "image": data_uri(await page.screenshot(type="jpeg", quality=_FRAME_QUALITY)),
    }
    contents: list = [
        types.Content(
            role="user",
            parts=[
                types.Part(text=task),
                types.Part.from_bytes(data=shot, mime_type="image/png"),
            ],
        )
    ]

    for _step in range(1, max_steps + 1):
        response = await client.aio.models.generate_content(
            model=MODEL, contents=contents, config=config
        )
        candidate = response.candidates[0]
        parts = candidate.content.parts or []
        calls = [p.function_call for p in parts if getattr(p, "function_call", None)]

        for part in parts:
            if getattr(part, "text", None):
                yield {"type": "reasoning", "text": _redact(part.text.strip(), email, password)}

        if not calls:
            yield {"type": "note", "text": "✅ agent : page explorée"}
            return

        contents.append(candidate.content)
        response_parts: list = []
        for call in calls:
            args = dict(call.args) if call.args else {}
            safety = args.pop("safety_decision", None)
            if safety and safety.get("decision") == "require_confirmation":
                # G-7 : action sensible (connexion) — on ne la franchit jamais seul.
                yield {
                    "type": "safety",
                    "action": call.name,
                    "text": safety.get("explanation", "action sensible"),
                }
                yield {
                    "type": "note",
                    "text": "🔒 Garde-fou G-7 : action sensible — arrêt, pas de login automatique.",
                }
                return
            yield {"type": "action", "name": call.name, "args": _redact(str(args), email, password)}
            action_result = await exec_action(page, call.name, args)
            await page.wait_for_timeout(500)
            next_png = await page.screenshot(type="png")
            yield {
                "type": "frame",
                "label": call.name,
                "image": data_uri(await page.screenshot(type="jpeg", quality=_FRAME_QUALITY)),
            }
            response_parts.append(
                types.Part.from_function_response(
                    name=call.name, response={"url": page.url, **action_result}
                )
            )
            response_parts.append(types.Part.from_bytes(data=next_png, mime_type="image/png"))
        contents.append(types.Content(role="user", parts=response_parts))

    yield {"type": "note", "text": f"⚠️ limite de {max_steps} étapes atteinte"}


async def stream_scrape_cu(
    url: str,
    *,
    max_steps: int = _MAX_STEPS,
    screenshot_path: str | None = None,
    screenshot_url: str | None = None,
) -> AsyncIterator[dict]:
    """Scan Computer Use d'une seule page. Événements : start · (loop) · done · error."""
    _validate_url(url)
    yield {"type": "start", "driver": "gemini-cu", "url": url}

    key = _api_key()
    if not key:
        yield {"type": "error", "message": "Clé Gemini absente (.env.local)."}
        return

    email, password = _resolve_creds(None, None)
    started = time.perf_counter()

    try:
        client = genai.Client(api_key=key)
        config = _config()
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            page = await browser.new_page(viewport=VIEWPORT)
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=20_000)
                yield {"type": "note", "text": f"navigate → {url}"}
                async for event in _run_cu_loop(
                    client, config, page, _task(email, password), email, password, max_steps
                ):
                    yield event

                images = await extract_images(page)
                final_shot_url = None
                if screenshot_path:
                    await page.screenshot(path=screenshot_path, full_page=True)
                    final_shot_url = screenshot_url
                yield {
                    "type": "done",
                    "count": len(images),
                    "elapsed": round(time.perf_counter() - started, 2),
                    "screenshot": final_shot_url,
                    "images": [
                        {"url": i.url, "alt": i.alt, "width": i.width, "height": i.height}
                        for i in images
                    ],
                }
            finally:
                await browser.close()
    except Exception as exc:  # noqa: BLE001 — toute erreur remonte à l'UI
        yield {"type": "error", "message": f"{type(exc).__name__}: {exc}"}


async def scrape_images_cu(
    url: str,
    *,
    screenshot_path: str | None = None,
    screenshot_url: str | None = None,
    max_steps: int = _MAX_STEPS,
) -> ScrapeResult:
    """Version non-streamée (POST) : agrège le flux en ScrapeResult."""
    result = ScrapeResult(source_url=url, driver="gemini-cu")
    async for event in stream_scrape_cu(
        url, max_steps=max_steps, screenshot_path=screenshot_path, screenshot_url=screenshot_url
    ):
        kind = event["type"]
        if kind == "note":
            result.steps.append(event["text"])
        elif kind == "action":
            result.steps.append(f"🖱 {event['name']} {event['args']}")
        elif kind == "reasoning":
            result.steps.append(f"🧠 {event['text'][:150]}")
        elif kind == "safety":
            result.steps.append(f"🔒 action sensible : {event['action']} — {event['text']}")
        elif kind == "error":
            result.error = event["message"]
            result.steps.append(f"⚠️ échec Computer Use : {event['message']}")
        elif kind == "done":
            result.images = [ScrapedImage(**img) for img in event["images"]]
            result.elapsed_s = event["elapsed"]
            result.screenshot_url = event.get("screenshot")
    return result
