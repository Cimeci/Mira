"""Traduction d'une action Computer Use (renvoyée par Gemini) en gestes Playwright.

Le modèle raisonne en coordonnées normalisées 0-999 ; on les projette sur le
viewport réel. Partagé par le spike et le driver agent (mira/cu/agent.py).
"""

from __future__ import annotations

from playwright.async_api import Page

VIEWPORT = {"width": 1280, "height": 900}


def to_px(x: float, y: float) -> tuple[int, int]:
    """Coordonnées normalisées 0-999 → pixels du viewport."""
    return int(x / 1000 * VIEWPORT["width"]), int(y / 1000 * VIEWPORT["height"])


async def exec_action(page: Page, name: str, args: dict) -> dict:
    """Exécute une action prédéfinie Computer Use. Renvoie un résultat JSON-able
    (renvoyé au modèle dans le function_response). Une action inconnue n'est jamais
    silencieuse : elle remonte `status=unsupported_action`."""
    if name == "open_web_browser":
        return {"status": "ok"}
    if name == "navigate":
        await page.goto(args["url"], wait_until="domcontentloaded")
        return {"status": "ok"}
    if name == "click_at":
        x, y = to_px(args["x"], args["y"])
        await page.mouse.click(x, y)
        return {"status": "ok"}
    if name == "hover_at":
        x, y = to_px(args["x"], args["y"])
        await page.mouse.move(x, y)
        return {"status": "ok"}
    if name == "type_text_at":
        x, y = to_px(args["x"], args["y"])
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
        x, y = to_px(args.get("x", 500), args.get("y", 500))
        magnitude = args.get("magnitude", 800)
        dy = -magnitude if args.get("direction") == "up" else magnitude
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
