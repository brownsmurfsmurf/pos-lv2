"""結合テスト（テスト仕様書 v2 の 5 章のうち API 側）。TestClient + SQLite。

BFF の結合テスト（IT-04〜06、IT-29）は frontend/__tests__/bff.test.ts にある。
"""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select

from app.models import DiscountApplication, Product, ProductPriceHistory, TaxRate, Transaction, TransactionItem
from scripts.change_price import change_price

from .conftest import A, B, C, D


def quote(client, headers, member, items):
    return client.post("/api/v1/pricing/quote", json={"member_code": member, "items": items}, headers=headers)


def commit_body(q: dict, member):
    """API-05 の応答の値を組み替えて API-06 の入力を作る（値は書き換えない）。"""
    return {
        "member_code": member,
        "items": [{"product_code": l["product_code"], "quantity": l["quantity"], "unit_price": l["unit_price"],
                   "discount_amount": l["discount"]["amount"] if l["discount"] else 0,
                   "line_total": l["line_total"]} for l in q["lines"]],
        "tax_rate": q["tax_rate"], "subtotal_excl_tax": q["subtotal_excl_tax"],
        "tax_amount": q["tax_amount"], "total_incl_tax": q["total_incl_tax"],
    }


def totals(q: dict):
    return q["subtotal_excl_tax"], q["tax_amount"], q["total_incl_tax"]


# ---- ログイン ----

def test_it_01_login_ok(client, seeded):
    r = client.post("/api/v1/auth/login", json={"login_id": "staff01", "password": "pos-staff-01"})
    assert r.status_code == 200
    body = r.json()
    assert body["token_type"] == "Bearer" and body["access_token"]
    assert body["staff"] == {"id": body["staff"]["id"], "login_id": "staff01"}


def test_it_02_login_failures_same_body(client, seeded):
    r1 = client.post("/api/v1/auth/login", json={"login_id": "nobody", "password": "pos-staff-01"})
    r2 = client.post("/api/v1/auth/login", json={"login_id": "staff01", "password": "wrong"})
    assert r1.status_code == r2.status_code == 401 and r1.json() == r2.json()
    assert r1.json()["error"]["code"] == "AUTH_INVALID_CREDENTIALS"


def test_it_03_login_type_error_400(client, seeded):
    r = client.post("/api/v1/auth/login", json={"login_id": 123, "password": None})
    assert r.status_code == 400 and r.json()["error"]["code"] == "VALIDATION_ERROR"


def test_it_06_no_token_401(client, seeded):
    r = client.get("/api/v1/auth/me")
    assert r.status_code == 401 and r.json()["error"]["code"] == "AUTH_REQUIRED"


def test_it_07_me_returns_login_id_only(client, auth_header):
    r = client.get("/api/v1/auth/me", headers=auth_header)
    assert r.status_code == 200 and set(r.json()) == {"id", "login_id"} and r.json()["login_id"] == "staff01"


# ---- 商品・会員 ----

def test_it_08_product_found(client, auth_header):
    r = client.get(f"/api/v1/products/{A}", headers=auth_header)
    assert r.status_code == 200 and r.json()["name"] == "緑茶 500ml" and r.json()["unit_price"] == 150


def test_it_09_product_not_found(client, auth_header):
    r = client.get("/api/v1/products/4900000000000", headers=auth_header)
    assert r.status_code == 404 and r.json()["error"]["code"] == "PRODUCT_NOT_FOUND"


def test_it_10_product_code_format_400(client, auth_header):
    for code in ["49012345678901", "49012345678AB"]:
        assert client.get(f"/api/v1/products/{code}", headers=auth_header).status_code == 400, code


def test_it_11_member_found_id_only(client, auth_header):
    r = client.get("/api/v1/members/M0001", headers=auth_header)
    assert r.status_code == 200
    assert set(r.json()) == {"id", "member_code"} and r.json()["member_code"] == "M0001"   # 氏名・住所を返さない


def test_it_12_member_not_found(client, auth_header):
    r = client.get("/api/v1/members/M9999", headers=auth_header)
    assert r.status_code == 404 and r.json()["error"]["code"] == "MEMBER_NOT_FOUND"


# ---- 見積（人が決めた期待値） ----

def test_it_13_quote_e1(client, auth_header):
    """E-1（人）: 150 円 × 2、会員、20% 引き → 240／24／264"""
    q = quote(client, auth_header, "M0001", [{"product_code": A, "quantity": 2}]).json()
    assert totals(q) == (240, 24, 264)


def test_it_14_quote_e3(client, auth_header):
    """E-3（人）: 240 円 × 1、会員、値引きは昨日で終了 → 240／24／264"""
    q = quote(client, auth_header, "M0001", [{"product_code": C, "quantity": 1}]).json()
    assert totals(q) == (240, 24, 264) and q["lines"][0]["discount"] is None


