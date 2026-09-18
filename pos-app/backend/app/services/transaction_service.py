"""TransactionService: 再計算との照合と 1 トランザクションでの保存（設計仕様書 API-06、SEC-05、N-02）。"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import LIMITS
from ..errors import CartEmpty, CartTooManyLines, PriceMismatch
from ..models import DiscountApplication, Product, Staff, Transaction, TransactionItem
from ..schemas import CommitRequest, CommitResponse, QuoteResult
from .pricing_service import PricingService, check_quantity


def compare_with_client(server: QuoteResult, req: CommitRequest) -> list[str]:
    """Frontend の表示値と Backend の再計算値を 1 円単位で比較し、差異のある項目名を返す。"""
    diffs: list[str] = []
    if len(server.lines) != len(req.items):
        diffs.append("items.length")
        return diffs
    for i, (s, c) in enumerate(zip(server.lines, req.items)):
        if s.product_code != c.product_code:
            diffs.append(f"items[{i}].product_code")
        if s.quantity != c.quantity:
            diffs.append(f"items[{i}].quantity")
        if s.unit_price != c.unit_price:
            diffs.append(f"items[{i}].unit_price")
        if (s.discount.amount if s.discount else 0) != c.discount_amount:
            diffs.append(f"items[{i}].discount_amount")
        if s.line_total != c.line_total:
            diffs.append(f"items[{i}].line_total")
    if abs(server.tax_rate - req.tax_rate) > 1e-9:
        diffs.append("tax_rate")
    if server.subtotal_excl_tax != req.subtotal_excl_tax:
        diffs.append("subtotal_excl_tax")
    if server.tax_amount != req.tax_amount:
        diffs.append("tax_amount")
    if server.total_incl_tax != req.total_incl_tax:
        diffs.append("total_incl_tax")
    return diffs


class TransactionService:
    def __init__(self, session: Session, pricing: PricingService):
        self.session = session
        self.pricing = pricing

    def commit(self, req: CommitRequest, staff: Staff) -> CommitResponse:
        # 1. 業務範囲の検証（型・形式は Pydantic で済んでいる）
        if len(req.items) == 0:
            raise CartEmpty()                      # ★ Q-4 の仮置き
        if len(req.items) > LIMITS.CART_MAX_LINES:
            raise CartTooManyLines(details={"max": LIMITS.CART_MAX_LINES})
        for it in req.items:
            check_quantity(it.quantity)

        # 取引時刻・取引日は 1 回だけ取得し、判定と保存に同じ値を使う（6.1）
        ctx = self.pricing.new_context()

        # 2. 再計算と照合。1 円でも差があれば 409 で保存しない
        server = self.pricing.quote(req.member_code, [(i.product_code, i.quantity) for i in req.items], ctx)
        diffs = compare_with_client(server, req)
        if diffs:
            raise PriceMismatch(details={"server": server.model_dump(), "fields": diffs})

        # 3. 1 トランザクションで保存（写し列は Backend の再計算値。line_no は配列順）
        member = self.pricing.find_member(req.member_code)
        products = {
            p.product_code: p
            for p in self.session.execute(
                select(Product).where(Product.product_code.in_([l.product_code for l in server.lines]))
            ).scalars().all()
        }
        try:
            tx = Transaction(
                transacted_at=ctx.now_utc.replace(tzinfo=None),   # DB-4: UTC の naive で保存
                staff_id=staff.id,
                member_id=member.id if member else None,
                subtotal_excl_tax=server.subtotal_excl_tax,
                tax_amount=server.tax_amount,
                total_incl_tax=server.total_incl_tax,
            )
            self.session.add(tx)
            self.session.flush()
            for no, line in enumerate(server.lines, start=1):
                item = TransactionItem(
                    transaction_id=tx.id, line_no=no, product_id=products[line.product_code].id,
                    unit_price=line.unit_price, quantity=line.quantity,
                    discount_amount=line.discount.amount if line.discount else 0,
                    line_total=line.line_total,
                )
                self.session.add(item)
                self.session.flush()
                if line.discount is not None:
                    self.session.add(DiscountApplication(
                        transaction_item_id=item.id, discount_id=line.discount.discount_id,
                        applied_amount=line.discount.amount,
                    ))
            self.session.commit()
        except Exception:
            self.session.rollback()   # N-02: 部分的な取引を残さない
            raise

        return CommitResponse(
            transaction_id=tx.id,
            transacted_at=ctx.now_utc.isoformat().replace("+00:00", "Z"),
            subtotal_excl_tax=server.subtotal_excl_tax,
            tax_amount=server.tax_amount,
            total_incl_tax=server.total_incl_tax,
        )
