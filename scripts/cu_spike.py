"""Spike Computer Use — valide la boucle agentique AVANT toute intégration.

But : prouver que Gemini 2.5 Computer Use pilote la navigation (franchir le
login, scroller) sur le mock host, via generate_content + le tool computer_use.
Jetable-ish : le mapping actions→Playwright servira ensuite à mira/cu/agent.py.

Usage : .venv/bin/python scripts/cu_spike.py [url]
"""

from __future__ import annotations

import asyncio
import sys

from dotenv import dotenv_values
from google import genai
from google.genai import types
from playwright.async_api import Page, async_playwright

MODEL = "gemini-2.5-computer-use-preview-10-2025"
DEFAULT_URL = "http://127.0.0.1:8000/mockhost/"
MAX_STEPS = 10
VIEWPORT = {"width": 1280, "height": 900}

TASK = (
    "Tu es sur un site dont la galerie d'images est protégée par un écran de "
    "connexion. Connecte-toi avec l'e-mail 'demo@project-mira.example' et le mot "
    "de passe 'mira-demo', puis fais défiler la page jusqu'en bas pour afficher "
    "toutes les images de la galerie. Quand la galerie est entièrement visible, "
    "considère la tâche terminée et n'émets plus d'action."
)


def _api_key() -> str | None:
    return dotenv_values(".env.local").get("GOOGLE_GENERATIVE_AI_API_KEY")


def _to_px(x: float, y: float) -> tuple[int, int]:
    """Coordonnées normalisées 0-999 → pixels du viewport."""
    return int(x / 1000 * VIEWPORT["width"]), int(y / 1000 * VIEWPORT["height"])


async def exec_action(page: Page, name: str, args: dict) -> dict:
    """Mappe une action Computer Use vers Playwright. Renvoie un résultat JSON-able."""
    if name == "open_web_browser":
        return {"status": "ok"}
    if name == "navigate":
        await page.goto(args["url"], wait_until="domcontentloaded")
        return {"status": "ok"}
    if name == "click_at":
        x, y = _to_px(args["x"], args["y"])
        await page.mouse.click(x, y)
        return {"status": "ok"}
    if name == "hover_at":
        x, y = _to_px(args["x"], args["y"])
        await page.mouse.move(x, y)
        return {"status": "ok"}
    if name == "type_text_at":
        x, y = _to_px(args["x"], args["y"])
        await page.mouse.click(x, y)
        if args.get("clear_before_typing", True):
            await page.keyboard.press("ControlOrMeta+A")
            await page.keyboard.press("Delete")
        await page.keyboard.type(args["text"])
        if args.get("press_enter"):
            await page.keyboard.press("Enter")
        return {"status": "ok"}
    if name == "scroll_document":
        dy = -1200 if args.get("direction") == "up" else 1200
        await page.mouse.wheel(0, dy)
        return {"status": "ok"}
    if name == "scroll_at":
        x, y = _to_px(args.get("x", 500), args.get("y", 500))
        mag = args.get("magnitude", 800)
        dy = -mag if args.get("direction") == "up" else mag
        await page.mouse.move(x, y)
        await page.mouse.wheel(0, dy)
        return {"status": "ok"}
    if name == "key_combination":
        await page.keyboard.press(args["keys"].replace("Control", "ControlOrMeta"))
        return {"status": "ok"}
    if name == "wait_5_seconds":
        await page.wait_for_timeout(5000)
        return {"status": "ok"}
    if name == "go_back":
        await page.go_back()
        return {"status": "ok"}
    if name == "go_forward":
        await page.go_forward()
        return {"status": "ok"}
    return {"status": "unsupported_action", "name": name}


async def main() -> None:
    key = _api_key()
    if not key:
        sys.exit("❌ GOOGLE_GENERATIVE_AI_API_KEY absente de .env.local")
    url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_URL

    client = genai.Client(api_key=key)
    config = types.GenerateContentConfig(
        tools=[
            types.Tool(
                computer_use=types.ComputerUse(
                    environment=types.Environment.ENVIRONMENT_BROWSER,
                    enable_prompt_injection_detection=True,
                )
            )
        ],
    )

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        page = await browser.new_page(viewport=VIEWPORT)
        await page.goto(url, wait_until="domcontentloaded")
        shot = await page.screenshot(type="png")

        contents: list = [
            types.Content(
                role="user",
                parts=[
                    types.Part(text=TASK),
                    types.Part.from_bytes(data=shot, mime_type="image/png"),
                ],
            )
        ]

        for step in range(1, MAX_STEPS + 1):
            resp = await client.aio.models.generate_content(
                model=MODEL, contents=contents, config=config
            )
            candidate = resp.candidates[0]
            parts = candidate.content.parts or []

            # DEBUG au 1er tour : voir la vraie structure des parts.
            if step == 1:
                kinds = [
                    "function_call" if getattr(p, "function_call", None)
                    else "text" if getattr(p, "text", None)
                    else "other"
                    for p in parts
                ]
                print(f"[debug] parts du tour 1 : {kinds}")

            calls = [p.function_call for p in parts if getattr(p, "function_call", None)]
            for p in parts:
                if getattr(p, "text", None):
                    print(f"[{step}] 💬 {p.text.strip()[:180]}")

            if not calls:
                print(f"[{step}] ✅ terminé — plus d'action émise.")
                break

            contents.append(candidate.content)  # garde le raisonnement du modèle

            fr_parts: list = []
            for fc in calls:
                args = dict(fc.args) if fc.args else {}
                print(f"[{step}] 🖱  {fc.name}  {args}")
                result = await exec_action(page, fc.name, args)
                await page.wait_for_timeout(500)
                new_shot = await page.screenshot(type="png")
                fr_parts.append(
                    types.Part.from_function_response(
                        name=fc.name, response={"url": page.url, **result}
                    )
                )
                fr_parts.append(types.Part.from_bytes(data=new_shot, mime_type="image/png"))
            contents.append(types.Content(role="user", parts=fr_parts))
        else:
            print(f"⚠️ limite de {MAX_STEPS} étapes atteinte.")

        images = await page.evaluate(
            "() => Array.from(document.images).map(i => i.currentSrc || i.src).filter(Boolean)"
        )
        unique = sorted(set(images))
        print(f"\n🖼  {len(unique)} image(s) extraite(s) du DOM après pilotage :")
        for u in unique[:20]:
            print("   -", u)
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