def test_it_15_quote_e2(client, auth_header):
    """E-2（人）: 188 円 × 1 と 150 円 × 2（20% 引き）、会員 → 428／42／470"""
    q = quote(client, auth_header, "M0001", [{"product_code": B, "quantity": 1}, {"product_code": A, "quantity": 2}]).json()
    assert totals(q) == (428, 42, 470)


def test_it_16_business_date_boundary(client, auth_header, clock):
    """商品 D の値引きは 9/1〜9/9。UTC 9/9 14:59:59 は日本時間 9/9、15:00:00 は 9/10。"""
    clock.set("2026-09-09T14:59:59Z")
    q1 = quote(client, auth_header, "M0001", [{"product_code": D, "quantity": 1}]).json()
    clock.set("2026-09-09T15:00:00Z")
    q2 = quote(client, auth_header, "M0001", [{"product_code": D, "quantity": 1}]).json()
    assert q1["lines"][0]["discount"]["amount"] == 20 and q2["lines"][0]["discount"] is None


def test_it_17_quantity_range_422(client, auth_header):
    for qty in (0, 100):
        r = quote(client, auth_header, None, [{"product_code": A, "quantity": qty}])
        assert r.status_code == 422 and r.json()["error"]["code"] == "QUANTITY_OUT_OF_RANGE", qty


def test_it_18_quantity_type_400(client, auth_header):
    for qty in (1.5, None):
        r = quote(client, auth_header, None, [{"product_code": A, "quantity": qty}])
        assert r.status_code == 400 and r.json()["error"]["code"] == "VALIDATION_ERROR", qty


# ---- 確定 ----

def test_it_19_commit_and_persist(client, auth_header, session, seeded):
    q = quote(client, auth_header, "M0001", [{"product_code": A, "quantity": 2}, {"product_code": B, "quantity": 1}]).json()
    r = client.post("/api/v1/transactions", json=commit_body(q, "M0001"), headers=auth_header)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["total_incl_tax"] == 470 and body["transacted_at"] == "2026-09-15T03:00:00Z"

    tx = session.get(Transaction, body["transaction_id"])
    assert tx.staff_id == seeded["staff"].id and tx.member_id == seeded["member"].id        # 誰が処理・誰が買った
    assert str(tx.transacted_at) == "2026-09-15 03:00:00"                                    # いつ（UTC）
    assert Decimal(tx.tax_rate) == Decimal("10")                                             # 税率の写し
    assert (tx.subtotal_excl_tax, tx.tax_amount, tx.total_incl_tax) == (428, 42, 470)
    items = session.execute(select(TransactionItem).where(TransactionItem.transaction_id == tx.id)
                            .order_by(TransactionItem.line_no)).scalars().all()
    assert [(i.line_no, i.unit_price, i.quantity, i.discount_amount, i.line_total) for i in items] == [
        (1, 150, 2, 60, 240), (2, 188, 1, 0, 188)]                                           # 何を・いくつ・いくらで
    apps = session.execute(select(DiscountApplication)).scalars().all()
    assert len(apps) == 1 and apps[0].applied_amount == 60                                   # 値引きの適用記録


def test_it_20_commit_without_member(client, auth_header, session):
    q = quote(client, auth_header, None, [{"product_code": A, "quantity": 1}]).json()
    r = client.post("/api/v1/transactions", json=commit_body(q, None), headers=auth_header)
    assert r.status_code == 201 and session.get(Transaction, r.json()["transaction_id"]).member_id is None


def test_it_21_price_mismatch_not_saved(client, auth_header, session):
    q = quote(client, auth_header, "M0001", [{"product_code": A, "quantity": 2}]).json()
    body = commit_body(q, "M0001")
    body["total_incl_tax"] += 1
    r = client.post("/api/v1/transactions", json=body, headers=auth_header)
    assert r.status_code == 409 and r.json()["error"]["code"] == "PRICE_MISMATCH"
    assert r.json()["error"]["details"]["server"]["total_incl_tax"] == 264
    assert session.execute(select(Transaction)).first() is None


def test_it_22_history_unchanged_after_price_change(client, auth_header, session, seeded):
    q = quote(client, auth_header, None, [{"product_code": A, "quantity": 1}]).json()
    tx_id = client.post("/api/v1/transactions", json=commit_body(q, None), headers=auth_header).json()["transaction_id"]
    change_price(session, A, 999)
    item = session.execute(select(TransactionItem).where(TransactionItem.transaction_id == tx_id)).scalar_one()
    assert item.unit_price == 150 and session.get(Transaction, tx_id).total_incl_tax == 165


def test_it_23_empty_cart_422(client, auth_header):
    body = {"member_code": None, "items": [], "tax_rate": 10.0, "subtotal_excl_tax": 0, "tax_amount": 0, "total_incl_tax": 0}
    r = client.post("/api/v1/transactions", json=body, headers=auth_header)
    assert r.status_code == 422 and r.json()["error"]["code"] == "CART_EMPTY"


