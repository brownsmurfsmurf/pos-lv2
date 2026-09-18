"""API-01 POST /auth/login、API-02 GET /auth/me。"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..clock import Clock, get_clock
from ..db import get_session
from ..models import Staff
from ..schemas import LoginRequest, LoginResponse, StaffInfo
from ..security import get_current_staff
from ..services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(body: LoginRequest, session: Session = Depends(get_session), clock: Clock = Depends(get_clock)):
    staff, token, expires_in = AuthService(session).login(body.login_id, body.password, clock.now_utc())
    return LoginResponse(access_token=token, expires_in=expires_in, staff=StaffInfo.model_validate(staff, from_attributes=True))


@router.get("/me", response_model=StaffInfo)
def me(staff: Staff = Depends(get_current_staff)):
    return StaffInfo.model_validate(staff, from_attributes=True)
