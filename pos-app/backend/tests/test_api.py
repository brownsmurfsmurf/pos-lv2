"""結合テスト IT-01〜32 のうち API 側（テスト仕様書 6.1）。TestClient + SQLite。"""
from __future__ import annotations

from sqlalchemy import select

from app.models import DiscountApplication, Transaction, TransactionItem

A, B, C, D = "4901234567894", "4901234567900", "4901234567917", "4901234567924"


def quote(client, headers, member, items):
    return client.post("/api/v1/pricing/quote", json={"member_code": member, "items": items}, headers=headers)


def commit_body(q: dict, member):
    return {
        "member_code": member,
        "items": [{"product_code": l["product_code"], "quantity": l["quantity"], "unit_price": l["unit_price"],
                   "discount_amount": l["discount"]["amount"] if l["discount"] else 0,
                   "line_total": l["line_total"]} for l in q["lines"]],
        "tax_rate": q["tax_rate"], "subtotal_excl_tax": q["subtotal_excl_tax"],
        "tax_amount": q["tax_amount"], "total_incl_tax": q["total_incl_tax"],
    }


# ---- IT-01〜03, 07: ログイン ----

def test_it_01_login_ok(client, seeded):
    r = client.post("/api/v1/auth/login", json={"login_id": "staff01", "password": "pos-staff-01"})
    assert r.status_code == 200
    body = r.json()
    assert body["token_type"] == "Bearer" and body["staff"]["name"] == "佐藤 花子" and body["access_token"]


def test_it_02_login_failures_same_body(client, seeded):
    r1 = client.post("/api/v1/auth/login", json={"login_id": "nobody", "password": "pos-staff-01"})
    r2 = client.post("/api/v1/auth/login", json={"login_id": "staff01", "password": "wrong"})
    assert r1.status_code == r2.status_code == 401
    assert r1.json() == r2.json()
    assert r1.json()["error"]["code"] == "AUTH_INVALID_CREDENTIALS"


def test_it_03_login_type_error_400(client, seeded):
    r = client.post("/api/v1/auth/login", json={"login_id": 123, "password": None})
    assert r.status_code == 400 and r.json()["error"]["code"] == "VALIDATION_ERROR"


def test_it_06_no_or_bad_token_401(client, seeded):
    assert client.get("/api/v1/auth/me").status_code == 401
    r = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer not.a.token"})
    assert r.status_code == 401 and r.json()["error"]["code"] == "AUTH_REQUIRED"


def test_it_07_me(client, auth_header):
    r = client.get("/api/v1/auth/me", headers=auth_header)
    assert r.status_code == 200 and r.json()["login_id"] == "staff01"


# ---- IT-08〜10: 商品 ----

def test_it_08_product_found(client, auth_header):
    r = client.get(f"/api/v1/products/{A}", headers=auth_header)
    assert r.status_code == 200 and r.json()["name"] == "緑茶 500ml" and r.json()["unit_price"] == 150


def test_it_09_product_not_found(client, auth_header):
    r = client.get("/api/v1/products/4900000000000", headers=auth_header)
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "PRODUCT_NOT_FOUND"
    assert r.json()["error"]["message"] == "商品がマスタ未登録です"


def test_it_10_product_code_format_400(client, auth_header):
    for code in ["49012345678901", "49012345678AB"]:   # 14 桁 / 英字混じり
        r = client.get(f"/api/v1/products/{code}", headers=auth_header)
        assert r.status_code == 400, code


# ---- IT-11〜12: 会員 ----

def test_it_11_member_found_name_only(client, auth_header):
    r = client.get("/api/v1/members/M0001", headers=auth_header)
    assert r.status_code == 200
    assert r.json() == {"id": r.json()["id"], "member_code": "M0001", "name": "山田 太郎"}
    assert "address" not in r.json()


def test_it_12_member_not_found(client, auth_header):
    r = client.get("/api/v1/members/M9999", headers=auth_header)
    assert r.status_code == 404 and r.json()["error"]["code"] == "MEMBER_NOT_FOUND"


# ---- IT-13〜20: 見積 ----

def test_it_13_quote_no_member(client, auth_header):
    r = quote(client, auth_header, None, [{"product_code": A, "quantity": 2}, {"product_code": B, "quantity": 1},
                                          {"product_code": C, "quantity": 1}])
    assert r.status_code == 200
    q = r.json()
    assert all(l["discount"] is None for l in q["lines"])
    assert q["subtotal_excl_tax"] == 300 + 188 + 240 == 728
    assert q["tax_amount"] == 72 and q["total_incl_tax"] == 800


