"""Connecte-toi UNE fois à tes comptes — l'agent réutilisera la session.

Ouvre un navigateur PERSISTANT. Tu te connectes à la main (comme un humain), la
session (cookies) est sauvée dans .mira_browser_profile/ (gitignored — ce sont des
secrets). Le crawler la réutilise ensuite : il arrive DÉJÀ connecté, sans jamais
retaper de login → il ne déclenche pas le mur anti-bot du login.

Usage :
    .venv/bin/python scripts/browser_login.py [url]
Connecte-toi dans la fenêtre, puis reviens ici et appuie sur Entrée.
"""

from __future__ import annotations

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

PROFILE_DIR = str((Path.cwd() / ".mira_browser_profile").resolve())
DEFAULT_URL = "https://x.com/login"


def main() -> None:
    url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_URL
    print(f"Profil de session : {PROFILE_DIR}")
    print("Une fenêtre va s'ouvrir — connecte-toi à ton compte, puis reviens ici.\n")
    with sync_playwright() as pw:
        context = pw.chromium.launch_persistent_context(
            PROFILE_DIR, headless=False, viewport={"width": 1280, "height": 900}
        )
        page = context.pages[0] if context.pages else context.new_page()
        page.goto(url)
        input("→ Appuie sur Entrée une fois connecté (ça sauve la session et ferme)… ")
        context.close()
    print("✅ Session sauvée. Le crawler la réutilisera automatiquement.")


if __name__ == "__main__":
    main()
