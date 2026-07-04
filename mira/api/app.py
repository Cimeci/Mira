from __future__ import annotations

import os
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import asyncio

from mira.api.schemas import RunRequest, CaseCreated
from mira.api.store import create_case, CaseAlreadyExists
from mira.api.events import make_logger
from mira.orchestrator import run_until_gate, ConsentError
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

@app.exception_handler(ConsentError)
async def consent_error_handler(request: Request, exc: ConsentError):
    return JSONResponse(
        status_code=403,
        content={"detail": "Aucun mandat actif pour ce cas ; traitement refusé (G-1)."}
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

@app.post("/run", response_model=CaseCreated)
async def run_pipeline(req: RunRequest):
    # This may raise ConsentError which is mapped to 403
    mandate = req.to_mandate()
    
    try:
        case_state = create_case(req.case_id, mandate)
    except CaseAlreadyExists:
        raise HTTPException(status_code=409, detail="Case already active")
        
    emit = make_logger(case_state.queue)
    case_state.task = asyncio.create_task(run_until_gate(mandate, emit=emit))
    
    return CaseCreated(case_id=req.case_id, stream_url=f"/stream/{req.case_id}")