def test_it_14_quote_member_discount(client, auth_header):
    r = quote(client, auth_header, "M0001", [{"product_code": A, "quantity": 2}, {"product_code": B, "quantity": 1}])
    q = r.json()
    assert q["lines"][0]["discount"] == {"discount_id": 1, "type": "percent", "value": 20.0, "amount": 60}
    assert q["lines"][0]["line_total"] == 240 and q["lines"][1]["discount"] is None
    assert q["subtotal_excl_tax"] == 428 and q["tax_amount"] == 42 and q["total_incl_tax"] == 470


def test_it_15_discount_ended_yesterday_not_applied(client, auth_header):
    q = quote(client, auth_header, "M0001", [{"product_code": C, "quantity": 1}]).json()
    assert q["lines"][0]["discount"] is None


def test_it_16_jst_boundary_via_api(client, auth_header, clock):
    """商品 D の値引きは 9/1〜9/9。UTC 9/9 14:59:59（JST 23:59:59）は適用、15:00:00（JST 9/10）は非適用。"""
    clock.set("2026-09-09T14:59:59Z")
    q1 = quote(client, auth_header, "M0001", [{"product_code": D, "quantity": 1}]).json()
    clock.set("2026-09-09T15:00:00Z")
    q2 = quote(client, auth_header, "M0001", [{"product_code": D, "quantity": 1}]).json()
    assert q1["lines"][0]["discount"]["amount"] == 20
    assert q2["lines"][0]["discount"] is None


def test_it_17_quantity_range_422(client, auth_header):
    for qty in (0, 100):
        r = quote(client, auth_header, None, [{"product_code": A, "quantity": qty}])
        assert r.status_code == 422 and r.json()["error"]["code"] == "QUANTITY_OUT_OF_RANGE", qty


def test_it_18_quantity_type_400(client, auth_header):
    r = quote(client, auth_header, None, [{"product_code": A, "quantity": "2"}])
    assert r.status_code == 400 and r.json()["error"]["code"] == "VALIDATION_ERROR"


def test_it_19_cart_max_lines(client, auth_header, session):
    from app.models import Product
    session.add_all([Product(product_code=f"49{n:011d}", name=f"p{n}", unit_price=1) for n in range(101)])
    session.commit()
    items = [{"product_code": f"49{n:011d}", "quantity": 1} for n in range(100)]
    assert quote(client, auth_header, None, items).status_code == 200
    items.append({"product_code": f"49{100:011d}", "quantity": 1})
    assert quote(client, auth_header, None, items).status_code == 422


def test_it_20_tax_rate_not_configured(client, auth_header, session):
    from app.models import TaxRate
    for t in session.execute(select(TaxRate)).scalars():
        session.delete(t)
    session.commit()
    r = quote(client, auth_header, None, [{"product_code": A, "quantity": 1}])
    assert r.status_code == 422 and r.json()["error"]["code"] == "TAX_RATE_NOT_CONFIGURED"


# ---- IT-21〜27: 確定 ----

def test_it_21_22_commit_and_persist(client, auth_header, session, seeded):
    q = quote(client, auth_header, "M0001", [{"product_code": A, "quantity": 2}, {"product_code": B, "quantity": 1}]).json()
    r = client.post("/api/v1/transactions", json=commit_body(q, "M0001"), headers=auth_header)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["total_incl_tax"] == 470 and body["transacted_at"] == "2026-09-15T03:00:00Z"

    tx = session.get(Transaction, body["transaction_id"])
    assert tx.staff_id == seeded["staff"].id and tx.member_id == seeded["member"].id
    assert (tx.subtotal_excl_tax, tx.tax_amount, tx.total_incl_tax) == (428, 42, 470)
    items = session.execute(select(TransactionItem).where(TransactionItem.transaction_id == tx.id)
                            .order_by(TransactionItem.line_no)).scalars().all()
    assert [(i.line_no, i.unit_price, i.quantity, i.discount_amount, i.line_total) for i in items] == [
        (1, 150, 2, 60, 240), (2, 188, 1, 0, 188)]
    apps = session.execute(select(DiscountApplication)).scalars().all()
    assert len(apps) == 1 and apps[0].applied_amount == 60


