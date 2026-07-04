"""Scraping d'images — mode déterministe (Playwright pur).

Ouvre l'URL, scrolle pour déclencher le lazy-load, extrait tous les <img> du DOM.
C'est le socle FIABLE de la démo : pas de LLM dans la boucle, donc pas de surprise
au vidéoprojecteur. Le mode Gemini Computer Use (à venir) réutilisera exactement
cette extraction DOM ; seule la navigation sera pilotée par le modèle.

G-2 (scope) est appliqué en amont par l'orchestrateur/locator ; ici on scrape la
seule URL fournie, sans jamais suivre de lien sortant.
"""

from __future__ import annotations

import time
from collections.abc import AsyncIterator
from urllib.parse import urlparse

from dotenv import dotenv_values, load_dotenv
from playwright.async_api import async_playwright

from .live import data_uri
from .models import ScrapedImage, ScrapeResult

# Charge .env.local (cwd = racine du repo au lancement). Les identifiants d'auto-login
# y vivent — jamais en dur dans le code, jamais commités (.env.local est gitignored).
load_dotenv(".env.local")

# Combien de fois scroller pour déclencher le lazy-load, et la pause entre deux.
_SCROLL_STEPS = 8
_SCROLL_PAUSE_MS = 350
_NAV_TIMEOUT_MS = 20_000

# Fallback si le .env ne définit pas d'identifiants : franchit le login MOCK.
_DEMO_EMAIL = "demo@project-mira.example"
_DEMO_PASSWORD = "mira-demo"
_ENV_FILE = ".env.local"

# Noms de variables acceptés (le premier non vide gagne). On tolère les alias
# courts au cas où le .env les nomme MAIL / PASSWORD plutôt que MIRA_LOGIN_*.
_EMAIL_KEYS = ("MIRA_LOGIN_EMAIL", "MAIL", "EMAIL", "LOGIN_EMAIL")
_PASSWORD_KEYS = ("MIRA_LOGIN_PASSWORD", "PASSWORD", "LOGIN_PASSWORD")


def _from_env_file(keys: tuple[str, ...]) -> str | None:
    """Première clé non vide lue DEPUIS LE FICHIER .env.local (pas os.environ,
    pour éviter les collisions avec des variables système comme MAIL)."""
    values = dotenv_values(_ENV_FILE)
    for key in keys:
        if values.get(key):
            return values[key]
    return None


def _resolve_creds(email: str | None, password: str | None) -> tuple[str, str]:
    """Priorité : argument explicite > .env.local > fallback mock."""
    resolved_email = email or _from_env_file(_EMAIL_KEYS) or _DEMO_EMAIL
    resolved_password = password or _from_env_file(_PASSWORD_KEYS) or _DEMO_PASSWORD
    return resolved_email, resolved_password

# JS exécuté dans la page : renvoie chaque <img> réellement rendu.
_EXTRACT_JS = """
() => Array.from(document.images).map(img => ({
  url: img.currentSrc || img.src || '',
  alt: img.alt || '',
  width: img.naturalWidth || null,
  height: img.naturalHeight || null,
})).filter(x => x.url)
"""


