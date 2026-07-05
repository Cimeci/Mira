"""Connecte-toi UNE fois à tes comptes — l'agent réutilisera la session.

Ouvre un navigateur PERSISTANT. Tu te connectes à la main (comme un humain), la
session (cookies) est sauvée dans .mira_browser_profile/ (gitignored — ce sont des
secrets). Le crawler la réutilise ensuite : il arrive DÉJÀ connecté, sans jamais
retaper de login → il ne déclenche pas le mur anti-bot du login.

Usage :
    .venv/bin/python scripts/browser_login.py [url]
Une fenêtre s'ouvre (patiente ~5-10 s la 1re fois), tu te connectes, puis tu
reviens ici et tu appuies sur Entrée.
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
    print("⏳ Ouverture de Chromium (5-10 s la première fois) — NE COUPE PAS.")
    print("   La fenêtre peut s'ouvrir DERRIÈRE ton terminal : cherche-la.\n")
    try:
        with sync_playwright() as pw:
            context = pw.chromium.launch_persistent_context(
                PROFILE_DIR,
                headless=False,
                no_viewport=True,  # fenêtre normale, redimensionnable, bien visible
                args=["--no-first-run", "--no-default-browser-check", "--start-maximized"],
            )
            page = context.pages[0] if context.pages else context.new_page()
            page.goto(url)
            page.bring_to_front()
            print(f"✅ Fenêtre ouverte sur {url}")
            input("→ Connecte-toi, puis appuie sur Entrée ICI (ça sauve et ferme)… ")
            context.close()
        print("✅ Session sauvée. Lance un crawl : l'agent la réutilisera.")
    except KeyboardInterrupt:
        print("\n⚠️  Interrompu — session NON sauvée. Relance et laisse la fenêtre s'ouvrir.")
        sys.exit(1)


if __name__ == "__main__":
    main()
