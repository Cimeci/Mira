"""Lance la surface de démo : `.venv/bin/python -m mira.web`.

Port via MIRA_WEB_PORT (défaut 8001) — 8000 est réservé à l'API pipeline
(`python -m mira.api`), pour que les deux tournent ensemble sous `bash dev.sh`.
"""

from __future__ import annotations

import os

import uvicorn

if __name__ == "__main__":
    port = int(os.getenv("MIRA_WEB_PORT", "8001"))
    uvicorn.run("mira.web.app:app", host="127.0.0.1", port=port, reload=False)
