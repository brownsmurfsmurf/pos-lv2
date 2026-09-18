"""テスト共通設定。DB は SQLite（メモリ）、時刻は FixedClock で固定する。"""
from __future__ import annotations

import os
from datetime import date, datetime, timezone
from decimal import Decimal

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("JWT_SECRET", "test-secret-test-secret-test-secret")
os.environ.setdefault("CORS_ALLOW_ORIGINS", "http://localhost:3000")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app import db as dbmod
from app.clock import FixedClock, get_clock
from app.db import Base, get_session
from app.main import app
from app.models import Discount, Member, Product, Staff, TaxRate
from app.security import hash_password

# JST 2026-09-15 12:00 = UTC 03:00
DEFAULT_NOW = datetime(2026, 9, 15, 3, 0, 0, tzinfo=timezone.utc)
TODAY_JST = date(2026, 9, 15)


@pytest.fixture()
def session():
    Base.metadata.drop_all(dbmod.engine)
    Base.metadata.create_all(dbmod.engine)
    s = dbmod.SessionLocal()
    try:
        yield s
    finally:
        s.close()


@pytest.fixture()
def seeded(session: Session):
    """商品 A（20% 引き・期間内）、B（値引きなし）、C（期間切れ）、D（20 円引き）、会員 M0001、税率 10%。"""
    staff = Staff(login_id="staff01", password_hash=hash_password("pos-staff-01"), name="佐藤 花子")
    a = Product(product_code="4901234567894", name="緑茶 500ml", unit_price=150)
    b = Product(product_code="4901234567900", name="食パン 6枚切", unit_price=188)
    c = Product(product_code="4901234567917", name="牛乳 1L", unit_price=240)
    d = Product(product_code="4901234567924", name="卵 10個", unit_price=270)
    m = Member(member_code="M0001", name="山田 太郎", address="東京都", age=34)
    session.add_all([staff, a, b, c, d, m, TaxRate(rate=Decimal("10.00"))])
    session.flush()
    session.add_all([
        Discount(product_id=a.id, start_date=date(2026, 9, 1), end_date=date(2026, 9, 30),
                 discount_type="percent", discount_value=Decimal("20.00")),
        Discount(product_id=c.id, start_date=date(2026, 8, 1), end_date=date(2026, 9, 14),
                 discount_type="amount", discount_value=Decimal("30.00")),
        Discount(product_id=d.id, start_date=date(2026, 9, 1), end_date=date(2026, 9, 9),
                 discount_type="amount", discount_value=Decimal("20.00")),
    ])
    session.commit()
    return {"staff": staff, "a": a, "b": b, "c": c, "d": d, "member": m}


class ClockHolder:
    def __init__(self):
        self.now = DEFAULT_NOW

    def set(self, iso: str):
        self.now = datetime.fromisoformat(iso.replace("Z", "+00:00"))


@pytest.fixture()
def clock():
    return ClockHolder()


@pytest.fixture()
def client(session: Session, clock: ClockHolder):
    def _session():
        yield session

    app.dependency_overrides[get_session] = _session
    app.dependency_overrides[get_clock] = lambda: FixedClock(clock.now)
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def auth_header(client: TestClient, seeded):
    r = client.post("/api/v1/auth/login", json={"login_id": "staff01", "password": "pos-staff-01"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}
