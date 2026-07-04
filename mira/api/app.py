from __future__ import annotations

import os
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Mira API")

# CONDITIONNEL: CORS (autorisant le front sur localhost:3000 + preview Vercel)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://mira-onboarding.vercel.app",  # TODO: Affiner avec regex ou .env pour les preview Vercel
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}

# Monter StaticFiles pour les assets brand depuis public/
if os.path.isdir("public"):
    app.mount("/static", StaticFiles(directory="public"), name="static")

@app.get("/")
def read_root() -> HTMLResponse:
    # GET / rend la page demo (template derive de la page brand — servie par L3)
    if os.path.exists("public/index.html"):
        with open("public/index.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>Mira API Scaffold (L2-a)</h1>")
