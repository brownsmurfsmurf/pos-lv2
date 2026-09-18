"""単体テスト UT-B-01〜43（テスト仕様書 5.1）: PricingService の純粋計算。DB を使わない。"""
from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from app.clock import FixedClock, business_date_of
from app.errors import QuantityOutOfRange, TaxRateNotConfigured
from app.services.pricing_service import (
    DiscountRule, applicable_discount, calc_line, calc_totals, discount_amount_for,
)


def rule(dtype: str, value, start: str, end: str, product_id: int = 1, id: int = 1) -> DiscountRule:
    return DiscountRule(id, product_id, date.fromisoformat(start), date.fromisoformat(end), dtype, Decimal(str(value)))


# ---- calc_line: UT-B-01〜24 ----

@pytest.mark.parametrize("price,qty,expected", [
    (0, 1, 0),            # UT-B-01 単価下限
    (1, 1, 1),            # UT-B-02
    (150, 1, 150),        # UT-B-03 数量下限
    (150, 99, 14850),     # UT-B-04 数量上限
    (150, 2, 300),        # UT-B-05 代表値
    (999, 1, 999), (1000, 1, 1000), (1001, 1, 1001),   # UT-B-06 桁の境界
    (9_999_999, 99, 989_999_901),                       # UT-B-07 ★ 上限で桁あふれしない
])
def test_calc_line_normal(price, qty, expected):
    assert calc_line(price, qty) == expected


@pytest.mark.parametrize("price,qty,disc,expected", [
    (150, 2, ("amount", 20), 260),       # UT-B-08 20 円引き × 2
    (150, 2, ("percent", 20), 240),      # UT-B-09 20% 引き
    (15, 1, ("percent", 10), 14),        # UT-B-10 ★ 1.5 → 1 切り捨て
    (50, 1, ("percent", 8), 46),         # UT-B-11 ★ 4 円引き
    (100, 1, ("percent", 100), 0),       # UT-B-12 全額
    (100, 1, ("amount", 100), 0),        # UT-B-13 行の金額と同額
])
def test_calc_line_discount(price, qty, disc, expected):
    assert calc_line(price, qty, (disc[0], Decimal(disc[1]))) == expected


def test_ut_b_14_discount_exceeds_line_is_capped():
    # Q-7 保留。★ 仮置き: 行の金額を上限（負の小計にしない）
    assert calc_line(100, 1, ("amount", Decimal(150))) == 0


@pytest.mark.parametrize("qty", [0, 100, -1])   # UT-B-15〜17
def test_quantity_out_of_range(qty):
    with pytest.raises(QuantityOutOfRange):
        calc_line(150, qty)


@pytest.mark.parametrize("qty", [1.5, "2", True, None])   # UT-B-18〜21 型の混同・欠損
def test_quantity_type_confusion(qty):
    with pytest.raises(TypeError):
        calc_line(150, qty)


@pytest.mark.parametrize("price", [-1, float("nan"), float("inf")])   # UT-B-22〜23
def test_unit_price_invalid(price):
    with pytest.raises((ValueError, TypeError)):
        calc_line(price, 1)


@pytest.mark.parametrize("dtype", ["PERCENT", " percent", "", "ratio"])   # UT-B-24 表記揺れ
def test_discount_type_variants_rejected(dtype):
    with pytest.raises(ValueError):
        discount_amount_for(100, 1, dtype, Decimal(10))


# ---- applicable_discount: UT-B-25〜35（時計を固定して境界を確認） ----

def bdate(utc_iso: str) -> date:
    return business_date_of(FixedClock(datetime.fromisoformat(utc_iso)).now_utc())


@pytest.mark.parametrize("start,end,utc,applied", [
    ("2026-09-01", "2026-09-30", "2026-09-15T03:00:00+00:00", True),    # UT-B-25 期間内
    ("2026-09-10", "2026-09-30", "2026-09-10T00:00:00+00:00", True),    # UT-B-26 開始日当日（JST 9:00）
    ("2026-09-10", "2026-09-30", "2026-09-09T03:00:00+00:00", False),   # UT-B-27 開始日前日
    ("2026-09-01", "2026-09-09", "2026-09-09T03:00:00+00:00", True),    # UT-B-28 終了日当日を含む
    ("2026-09-01", "2026-09-09", "2026-09-10T03:00:00+00:00", False),   # UT-B-29 終了日翌日
    ("2026-09-01", "2026-09-09", "2026-09-09T14:59:59+00:00", True),    # UT-B-30 JST 23:59:59 → 適用
    ("2026-09-01", "2026-09-09", "2026-09-09T15:00:00+00:00", False),   # UT-B-31 JST 翌 0:00:00 → 非適用
    ("2026-09-10", "2026-09-30", "2026-09-09T15:00:00+00:00", True),    # UT-B-32 JST 9/10 0:00 → 開始
])
def test_discount_period_jst_boundary(start, end, utc, applied):
    r = rule("percent", 10, start, end)
    hit = applicable_discount(1, 100, 1, [r], bdate(utc), has_member=True)
    assert (hit is not None) == applied


def test_ut_b_30_31_would_fail_with_utc_date():
    """UTC の日付で判定すると 15:00:00 のケースも 9/9 と誤判定される（取引日を JST で作る根拠）。"""
    utc_date = datetime.fromisoformat("2026-09-09T15:00:00+00:00").date()
    assert utc_date == date(2026, 9, 9)
    assert bdate("2026-09-09T15:00:00+00:00") == date(2026, 9, 10)


def test_ut_b_33_no_member():
    r = rule("percent", 10, "2026-09-01", "2026-09-30")
    assert applicable_discount(1, 100, 1, [r], date(2026, 9, 15), has_member=False) is None


def test_ut_b_34_other_product():
    r = rule("percent", 10, "2026-09-01", "2026-09-30", product_id=2)
    assert applicable_discount(1, 100, 1, [r], date(2026, 9, 15), has_member=True) is None


def test_ut_b_35_overlapping_picks_max_amount():
    # ★ Q-8 仮置き: 20%（=20 円）と 50 円引き → 50 円
    rules = [rule("percent", 20, "2026-09-01", "2026-09-30", id=1),
             rule("amount", 50, "2026-09-01", "2026-09-30", id=2)]
    hit = applicable_discount(1, 100, 1, rules, date(2026, 9, 15), has_member=True)
    assert hit is not None and hit[0].id == 2 and hit[1] == 50


# ---- calc_totals: UT-B-36〜43 ----

@pytest.mark.parametrize("subtotal,rate,tax,total", [
    (1098, "10", 109, 1207),     # UT-B-36 ★ 109.8 → 109
    (0, "10", 0, 0),             # UT-B-37
    (5, "10", 0, 5), (9, "10", 0, 9), (10, "10", 1, 11),   # UT-B-38 ★ 端数の境界
    (1000, "0", 0, 1000),        # UT-B-39
    (15, "8", 1, 16),            # UT-B-40
    (100, "100", 100, 200),      # UT-B-41
])
def test_calc_totals(subtotal, rate, tax, total):
    assert calc_totals(subtotal, Decimal(rate)) == (tax, total)


@pytest.mark.parametrize("rate", ["100.01", "-0.01"])   # UT-B-42
def test_calc_totals_rate_out_of_range(rate):
    with pytest.raises(ValueError):
        calc_totals(100, Decimal(rate))


def test_ut_b_43_tax_rate_not_configured():
    with pytest.raises(TaxRateNotConfigured):
        calc_totals(100, None)
