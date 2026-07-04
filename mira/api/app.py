from __future__ import annotations

import os
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import asyncio

from mira.api.schemas import RunRequest, CaseCreated
from mira.api.store import create_case, CaseAlreadyExists, get_case, CaseNotFound
from mira.api.events import make_logger, to_sse, to_sse_done
from mira.orchestrator import run_until_gate, ConsentError
from mira.types import Status
from fastapi.middleware.cors import CORSMiddleware

from pydantic import BaseModel

class ConfirmRequest(BaseModel):
    confirm: bool

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

import logging
logger = logging.getLogger("mira.api")

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled error on %s %s: %s", request.method, request.url, exc, exc_info=exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
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
    
    async def task_wrapper():
        try:
            await run_until_gate(mandate, emit=emit)
        except Exception as e:
            await case_state.queue.put(e)
            
    case_state.task = asyncio.create_task(task_wrapper())
    
    return CaseCreated(case_id=req.case_id, stream_url=f"/stream/{req.case_id}")

@app.get("/stream/{case_id}")
async def stream_case(case_id: str, request: Request):
    try:
        case = get_case(case_id)
    except CaseNotFound:
        raise HTTPException(status_code=404, detail="Case not found")
        
    if case.status == "DONE":
        raise HTTPException(status_code=404, detail="Stream already finished")
        
    async def event_generator():
        try:
            while True:
                if await request.is_disconnected():
                    if case.task and not case.task.done():
                        case.task.cancel()
                    break
                
                try:
                    event = await asyncio.wait_for(case.queue.get(), timeout=15.0)
                    
                    if isinstance(event, Exception):
                        if isinstance(event, ConsentError):
                            yield f"event: refus\ndata: {{}}\n\n"
                        else:
                            yield f"event: failed\ndata: {{\"error\": \"{type(event).__name__}\"}}\n\n"
                        case.status = "DONE"
                        break
                        
                    yield to_sse(event)
                    
                    terminal_statuses = {
                        Status.REJECTED, 
                        Status.ESCALATED, 
                        Status.DECLINED, 
                        Status.NOTIFIED, 
                        Status.FAILED,
                        Status.REVOKED
                    }
                    if event.to_status in terminal_statuses:
                        yield to_sse_done()
                        case.status = "DONE"
                        break
                except asyncio.TimeoutError:
                    yield ": ping\n\n"
        except Exception as e:
            yield f"event: error\ndata: {{\"detail\": \"{str(e)}\"}}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )

@app.post("/confirm/{case_id}")
async def confirm_case(case_id: str, req: ConfirmRequest):
    try:
        case = get_case(case_id)
    except CaseNotFound:
        raise HTTPException(status_code=404, detail="Case not found")
        
    if not case.mandate.active:
        raise HTTPException(status_code=403, detail="Aucun mandat actif pour ce cas ; traitement refusé (G-1).")
        
    if case.confirm_future.done():
        raise HTTPException(status_code=409, detail="Already confirmed or declined")
        
    # Resolve the future immediately
    case.confirm_future.set_result(req.confirm)
    
    if not case.task or not case.task.done():
        raise HTTPException(status_code=409, detail="Pipeline is not ready for confirmation")
        
    records, notices = case.task.result()
    verified_records = [r for r in records if r.status == Status.VERIFIED]
    if not verified_records:
        raise HTTPException(status_code=409, detail="No verified record to confirm")
        
    record = verified_records[0]
    notice = notices.get(record.source_url)
    
    emit = make_logger(case.queue)
    
    from mira.orchestrator import dispatch
    try:
        notif_record = await dispatch(
            record,
            case.mandate,
            notice,
            confirm=lambda _: case.confirm_future,
            emit=emit
        )
    except Exception as e:
        await case.queue.put(e)
        raise HTTPException(status_code=500, detail="Internal server error")
        
    return {
        "notice_text": notif_record.notice_text,
        "host_contact": notif_record.host_contact
    }

from mira.api.schemas import MandateRequest
from mira import mandate as mandate_mod
import uuid

@app.post("/mandate")
async def create_mandate(req: MandateRequest):
    case_id = str(uuid.uuid4())
    urls_str = [str(url) for url in req.scope_urls]
    
    try:
        mand = mandate_mod.capture_consent(
            case_id=case_id,
            requester_role=req.requester_role,
            scope_urls=urls_str,
            legal_basis=req.legal_basis,
            attestation=req.attestation
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
        
    return {"case_id": mand.case_id, "status": "MANDATED"}

from mira.api.store import purge
from mira.events import make_event

@app.post("/revoke/{case_id}")
async def revoke_mandate(case_id: str):
    try:
        case = get_case(case_id)
    except CaseNotFound:
        raise HTTPException(status_code=404, detail="Case not found")
        
    case.mandate.revoke()
    
    if case.task and not case.task.done():
        case.task.cancel()
        
    emit = make_logger(case.queue)
    emit(make_event(case_id, "mandate", Status.REVOKED, from_status=Status.MANDATED, payload={"reason": "user_revoked"}))
    
    # We yield the cpu a bit so SSE can push the REVOKED event before purge drops the queue
    await asyncio.sleep(0.1)
    
    purge(case_id)
    
    return {"status": "REVOKED"}