def test_it_24_failure_mid_save_rolls_back(client, auth_header, session, monkeypatch):
    from app.services import transaction_service as ts

    def exploding(*a, **k):
        raise RuntimeError("simulated failure")

    monkeypatch.setattr(ts, "DiscountApplication", exploding)
    q = quote(client, auth_header, "M0001", [{"product_code": A, "quantity": 1}]).json()
    r = client.post("/api/v1/transactions", json=commit_body(q, "M0001"), headers=auth_header)
    assert r.status_code == 500 and r.json()["error"]["code"] == "INTERNAL_ERROR"
    assert session.execute(select(Transaction)).first() is None
    assert session.execute(select(TransactionItem)).first() is None


# ---- 運用・セキュリティ ----

def test_it_25_health(client, session):
    r = client.get("/api/v1/health")
    assert r.status_code == 200 and r.json() == {"status": "ok", "db": "ok"}


def test_it_26_cors_other_origin_not_allowed(client, seeded):
    r = client.options("/api/v1/auth/login", headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "POST"})
    assert "access-control-allow-origin" not in {k.lower() for k in r.headers}
    r = client.options("/api/v1/auth/login", headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "POST"})
    assert r.headers.get("access-control-allow-origin") == "http://localhost:3000"


def test_it_27_docs_hidden_outside_development(client):
    assert client.get("/docs").status_code == 404
    assert client.get("/openapi.json").status_code == 404


def test_it_28_sql_injection_rejected(client, auth_header, session):
    r = client.get("/api/v1/products/' OR '1'='1", headers=auth_header)
    assert r.status_code == 400
    assert session.execute(select(Product)).first() is not None


def test_it_30_price_change_keeps_history(session, seeded):
    h = change_price(session, A, 160)
    assert (h.old_unit_price, h.new_unit_price) == (150, 160) and h.changed_at is not None
    assert seeded["a"].unit_price == 160
    rows = session.execute(select(ProductPriceHistory)).scalars().all()
    assert len(rows) == 1
    # 途中で失敗したら、単価も履歴も元のまま
    try:
        change_price(session, A, -1)
    except ValueError:
        pass
    assert seeded["a"].unit_price == 160 and len(session.execute(select(ProductPriceHistory)).scalars().all()) == 1


def test_it_31_expired_token_401(client, auth_header, clock):
    clock.set("2026-09-15T11:00:00Z")   # 発行（03:00）からちょうど 8 時間
    r = client.get("/api/v1/auth/me", headers=auth_header)
    assert r.status_code == 401 and r.json()["error"]["code"] == "AUTH_REQUIRED"


def test_it_32_unknown_product_or_member_in_quote_and_commit(client, auth_header, session):
    r = quote(client, auth_header, None, [{"product_code": "4900000000000", "quantity": 1}])
    assert r.status_code == 404 and r.json()["error"]["code"] == "PRODUCT_NOT_FOUND"
    r = quote(client, auth_header, "M9999", [{"product_code": A, "quantity": 1}])
    assert r.status_code == 404 and r.json()["error"]["code"] == "MEMBER_NOT_FOUND"
    body = {"member_code": "M9999", "items": [{"product_code": A, "quantity": 1, "unit_price": 150, "discount_amount": 0, "line_total": 150}],
            "tax_rate": 10.0, "subtotal_excl_tax": 150, "tax_amount": 15, "total_incl_tax": 165}
    r = client.post("/api/v1/transactions", json=body, headers=auth_header)
    assert r.status_code == 404 and session.execute(select(Transaction)).first() is None


def test_it_33_business_date_at_commit(client, auth_header, session, clock):
    """見積は UTC 9/9 14:59:59（値引きあり）。15:00:00 に進めて確定すると値引きが外れて 409。"""
    clock.set("2026-09-09T14:59:59Z")
    r = client.post("/api/v1/auth/login", json={"login_id": "staff01", "password": "pos-staff-01"})
    h = {"Authorization": f"Bearer {r.json()['access_token']}"}
    q = quote(client, h, "M0001", [{"product_code": D, "quantity": 1}]).json()
    assert q["lines"][0]["discount"]["amount"] == 20

    clock.set("2026-09-09T15:00:00Z")
    r = client.post("/api/v1/transactions", json=commit_body(q, "M0001"), headers=h)
    assert r.status_code == 409 and session.execute(select(Transaction)).first() is None

    clock.set("2026-09-09T14:59:59Z")
    r = client.post("/api/v1/transactions", json=commit_body(q, "M0001"), headers=h)
    assert r.status_code == 201 and r.json()["transacted_at"] == "2026-09-09T14:59:59Z"


def test_tax_rate_not_configured_422(client, auth_header, session):
    for t in session.execute(select(TaxRate)).scalars():
        session.delete(t)
    session.commit()
    r = quote(client, auth_header, None, [{"product_code": A, "quantity": 1}])
    assert r.status_code == 422 and r.json()["error"]["code"] == "TAX_RATE_NOT_CONFIGURED"
