"""API-07 GET /health ★（DB 疎通）。"""
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from ..db import get_session, ping

router = APIRouter(tags=["health"])


@router.get("/health")
def health(session: Session = Depends(get_session)):
    try:
        ping(session)
    except Exception:
        return JSONResponse(status_code=503, content={"status": "error", "db": "error"})
    return {"status": "ok", "db": "ok"}
