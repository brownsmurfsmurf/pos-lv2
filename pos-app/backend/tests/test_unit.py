"""単体テスト UT-B-01〜41（テスト仕様書 v2 の 4.1）。

期待値の出どころ: 人 = E-1〜E-3（受講者が計算）、AI 算出 = 設計の計算規則に当てはめた値（人の検算待ち）。
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.clock import FixedClock, business_date_of
from app.errors import AuthInvalidCredentials, AuthRequired, CartEmpty, QuantityOutOfRange, TaxRateNotConfigured
from app.models import Staff
from app.schemas import (
    AppliedDiscount, CommitItem, CommitRequest, LoginRequest, QuoteItemRequest, QuoteLine, QuoteRequest, QuoteResult,
)
from app.security import create_access_token, decode_access_token, hash_password
from app.services.auth_service import AuthService
from app.services.pricing_service import DiscountRule, PricedItem, calc_totals, check_quantity, compute_quote
from app.services.transaction_service import TransactionService, compare_with_client

TAX = Decimal("10")
TODAY = date(2026, 9, 15)
NOW = datetime(2026, 9, 15, 3, 0, 0, tzinfo=timezone.utc)
SECRET = "unit-test-secret-unit-test-secret-32b"


def item(pid: int, price: int, qty: int) -> PricedItem:
    return PricedItem(pid, f"49{pid:011d}", f"商品{pid}", price, qty)


def rule(dtype: str, value, start: str, end: str, product_id: int = 1, id: int = 1) -> DiscountRule:
    return DiscountRule(id, product_id, date.fromisoformat(start), date.fromisoformat(end), dtype, Decimal(str(value)))


def totals(q: QuoteResult) -> tuple[int, int, int]:
    return q.subtotal_excl_tax, q.tax_amount, q.total_incl_tax


def jst_date(utc_iso: str) -> date:
    return business_date_of(FixedClock(datetime.fromisoformat(utc_iso)).now_utc())


# ---- 人が決めた期待値 ----

def test_ut_b_01_e1_percent_discount_and_tax():
    """E-1（人）: 150 円 × 2、会員、20% 引き → 税抜 240、税 24、税込 264"""
    q = compute_quote([item(1, 150, 2)], [rule("percent", 20, "2026-09-01", "2026-09-30")], TODAY, True, TAX)
    assert totals(q) == (240, 24, 264)
    assert q.lines[0].discount.amount == 60


def test_ut_b_02_e2_two_lines():
    """E-2（人）: 188 円 × 1（値引きなし）と 150 円 × 2（20% 引き）、会員 → 税抜 428、税 42、税込 470"""
    q = compute_quote([item(2, 188, 1), item(1, 150, 2)], [rule("percent", 20, "2026-09-01", "2026-09-30")], TODAY, True, TAX)
    assert totals(q) == (428, 42, 470)
    assert q.lines[0].discount is None and q.lines[1].discount.amount == 60


def test_ut_b_03_e3_expired_discount():
    """E-3（人）: 240 円 × 1、会員、20% 引きの値引きは昨日で終了 → 税抜 240、税 24、税込 264"""
    q = compute_quote([item(1, 240, 1)], [rule("percent", 20, "2026-08-01", "2026-09-14")], TODAY, True, TAX)
    assert totals(q) == (240, 24, 264)
    assert q.lines[0].discount is None


# ---- 数量の境界（FR-05-6, FR-05-7） ----

def test_ut_b_04_quantity_0_rejected():
    with pytest.raises(QuantityOutOfRange):
        check_quantity(0)


def test_ut_b_05_quantity_1_accepted():
    assert check_quantity(1) == 1


def test_ut_b_06_quantity_99_accepted():
    assert check_quantity(99) == 99


def test_ut_b_07_quantity_100_rejected():
    with pytest.raises(QuantityOutOfRange):
        check_quantity(100)


@pytest.mark.parametrize("qty", [1.5, None, "abc"])
def test_ut_b_08_quantity_not_integer(qty):
    with pytest.raises(TypeError):
        check_quantity(qty)
    with pytest.raises(ValidationError):   # API の入口でも 400 になる
        QuoteItemRequest(product_code="4901234567894", quantity=qty)


# ---- 取引日の境界（D-009。★ K-35: 終了日を含む） ----

def test_ut_b_09_business_date_before_midnight_jst():
    d = jst_date("2026-09-09T14:59:59+00:00")
    assert d == date(2026, 9, 9)
    q = compute_quote([item(1, 100, 1)], [rule("percent", 10, "2026-09-01", "2026-09-09")], d, True, TAX)
    assert q.lines[0].discount is not None


def test_ut_b_10_business_date_at_midnight_jst():
    d = jst_date("2026-09-09T15:00:00+00:00")
    assert d == date(2026, 9, 10)   # UTC ではまだ 9/9。日本時間では 9/10
    q = compute_quote([item(1, 100, 1)], [rule("percent", 10, "2026-09-01", "2026-09-09")], d, True, TAX)
    assert q.lines[0].discount is None


@pytest.mark.parametrize("tid,today,start,end,applied", [
    ("UT-B-11", "2026-09-09", "2026-09-10", "2026-09-30", False),   # 開始日の前日
    ("UT-B-12", "2026-09-10", "2026-09-10", "2026-09-30", True),    # 開始日の当日
    ("UT-B-13", "2026-09-09", "2026-09-01", "2026-09-09", True),    # 終了日の当日
    ("UT-B-14", "2026-09-10", "2026-09-01", "2026-09-09", False),   # 終了日の翌日
])
def test_ut_b_11_to_14_discount_period_edges(tid, today, start, end, applied):
    q = compute_quote([item(1, 100, 1)], [rule("percent", 10, start, end)], date.fromisoformat(today), True, TAX)
    assert (q.lines[0].discount is not None) == applied, tid


def test_ut_b_15_no_member_no_discount():
    q = compute_quote([item(1, 150, 2)], [rule("percent", 20, "2026-09-01", "2026-09-30")], TODAY, False, TAX)
    assert q.lines[0].discount is None and q.subtotal_excl_tax == 300


def test_ut_b_16_other_product_no_discount():
    q = compute_quote([item(1, 150, 2)], [rule("percent", 20, "2026-09-01", "2026-09-30", product_id=2)], TODAY, True, TAX)
    assert q.lines[0].discount is None


# ---- 値引きと税の規則（★ AI 算出。人の検算待ち） ----

def test_ut_b_17_amount_discount_per_item():
    """★ K-39: 150 円 × 2、20 円引き → 値引き 40、小計 260"""
    q = compute_quote([item(1, 150, 2)], [rule("amount", 20, "2026-09-01", "2026-09-30")], TODAY, True, TAX)
    assert q.lines[0].discount.amount == 40 and q.lines[0].line_total == 260


def test_ut_b_18_percent_discount_rounds_down():
    """★ K-13: 15 円 × 1、10% 引き → 値引き 1（1.5 を切り捨て）、小計 14"""
    q = compute_quote([item(1, 15, 1)], [rule("percent", 10, "2026-09-01", "2026-09-30")], TODAY, True, TAX)
    assert q.lines[0].discount.amount == 1 and q.lines[0].line_total == 14


def test_ut_b_19_discount_capped_at_line_amount():
    """★ K-13: 100 円 × 1、150 円引き → 値引き 100、小計 0"""
    q = compute_quote([item(1, 100, 1)], [rule("amount", 150, "2026-09-01", "2026-09-30")], TODAY, True, TAX)
    assert q.lines[0].discount.amount == 100 and q.lines[0].line_total == 0


def test_ut_b_20_overlapping_discounts_pick_larger():
    """★ K-14: 100 円 × 1、20% 引きと 50 円引き → 値引き 50（大きい方）"""
    rules = [rule("percent", 20, "2026-09-01", "2026-09-30", id=1), rule("amount", 50, "2026-09-01", "2026-09-30", id=2)]
    q = compute_quote([item(1, 100, 1)], rules, TODAY, True, TAX)
    assert q.lines[0].discount.amount == 50 and q.lines[0].discount.discount_id == 2


def test_ut_b_21_tax_rounding_below():
    """★ K-12: 税抜 9 円 → 税 0、税込 9"""
    assert calc_totals(9, TAX) == (0, 9)


def test_ut_b_22_tax_rounding_above():
    """★ K-12: 税抜 10 円 → 税 1、税込 11"""
    assert calc_totals(10, TAX) == (1, 11)


def test_ut_b_23_tax_rate_not_configured():
    with pytest.raises(TaxRateNotConfigured):
        calc_totals(100, None)


# ---- ログインとトークン ----

def test_ut_b_24_login_ok(seeded, session):
    staff, token, expires_in = AuthService(session).login("staff01", "pos-staff-01", NOW)
    assert staff.login_id == "staff01" and expires_in == 8 * 3600
    assert decode_access_token(token, now_utc=NOW)["login_id"] == "staff01"


def test_ut_b_25_login_failures_are_indistinguishable(seeded, session):
    svc = AuthService(session)
    with pytest.raises(AuthInvalidCredentials) as e1:
        svc.login("nobody", "pos-staff-01", NOW)
    with pytest.raises(AuthInvalidCredentials) as e2:
        svc.login("staff01", "wrong-password", NOW)
    assert (e1.value.code, e1.value.message) == (e2.value.code, e2.value.message)


def _staff() -> Staff:
    return Staff(id=1, login_id="staff01", password_hash=hash_password("x"))


def test_ut_b_26_token_valid_one_second_before_8h():
    token, ttl = create_access_token(_staff(), NOW, secret=SECRET)
    assert decode_access_token(token, secret=SECRET, now_utc=NOW + timedelta(seconds=ttl - 1))["sub"] == "1"


def test_ut_b_27_token_invalid_at_exactly_8h():
    token, ttl = create_access_token(_staff(), NOW, secret=SECRET)
    assert ttl == 8 * 3600
    with pytest.raises(AuthRequired):
        decode_access_token(token, secret=SECRET, now_utc=NOW + timedelta(seconds=ttl))


def test_ut_b_28_tampered_token_rejected():
    token, _ = create_access_token(_staff(), NOW, secret=SECRET)
    head, body, sig = token.split(".")
    tampered = ".".join([head, body, sig[:-2] + ("AA" if sig[-2:] != "AA" else "BB")])
    with pytest.raises(AuthRequired):
        decode_access_token(tampered, secret=SECRET, now_utc=NOW)


# ---- 照合（D-008、課題の指定） ----

def _server() -> QuoteResult:
    return QuoteResult(
        tax_rate=10.0,
        lines=[QuoteLine(product_code="4901234567894", product_name="緑茶", unit_price=150, quantity=2,
                         discount=AppliedDiscount(discount_id=1, type="percent", value=20.0, amount=60), line_total=240)],
        subtotal_excl_tax=240, tax_amount=24, total_incl_tax=264,
    )


def _client(**over) -> CommitRequest:
    base = dict(
        member_code="M0001",
        items=[CommitItem(product_code="4901234567894", quantity=2, unit_price=150, discount_amount=60, line_total=240)],
        tax_rate=10.0, subtotal_excl_tax=240, tax_amount=24, total_incl_tax=264,
    )
    base.update(over)
    return CommitRequest(**base)


def test_ut_b_29_compare_match():
    assert compare_with_client(_server(), _client()) == []


def test_ut_b_30_compare_total_off_by_one_yen():
    assert "total_incl_tax" in compare_with_client(_server(), _client(total_incl_tax=265))


def test_ut_b_31_compare_unit_price_tampered():
    items = [CommitItem(product_code="4901234567894", quantity=2, unit_price=100, discount_amount=40, line_total=160)]
    diffs = compare_with_client(_server(), _client(items=items))
    assert "items[0].unit_price" in diffs


def test_ut_b_32_empty_cart_rejected():
    req = CommitRequest(member_code=None, items=[], tax_rate=10.0, subtotal_excl_tax=0, tax_amount=0, total_incl_tax=0)
    with pytest.raises(CartEmpty):
        TransactionService(None, None).commit(req, _staff())


# ---- 入力の形（★ K-32, K-21, K-17） ----

def _items(n: int) -> list[dict]:
    return [{"product_code": f"49{i:011d}", "quantity": 1} for i in range(n)]


def test_ut_b_33_100_lines_accepted():
    assert len(QuoteRequest(member_code=None, items=_items(100)).items) == 100


def test_ut_b_34_101_lines_rejected():
    with pytest.raises(ValidationError):
        QuoteRequest(member_code=None, items=_items(101))


def test_ut_b_35_duplicate_product_code_rejected():
    with pytest.raises(ValidationError):
        QuoteRequest(member_code=None, items=[{"product_code": "4901234567894", "quantity": 1}] * 2)


@pytest.mark.parametrize("code", ["4", "4901234567894"])
def test_ut_b_36_product_code_accepted(code):
    assert QuoteItemRequest(product_code=code, quantity=1).product_code == code


@pytest.mark.parametrize("code", ["", "49012345678941", "49012345678AB"])
def test_ut_b_37_product_code_rejected(code):
    with pytest.raises(ValidationError):
        QuoteItemRequest(product_code=code, quantity=1)


@pytest.mark.parametrize("code", ["M", "A" * 32])
def test_ut_b_38_member_code_accepted(code):
    assert QuoteRequest(member_code=code, items=[]).member_code == code


@pytest.mark.parametrize("code", ["", "A" * 33, "M-0001"])
def test_ut_b_39_member_code_rejected(code):
    with pytest.raises(ValidationError):
        QuoteRequest(member_code=code, items=[])


def test_ut_b_40_tax_is_calculated_once_on_the_total():
    """★ K-12（AI 算出）: 15 円 × 1 を 2 行、会員なし → 税抜 30、税 3、税込 33。明細ごとに計算すると税は 2 になる"""
    q = compute_quote([item(1, 15, 1), item(2, 15, 1)], [], TODAY, False, TAX)
    assert totals(q) == (30, 3, 33)


@pytest.mark.parametrize("login_len,pw_len,ok", [(32, 64, True), (33, 64, False), (32, 65, False)])
def test_ut_b_41_login_id_and_password_length(login_len, pw_len, ok):
    try:
        LoginRequest(login_id="a" * login_len, password="p" * pw_len)
        assert ok
    except ValidationError:
        assert not ok
