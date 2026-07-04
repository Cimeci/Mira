from __future__ import annotations

import uvicorn

if __name__ == "__main__":
    # uvicorn avec 1 SEUL worker requis (état in-memory non partagé)
    uvicorn.run("mira.api.app:app", host="0.0.0.0", port=8000, workers=1)