def test_it_21b_commit_without_member(client, auth_header, session):
    q = quote(client, auth_header, None, [{"product_code": A, "quantity": 1}]).json()
    r = client.post("/api/v1/transactions", json=commit_body(q, None), headers=auth_header)
    assert r.status_code == 201
    assert session.get(Transaction, r.json()["transaction_id"]).member_id is None


def test_it_23_24_price_mismatch_not_saved(client, auth_header, session):
    q = quote(client, auth_header, "M0001", [{"product_code": A, "quantity": 2}]).json()
    body = commit_body(q, "M0001")
    body["total_incl_tax"] += 1
    r = client.post("/api/v1/transactions", json=body, headers=auth_header)
    assert r.status_code == 409 and r.json()["error"]["code"] == "PRICE_MISMATCH"
    assert r.json()["error"]["details"]["server"]["total_incl_tax"] == q["total_incl_tax"]

    body = commit_body(q, "M0001")
    body["items"][0]["unit_price"] = 100   # 単価を安く改ざん
    body["items"][0]["line_total"] = 160
    assert client.post("/api/v1/transactions", json=body, headers=auth_header).status_code == 409
    assert session.execute(select(Transaction)).first() is None


def test_it_25_history_immutable_after_price_change(client, auth_header, session, seeded):
    q = quote(client, auth_header, None, [{"product_code": A, "quantity": 1}]).json()
    tx_id = client.post("/api/v1/transactions", json=commit_body(q, None), headers=auth_header).json()["transaction_id"]
    seeded["a"].unit_price = 999
    session.commit()
    item = session.execute(select(TransactionItem).where(TransactionItem.transaction_id == tx_id)).scalar_one()
    assert item.unit_price == 150 and session.get(Transaction, tx_id).total_incl_tax == 165


def test_it_26_cart_empty(client, auth_header):
    body = {"member_code": None, "items": [], "tax_rate": 10.0, "subtotal_excl_tax": 0, "tax_amount": 0, "total_incl_tax": 0}
    r = client.post("/api/v1/transactions", json=body, headers=auth_header)
    assert r.status_code == 422 and r.json()["error"]["code"] == "CART_EMPTY"


def test_it_27_failure_mid_save_rolls_back(client, auth_header, session, monkeypatch):
    from app.services import transaction_service as ts

    original = ts.DiscountApplication

    class Boom(Exception):
        pass

    def exploding(*a, **k):
        raise Boom("simulated failure")

    monkeypatch.setattr(ts, "DiscountApplication", exploding)
    q = quote(client, auth_header, "M0001", [{"product_code": A, "quantity": 1}]).json()
    r = client.post("/api/v1/transactions", json=commit_body(q, "M0001"), headers=auth_header)
    assert r.status_code == 500 and r.json()["error"]["code"] == "INTERNAL_ERROR"
    assert session.execute(select(Transaction)).first() is None
    assert session.execute(select(TransactionItem)).first() is None
    monkeypatch.setattr(ts, "DiscountApplication", original)


# ---- IT-28〜32: 運用・セキュリティ ----

def test_it_28_health(client, session):
    r = client.get("/api/v1/health")
    assert r.status_code == 200 and r.json() == {"status": "ok", "db": "ok"}


def test_it_29_cors_other_origin_rejected(client, seeded):
    r = client.options("/api/v1/auth/login", headers={"Origin": "https://evil.example",
                                                      "Access-Control-Request-Method": "POST"})
    assert "access-control-allow-origin" not in {k.lower() for k in r.headers}
    r = client.options("/api/v1/auth/login", headers={"Origin": "http://localhost:3000",
                                                      "Access-Control-Request-Method": "POST"})
    assert r.headers.get("access-control-allow-origin") == "http://localhost:3000"


def test_it_30_docs_hidden_outside_development(client):
    # conftest は APP_ENV=test で起動している
    assert client.get("/docs").status_code == 404
    assert client.get("/openapi.json").status_code == 404


def test_it_31_sql_injection_rejected(client, auth_header, session):
    from app.models import Product
    r = client.get("/api/v1/products/' OR '1'='1", headers=auth_header)
    assert r.status_code == 400
    assert session.execute(select(Product)).first() is not None


def test_it_32_unexpected_error_hides_details(client, auth_header, monkeypatch):
    from app.routers import products as pr

    def boom(*a, **k):
        raise RuntimeError("secret internal detail")

    monkeypatch.setattr(pr, "select", boom)
    r = client.get(f"/api/v1/products/{A}", headers=auth_header)
    assert r.status_code == 500
    assert r.json()["error"]["code"] == "INTERNAL_ERROR" and "secret" not in r.text
