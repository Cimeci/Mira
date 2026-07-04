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
from urllib.parse import urlparse

from playwright.async_api import async_playwright

from .models import ScrapedImage, ScrapeResult

# Combien de fois scroller pour déclencher le lazy-load, et la pause entre deux.
_SCROLL_STEPS = 8
_SCROLL_PAUSE_MS = 350
_NAV_TIMEOUT_MS = 20_000

# Identifiants de démo : franchissent le login MOCK (jamais un vrai service).
# Le login mock n'a aucune sécurité réelle — c'est un mur de démo (cf. mockhost/index.html).
_DEMO_EMAIL = "demo@project-mira.example"
_DEMO_PASSWORD = "mira-demo"

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
    login_email: str = _DEMO_EMAIL,
    login_password: str = _DEMO_PASSWORD,
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
                    await _maybe_login(page, login_email, login_password, result.steps)

                for i in range(_SCROLL_STEPS):
                    await page.mouse.wheel(0, 2200)
                    await page.wait_for_timeout(_SCROLL_PAUSE_MS)
                result.steps.append(f"scroll ×{_SCROLL_STEPS} (lazy-load)")

                raw = await page.evaluate(_EXTRACT_JS)
                result.images = _dedup(raw)
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
