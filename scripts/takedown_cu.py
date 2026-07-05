"""Watch Gemini Computer Use fill and submit a takedown report form.

    python scripts/takedown_cu.py [form_url] [task_name]

With no form_url, serves mira/mockhost/takedown.html on localhost and targets that.
task_name defaults to takedown_legal_fr (Agents/prompts/takedown_legal_fr.md).

Needs GOOGLE_GENERATIVE_AI_API_KEY (Computer-Use-enabled) in .env.local, and chromium
(playwright install chromium).
"""

from __future__ import annotations

import asyncio
import functools
import http.server
import os
import sys
import threading
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

# Load .env.local (the project convention — same file mira/cu and mira/db read).
_envfile = _ROOT / ".env.local"
if _envfile.exists():
    for _line in _envfile.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _key, _val = _line.split("=", 1)
            os.environ.setdefault(_key.strip(), _val.strip())

# This is a "watch it" script — show the browser window by default (override: MIRA_CU_HEADFUL=0).
os.environ.setdefault("MIRA_CU_HEADFUL", "1")

from mira.cu.agent import stream_takedown_cu  # noqa: E402

_MOCKHOST = _ROOT / "mira" / "mockhost"


def _serve_mock_form() -> str:
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(_MOCKHOST))
    httpd = http.server.HTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return f"http://127.0.0.1:{httpd.server_address[1]}/takedown.html"


async def main() -> None:
    form_url = sys.argv[1] if len(sys.argv) > 1 else _serve_mock_form()
    task_name = sys.argv[2] if len(sys.argv) > 2 else "takedown_legal_fr"
    # Real government portal (PHAROS): fill only, never auto-submit a report.
    submit = task_name != "takedown_pharos"
    content_url = "https://mock-host.local/target/synthetic_test.jpg"
    print(f"form: {form_url}\ntask: {task_name}\nsubmit: {submit}\n")

    async for ev in stream_takedown_cu(form_url, content_url, task_name, submit=submit):
        kind = ev["type"]
        if kind == "reasoning":
            print("🧠", ev["text"][:200])
        elif kind == "action":
            print("🖱 ", ev["name"], str(ev["args"])[:160])
        elif kind == "note":
            print("•", ev["text"])
        elif kind == "safety":
            print("🔒", ev["text"])
        elif kind == "error":
            print("⚠️ ", ev["message"])
        elif kind == "done":
            print("✅ done —", ev.get("url"))


if __name__ == "__main__":
    asyncio.run(main())
