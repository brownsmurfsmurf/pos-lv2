"""AuthService: 認証と JWT の発行（設計仕様書 9 章、SEC-01〜02、API-01/02）。"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..errors import AuthInvalidCredentials
from ..models import Staff
from ..security import create_access_token, verify_password


class AuthService:
    def __init__(self, session: Session):
        self.session = session

    def login(self, login_id: str, password: str, now_utc: datetime) -> tuple[Staff, str, int]:
        """担当者ID・パスワードを照合し (staff, token, expires_in) を返す。

        ID 不存在とパスワード不一致は同じ例外にする（FR-01-4、SEC-01）。
        """
        staff = self.session.execute(select(Staff).where(Staff.login_id == login_id)).scalar_one_or_none()
        if staff is None or not verify_password(password, staff.password_hash):
            raise AuthInvalidCredentials()
        token, expires_in = create_access_token(staff, now_utc)
        return staff, token, expires_in