def _validate_url(url: str) -> None:
    """Fail fast : on n'ouvre que du http/https (pas de file://, data:, etc.)."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError(f"URL invalide (attendu http/https) : {url!r}")


def _dedup(raw: list[dict]) -> list[ScrapedImage]:
    """Déduplique par URL en gardant l'ordre d'apparition."""
    seen: set[str] = set()
    images: list[ScrapedImage] = []
    for item in raw:
        url = item["url"]
        if url in seen:
            continue
        seen.add(url)
        images.append(
            ScrapedImage(
                url=url,
                alt=item.get("alt", ""),
                width=item.get("width"),
                height=item.get("height"),
            )
        )
    return images


async def extract_images(page) -> list[ScrapedImage]:
    """Récolte déterministe des <img> rendus. Partagée par les deux moteurs :
    quel que soit le pilote de navigation, la récolte finale reste fiable (DOM)."""
    raw = await page.evaluate(_EXTRACT_JS)
    return _dedup(raw)


async def _maybe_login(page, email: str, password: str, steps: list[str]) -> None:
    """Si la page présente un champ mot de passe, la remplit et la soumet.

    C'est le pendant déterministe du form-fill que fera l'agent CU : on détecte
    un login, on saisit les identifiants de démo, on entre. Sur une page sans
    login (cas normal), c'est un no-op.
    """
    password_field = page.locator("input[type=password]")
    if await password_field.count() == 0:
        return
    steps.append("login détecté")
    email_field = page.locator(
        "input[type=email], input[type=text], input[name*=email i], input[name*=user i]"
    ).first
    if await email_field.count() > 0:
        await email_field.fill(email)
    await password_field.first.fill(password)
    steps.append(f"saisie des identifiants ({email})")

    submit = page.locator("button[type=submit], input[type=submit], button")
    if await submit.count() > 0:
        await submit.first.click()
    else:
        await password_field.first.press("Enter")
    await page.wait_for_load_state("networkidle")
    steps.append("connecté → accès au contenu")


async def scrape_images(
    url: str,
    *,
    screenshot_path: str | None = None,
    screenshot_url: str | None = None,
    headless: bool = True,
    auto_login: bool = True,
    login_email: str | None = None,
    login_password: str | None = None,
) -> ScrapeResult:
    """Ouvre `url`, scrolle, extrait les images. Renvoie un ScrapeResult complet.

    Ne lève jamais pour une page qui charge mal : l'échec est capturé dans
    `result.error` (affiché à l'écran, jamais avalé en silence). Lève seulement
    pour une URL structurellement invalide (contrat d'entrée).
    """
    _validate_url(url)
    started = time.perf_counter()
    result = ScrapeResult(source_url=url, driver="playwright")

    try:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=headless)
            page = await browser.new_page(viewport={"width": 1280, "height": 900})
            try:
                result.steps.append(f"navigate → {url}")
                await page.goto(url, wait_until="domcontentloaded", timeout=_NAV_TIMEOUT_MS)

                if auto_login:
                    email, password = _resolve_creds(login_email, login_password)
                    await _maybe_login(page, email, password, result.steps)

                for _ in range(_SCROLL_STEPS):
                    await page.mouse.wheel(0, 2200)
                    await page.wait_for_timeout(_SCROLL_PAUSE_MS)
                result.steps.append(f"scroll ×{_SCROLL_STEPS} (lazy-load)")

                result.images = await extract_images(page)
                result.steps.append(f"extract → {len(result.images)} image(s) unique(s)")

                if screenshot_path:
                    await page.screenshot(path=screenshot_path, full_page=True)
                    result.screenshot_url = screenshot_url
                    result.steps.append("screenshot full-page")
            finally:
                await browser.close()
    except Exception as exc:  # noqa: BLE001 — on veut afficher TOUTE erreur, pas crasher l'UI
        result.error = f"{type(exc).__name__}: {exc}"
        result.steps.append(f"⚠️ échec : {result.error}")

    result.elapsed_s = round(time.perf_counter() - started, 2)
    return result


async def _frame(page, label: str) -> dict:
    """Capture JPEG légère pour la live view."""
    jpeg = await page.screenshot(type="jpeg", quality=55)
    return {"type": "frame", "label": label, "image": data_uri(jpeg)}


async def stream_scrape_det(
    url: str,
    *,
    screenshot_path: str | None = None,
    screenshot_url: str | None = None,
) -> AsyncIterator[dict]:
    """Version streamée du moteur déterministe (mêmes events que l'agent CU)."""
    _validate_url(url)
    started = time.perf_counter()
    yield {"type": "start", "driver": "playwright", "url": url}
    try:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            page = await browser.new_page(viewport={"width": 1280, "height": 900})
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=_NAV_TIMEOUT_MS)
                yield {"type": "note", "text": f"navigate → {url}"}
                yield await _frame(page, "page ouverte")

                email, password = _resolve_creds(None, None)
                password_field = page.locator("input[type=password]")
                if await password_field.count() > 0:
                    yield {"type": "note", "text": "login détecté"}
                    email_field = page.locator(
                        "input[type=email], input[type=text], "
                        "input[name*=email i], input[name*=user i]"
                    ).first
                    if await email_field.count() > 0:
                        await email_field.fill(email)
                    await password_field.first.fill(password)
                    yield {
                        "type": "action",
                        "name": "type_credentials",
                        "args": "[identifiants masqués]",
                    }
                    submit = page.locator("button[type=submit], input[type=submit], button")
                    if await submit.count() > 0:
                        await submit.first.click()
                    else:
                        await password_field.first.press("Enter")
                    await page.wait_for_load_state("networkidle")
                    yield await _frame(page, "connecté")

                for _ in range(_SCROLL_STEPS):
                    await page.mouse.wheel(0, 2200)
                    await page.wait_for_timeout(_SCROLL_PAUSE_MS)
                yield {"type": "note", "text": f"scroll ×{_SCROLL_STEPS} (lazy-load)"}
                yield await _frame(page, "défilement")

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
