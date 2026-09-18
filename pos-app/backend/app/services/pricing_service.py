"""PricingService: 金額計算の正本（設計仕様書 7.4 API-05、SEC-05、6.1 取引日）。

- 値引きの判定・税率の決定・合計の算出はここだけが行う。API-05 と API-06 が共用する
- 取引日（JST）は Clock から得た UTC 時刻を BUSINESS_TIMEZONE に変換して自身で作る
- 端数は 1 円未満切り捨て（★ Q-6, Q-7）、複数該当時は値引き額が最大の 1 件（★ Q-8）
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import ROUND_FLOOR, Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..clock import Clock, business_date_of
from ..config import LIMITS
from ..errors import (
    CartTooManyLines, MemberNotFound, ProductNotFound, QuantityOutOfRange, TaxRateNotConfigured,
)
from ..models import Discount, Member, Product, TaxRate
from ..schemas import AppliedDiscount, QuoteLine, QuoteResult

DISCOUNT_TYPES = ("percent", "amount")


@dataclass(frozen=True)
class DiscountRule:
    """discounts テーブル 1 行分の値（ORM から独立させ、単体テストしやすくする）。"""

    id: int
    product_id: int
    start_date: date
    end_date: date
    discount_type: str
    discount_value: Decimal

    @classmethod
    def from_model(cls, d: Discount) -> "DiscountRule":
        return cls(d.id, d.product_id, d.start_date, d.end_date, d.discount_type, Decimal(d.discount_value))


def _floor(x: Decimal) -> int:
    return int(x.to_integral_value(rounding=ROUND_FLOOR))


def _check_int(name: str, value) -> int:
    # bool は int の派生だが数量・金額として受け付けない（True を 1 と扱わない）
    if type(value) is not int:
        raise TypeError(f"{name} は整数で指定してください")
    return value


# ---- 純粋な計算（DB を使わない。単体テスト UT-B-01〜43 の対象） ----

def check_quantity(quantity) -> int:
    q = _check_int("quantity", quantity)
    if q < LIMITS.QTY_MIN or q > LIMITS.QTY_MAX:
        raise QuantityOutOfRange()
    return q


def check_unit_price(unit_price) -> int:
    p = _check_int("unit_price", unit_price)
    if p < 0 or p > LIMITS.PRICE_MAX:
        raise ValueError("unit_price が範囲外です")
    return p


def discount_amount_for(line_gross: int, quantity: int, discount_type: str, value: Decimal) -> int:
    """1 行の値引き額。percent: line_gross × value / 100、amount: value × quantity。端数は切り捨て。"""
    if discount_type not in DISCOUNT_TYPES:
        raise ValueError(f"discount_type が不正です: {discount_type!r}")
    value = Decimal(value)
    if value < 0:
        raise ValueError("discount_value は 0 以上で指定してください")
    if discount_type == "percent":
        if value > 100:
            raise ValueError("percent の値引きは 100 以下で指定してください")
        amount = _floor(Decimal(line_gross) * value / Decimal(100))
    else:
        amount = _floor(value * quantity)
    # 値引き額が行の金額を超える場合の扱いは Q-7（★ 仮置き: 行の金額を上限とする）
    return min(amount, line_gross)


def calc_line(unit_price, quantity, discount: tuple[str, Decimal] | None = None) -> int:
    """明細の小計 = 単価 × 数量 − 値引き額。"""
    p = check_unit_price(unit_price)
    q = check_quantity(quantity)
    gross = p * q
    if discount is None:
        return gross
    dtype, dvalue = discount
    return gross - discount_amount_for(gross, q, dtype, dvalue)


def applicable_discount(
    product_id: int, line_gross: int, quantity: int, rules: list[DiscountRule],
    business_date: date, has_member: bool,
) -> tuple[DiscountRule, int] | None:
    """会員あり・対象商品・期間内（開始日・終了日を含む）の値引きのうち、値引き額が最大の 1 件（★ Q-8）。"""
    if not has_member:
        return None
    best: tuple[DiscountRule, int] | None = None
    for r in rules:
        if r.product_id != product_id:
            continue
        if not (r.start_date <= business_date <= r.end_date):
            continue
        amount = discount_amount_for(line_gross, quantity, r.discount_type, r.discount_value)
        if best is None or amount > best[1]:
            best = (r, amount)
    return best


def calc_totals(subtotal_excl_tax: int, tax_rate: Decimal | None) -> tuple[int, int]:
    """(税額, 税込合計)。税額 = 税抜合計 × 税率 / 100 を切り捨て（★ Q-6）。"""
    if tax_rate is None:
        raise TaxRateNotConfigured()
    rate = Decimal(tax_rate)
    if rate < 0 or rate > 100:
        raise ValueError("tax_rate は 0〜100 で指定してください")
    tax = _floor(Decimal(subtotal_excl_tax) * rate / Decimal(100))
    return tax, subtotal_excl_tax + tax


# ---- DB を使う組み立て（API-05 / API-06 が呼ぶ） ----

@dataclass(frozen=True)
class QuoteContext:
    now_utc: datetime
    business_date: date


class PricingService:
    def __init__(self, session: Session, clock: Clock):
        self.session = session
        self.clock = clock

    def new_context(self) -> QuoteContext:
        """取引時刻と取引日を 1 回だけ取得する（6.1）。API-06 は判定と保存に同じ値を使う。"""
        now = self.clock.now_utc()
        return QuoteContext(now_utc=now, business_date=business_date_of(now))

    def current_tax_rate(self) -> Decimal | None:
        row = self.session.execute(select(TaxRate).order_by(TaxRate.id.desc()).limit(1)).scalar_one_or_none()
        return None if row is None else Decimal(row.rate)

    def find_member(self, member_code: str | None) -> Member | None:
        if member_code is None:
            return None
        m = self.session.execute(select(Member).where(Member.member_code == member_code)).scalar_one_or_none()
        if m is None:
            raise MemberNotFound()
        return m

    def find_products(self, codes: list[str]) -> dict[str, Product]:
        if not codes:
            return {}
        rows = self.session.execute(select(Product).where(Product.product_code.in_(codes))).scalars().all()
        found = {p.product_code: p for p in rows}
        for c in codes:
            if c not in found:
                raise ProductNotFound(details={"product_code": c})
        return found

    def rules_for(self, product_ids: list[int], business_date: date) -> list[DiscountRule]:
        if not product_ids:
            return []
        rows = self.session.execute(
            select(Discount).where(
                Discount.product_id.in_(product_ids),
                Discount.start_date <= business_date,   # DB-4: 日付は Backend が作りバインド変数で渡す
                Discount.end_date >= business_date,
            )
        ).scalars().all()
        return [DiscountRule.from_model(d) for d in rows]

    def quote(self, member_code: str | None, items: list[tuple[str, int]], ctx: QuoteContext) -> QuoteResult:
        """購入リスト＋会員IDから値引き・税・合計を算出する（API-05 の本体）。"""
        if len(items) > LIMITS.CART_MAX_LINES:
            raise CartTooManyLines(details={"max": LIMITS.CART_MAX_LINES})
        for _, q in items:
            check_quantity(q)

        member = self.find_member(member_code)
        products = self.find_products([code for code, _ in items])
        rules = self.rules_for([p.id for p in products.values()], ctx.business_date) if member else []
        tax_rate = self.current_tax_rate()
        if tax_rate is None:
            raise TaxRateNotConfigured()

        lines: list[QuoteLine] = []
        subtotal = 0
        for code, qty in items:
            p = products[code]
            gross = p.unit_price * qty
            hit = applicable_discount(p.id, gross, qty, rules, ctx.business_date, member is not None)
            applied = None
            amount = 0
            if hit is not None:
                rule, amount = hit
                applied = AppliedDiscount(
                    discount_id=rule.id, type=rule.discount_type, value=float(rule.discount_value), amount=amount
                )
            line_total = gross - amount
            subtotal += line_total
            lines.append(QuoteLine(
                product_code=p.product_code, product_name=p.name, unit_price=p.unit_price,
                quantity=qty, discount=applied, line_total=line_total,
            ))

        tax, total = calc_totals(subtotal, tax_rate)
        return QuoteResult(
            tax_rate=float(tax_rate), lines=lines,
            subtotal_excl_tax=subtotal, tax_amount=tax, total_incl_tax=total,
        )
