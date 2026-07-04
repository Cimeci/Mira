"""Helpers partagés du locator (plus de moteur déterministe — 100% Computer Use).

Ce qui reste ici est utilisé par l'agent Gemini (mira.cu.agent) :
  - validation de l'URL d'entrée ;
  - résolution des identifiants d'auto-login depuis .env.local ;
  - extraction des <img> du DOM (récolte finale des URLs).
"""

from __future__ import annotations

from urllib.parse import urlparse

from dotenv import dotenv_values

from .models import ScrapedImage

# Fallback si le .env ne définit pas d'identifiants : franchit le login MOCK.
_DEMO_EMAIL = "demo@project-mira.example"
_DEMO_PASSWORD = "mira-demo"
_ENV_FILE = ".env.local"

# Noms de variables acceptés (le premier non vide gagne). On tolère les alias
# courts au cas où le .env les nomme MAIL / PASSWORD plutôt que MIRA_LOGIN_*.
_EMAIL_KEYS = ("MIRA_LOGIN_EMAIL", "MAIL", "EMAIL", "LOGIN_EMAIL")
_PASSWORD_KEYS = ("MIRA_LOGIN_PASSWORD", "PASSWORD", "LOGIN_PASSWORD")

# JS exécuté dans la page : renvoie chaque <img> réellement rendu.
_EXTRACT_JS = """
() => Array.from(document.images).map(img => ({
  url: img.currentSrc || img.src || '',
  alt: img.alt || '',
  width: img.naturalWidth || null,
  height: img.naturalHeight || null,
})).filter(x => x.url)
"""


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
    """Récolte finale des <img> rendus (le seul reliquat DOM, à remplacer par la
    détection Gemini dans l'étape 'zéro DOM')."""
    raw = await page.evaluate(_EXTRACT_JS)
    return _dedup(raw)
