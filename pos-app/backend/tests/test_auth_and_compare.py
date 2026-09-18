"""単体テスト UT-B-44〜55（テスト仕様書 5.1）: AuthService と照合。"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.errors import AuthInvalidCredentials, AuthRequired
from app.models import Staff
from app.schemas import (
    AppliedDiscount, CommitItem, CommitRequest, LoginRequest, QuoteLine, QuoteResult,
)
from app.security import create_access_token, decode_access_token, hash_password
from app.services.auth_service import AuthService
from app.services.transaction_service import compare_with_client

NOW = datetime(2026, 9, 15, 3, 0, 0, tzinfo=timezone.utc)
SECRET = "unit-test-secret-unit-test-secret-32b"


# ---- AuthService: UT-B-44〜51 ----

def test_ut_b_44_login_ok(seeded, session):
    staff, token, expires_in = AuthService(session).login("staff01", "pos-staff-01", NOW)
    assert staff.login_id == "staff01"
    assert expires_in == 8 * 3600          # ★ JWT_TTL_HOURS
    payload = decode_access_token(token, now_utc=NOW)
    assert payload["sub"] == str(staff.id) and payload["login_id"] == "staff01"


def test_ut_b_45_46_unknown_id_and_wrong_password_are_indistinguishable(seeded, session):
    svc = AuthService(session)
    with pytest.raises(AuthInvalidCredentials) as e1:
        svc.login("nobody", "pos-staff-01", NOW)
    with pytest.raises(AuthInvalidCredentials) as e2:
        svc.login("staff01", "wrong-password", NOW)
    assert e1.value.code == e2.value.code and e1.value.message == e2.value.message


@pytest.mark.parametrize("length,ok", [(7, True), (8, True), (64, True), (65, False)])
def test_ut_b_47_password_length_schema(length, ok):
    # ★ Q-11: ログイン要求では最大長のみ検証（既存パスワードの照合を妨げない）。最小長は登録時の規則
    from pydantic import ValidationError
    try:
        LoginRequest(login_id="staff01", password="x" * length)
        assert ok
    except ValidationError:
        assert not ok


@pytest.mark.parametrize("pw", ["", None])
def test_ut_b_48_empty_password_rejected(pw):
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        LoginRequest(login_id="staff01", password=pw)


def _staff() -> Staff:
    return Staff(id=1, login_id="staff01", password_hash=hash_password("x"), name="佐藤")


def test_ut_b_49_token_roundtrip():
    token, _ = create_access_token(_staff(), NOW, secret=SECRET)
    assert decode_access_token(token, secret=SECRET, now_utc=NOW)["sub"] == "1"


def test_ut_b_50_expiry_boundary():
    token, ttl = create_access_token(_staff(), NOW, secret=SECRET)
    exp = NOW + timedelta(seconds=ttl)
    assert decode_access_token(token, secret=SECRET, now_utc=exp - timedelta(seconds=1))
    with pytest.raises(AuthRequired):
        decode_access_token(token, secret=SECRET, now_utc=exp)
    with pytest.raises(AuthRequired):
        decode_access_token(token, secret=SECRET, now_utc=exp + timedelta(seconds=1))


def test_ut_b_51_tampered_token_rejected():
    token, _ = create_access_token(_staff(), NOW, secret=SECRET)
    head, body, sig = token.split(".")
    tampered = ".".join([head, body, sig[:-2] + ("AA" if sig[-2:] != "AA" else "BB")])
    with pytest.raises(AuthRequired):
        decode_access_token(tampered, secret=SECRET, now_utc=NOW)
    with pytest.raises(AuthRequired):
        decode_access_token(token, secret="other-secret-other-secret-other-secret", now_utc=NOW)


# ---- compare_with_client: UT-B-52〜55 ----

def _server() -> QuoteResult:
    return QuoteResult(
        tax_rate=10.0,
        lines=[
            QuoteLine(product_code="4901234567894", product_name="緑茶", unit_price=150, quantity=2,
                      discount=AppliedDiscount(discount_id=1, type="percent", value=20.0, amount=60), line_total=240),
            QuoteLine(product_code="4901234567900", product_name="食パン", unit_price=188, quantity=1,
                      discount=None, line_total=188),
        ],
        subtotal_excl_tax=428, tax_amount=42, total_incl_tax=470,
    )


def _client(**over) -> CommitRequest:
    base = dict(
        member_code="M0001",
        items=[
            CommitItem(product_code="4901234567894", quantity=2, unit_price=150, discount_amount=60, line_total=240),
            CommitItem(product_code="4901234567900", quantity=1, unit_price=188, discount_amount=0, line_total=188),
        ],
        tax_rate=10.0, subtotal_excl_tax=428, tax_amount=42, total_incl_tax=470,
    )
    base.update(over)
    return CommitRequest(**base)


def test_ut_b_52_match():
    assert compare_with_client(_server(), _client()) == []


def test_ut_b_53_total_off_by_one():
    assert "total_incl_tax" in compare_with_client(_server(), _client(total_incl_tax=471))


def test_ut_b_54_discount_amount_differs():
    items = _client().items
    items[0] = CommitItem(product_code="4901234567894", quantity=2, unit_price=150, discount_amount=0, line_total=300)
    diffs = compare_with_client(_server(), _client(items=items))
    assert "items[0].discount_amount" in diffs and "items[0].line_total" in diffs


def test_ut_b_55_line_count_differs():
    assert compare_with_client(_server(), _client(items=_client().items[:1])) == ["items.length"]
