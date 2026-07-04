"""Lance la surface de démo : `.venv/bin/python -m mira.web`."""

from __future__ import annotations

import uvicorn

if __name__ == "__main__":
    uvicorn.run("mira.web.app:app", host="127.0.0.1", port=8000, reload=False)
