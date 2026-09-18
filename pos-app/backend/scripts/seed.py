"""初期データ投入（設計仕様書 6.4: 税率・値引きは SQL／シードで投入する）。

使い方（backend ディレクトリで）:
    python -m scripts.seed              # テーブル作成 + 初期データ
    python -m scripts.seed --reset      # 既存テーブルを削除して作り直す（開発用）

テスト仕様書 7 章の UAT 用データに合わせている:
  商品 A（値引き 20%・期間内）、商品 B（値引きなし）、商品 C（値引き終了日が昨日）
  会員 M1（登録済み）。担当者 staff01 / password: pos-staff-01
"""
from __future__ import annotations

import sys
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.clock import SystemClock, business_date_of
from app.db import Base, engine
from app.models import Discount, Member, Product, Staff, TaxRate
from app.security import hash_password


def seed(session: Session, today: date) -> None:
    if session.execute(select(Staff).limit(1)).first():
        print("既にデータがあります。--reset で作り直せます。")
        return

    session.add_all([
        Staff(login_id="staff01", password_hash=hash_password("pos-staff-01"), name="佐藤 花子"),
        Staff(login_id="staff02", password_hash=hash_password("pos-staff-02"), name="鈴木 一郎"),
    ])
    a = Product(product_code="4901234567894", name="緑茶 500ml", unit_price=150)
    b = Product(product_code="4901234567900", name="食パン 6枚切", unit_price=188)
    c = Product(product_code="4901234567917", name="牛乳 1L", unit_price=240)
    d = Product(product_code="4901234567924", name="卵 10個", unit_price=270)
    e = Product(product_code="4901234567931", name="ヨーグルト 400g", unit_price=160)
    session.add_all([a, b, c, d, e])
    session.add_all([
        Member(member_code="M0001", name="山田 太郎", phone="090-0000-0001", address="東京都千代田区1-1", gender="男性", age=34),
        Member(member_code="M0002", name="高橋 美咲", phone="090-0000-0002", address="東京都新宿区2-2", gender="女性", age=28),
    ])
    session.add(TaxRate(rate=Decimal("10.00")))
    session.flush()
    session.add_all([
        # 商品 A: 期間内 20% 引き
        Discount(product_id=a.id, start_date=today - timedelta(days=7), end_date=today + timedelta(days=30),
                 discount_type="percent", discount_value=Decimal("20.00")),
        # 商品 C: 終了日が昨日（期間切れ）
        Discount(product_id=c.id, start_date=today - timedelta(days=30), end_date=today - timedelta(days=1),
                 discount_type="amount", discount_value=Decimal("30.00")),
        # 商品 D: 期間内 20 円引き
        Discount(product_id=d.id, start_date=today - timedelta(days=1), end_date=today + timedelta(days=1),
                 discount_type="amount", discount_value=Decimal("20.00")),
    ])
    session.commit()
    print("初期データを投入しました。")


def main() -> None:
    if "--reset" in sys.argv:
        Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    today = business_date_of(SystemClock().now_utc())
    with Session(engine) as session:
        seed(session, today)


if __name__ == "__main__":
    main()
