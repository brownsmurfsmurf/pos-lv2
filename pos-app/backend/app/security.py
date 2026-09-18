"""パスワードハッシュと JWT（設計仕様書 SEC-01〜03）。"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from .clock import Clock, get_clock
from .config import LIMITS, get_settings
from .db import get_session
from .errors import AuthRequired
from .models import Staff

ALGORITHM = "HS256"


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("ascii")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("ascii"))
    except ValueError:
        return False


def create_access_token(staff: Staff, now_utc: datetime, secret: str | None = None) -> tuple[str, int]:
    """(token, expires_in_seconds) を返す。exp は JWT_TTL_HOURS（★ 8 時間）。"""
    ttl = timedelta(hours=LIMITS.JWT_TTL_HOURS)
    payload = {
        "sub": str(staff.id),
        "login_id": staff.login_id,
        "iat": int(now_utc.timestamp()),
        "exp": int((now_utc + ttl).timestamp()),
    }
    token = jwt.encode(payload, secret or get_settings().jwt_secret, algorithm=ALGORITHM)
    return token, int(ttl.total_seconds())


def decode_access_token(token: str, secret: str | None = None, now_utc: datetime | None = None) -> dict:
    """署名・期限を検証して payload を返す。無効なら AuthRequired。"""
    key = secret or get_settings().jwt_secret
    try:
        # 署名と必須クレームを検証。期限は「今」を差し替えられるように自前で比較する
        payload = jwt.decode(
            token, key, algorithms=[ALGORITHM],
            options={"require": ["exp", "sub"], "verify_exp": False},
        )
    except jwt.PyJWTError as e:
        raise AuthRequired() from e
    now = now_utc or utc_now()
    if int(payload["exp"]) <= int(now.timestamp()):
        raise AuthRequired()
    return payload


def _bearer_token(request: Request) -> str:
    auth = request.headers.get("Authorization", "")
    scheme, _, token = auth.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise AuthRequired()
    return token


def get_current_staff(
    request: Request, session: Session = Depends(get_session), clock: Clock = Depends(get_clock)
) -> Staff:
    """/auth/login と /health 以外の全 API で JWT を検証する依存（SEC-03）。期限の判定も Clock の時刻で行う。"""
    payload = decode_access_token(_bearer_token(request), now_utc=clock.now_utc())
    staff = session.execute(select(Staff).where(Staff.id == int(payload["sub"]))).scalar_one_or_none()
    if staff is None:
        raise AuthRequired()
    return staff


def utc_now() -> datetime:
    return datetime.now(timezone.utc)
