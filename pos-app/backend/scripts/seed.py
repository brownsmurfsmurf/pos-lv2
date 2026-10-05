"""初期データの投入（設計仕様書 v2 の DB-5: 税率・値引き・商品・担当者は SQL／スクリプトで入れる）。

使い方（backend フォルダで）:
    python -m scripts.seed              テーブルを作り、初期データを入れる
    python -m scripts.seed --reset      既存のテーブルを消して作り直す（開発用）

入るデータ（テスト仕様書 v2 の E-1〜E-3 をそのまま試せる）:
  担当者  staff01 / pos-staff-01、staff02 / pos-staff-02
  商品 A  4901234567894 緑茶 500ml 150 円      … 会員は 20% 引き（期間内）  → E-1, E-2
  商品 B  4901234567900 食パン 6枚切 188 円    … 値引きなし                → E-2
  商品 C  4901234567917 牛乳 1L 240 円         … 20% 引きだが終了日は昨日   → E-3
  商品 D  4901234567924 卵 10個 270 円         … 会員は 20 円引き（期間内）
  会員    M0001、M0002
  税率    10%
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
        Staff(login_id="staff01", password_hash=hash_password("pos-staff-01")),
        Staff(login_id="staff02", password_hash=hash_password("pos-staff-02")),
    ])
    a = Product(product_code="4901234567894", name="緑茶 500ml", unit_price=150)
    b = Product(product_code="4901234567900", name="食パン 6枚切", unit_price=188)
    c = Product(product_code="4901234567917", name="牛乳 1L", unit_price=240)
    d = Product(product_code="4901234567924", name="卵 10個", unit_price=270)
    session.add_all([a, b, c, d])
    session.add_all([
        Member(member_code="M0001", name="山田 太郎", phone="090-0000-0001", address="東京都千代田区1-1", gender="男性", age=34),
        Member(member_code="M0002", name="高橋 美咲", phone="090-0000-0002", address="東京都新宿区2-2", gender="女性", age=28),
    ])
    session.add(TaxRate(rate=Decimal("10.00")))
    session.flush()
    session.add_all([
        # 商品 A: 期間内の 20% 引き
        Discount(product_id=a.id, start_date=today - timedelta(days=7), end_date=today + timedelta(days=30),
                 discount_type="percent", discount_value=Decimal("20.00")),
        # 商品 C: 20% 引きだが、終了日は昨日（期間切れ）
        Discount(product_id=c.id, start_date=today - timedelta(days=30), end_date=today - timedelta(days=1),
                 discount_type="percent", discount_value=Decimal("20.00")),
        # 商品 D: 期間内の 20 円引き
        Discount(product_id=d.id, start_date=today - timedelta(days=1), end_date=today + timedelta(days=30),
                 discount_type="amount", discount_value=Decimal("20.00")),
    ])
    session.commit()
    print("初期データを投入しました。")


def main() -> None:
    from app.config import get_settings

    if get_settings().db_host and "--allow-remote" not in sys.argv:
        print("DB_HOST が設定されています（手元ではない DB）。\n"
              "このスクリプトは学習用の担当者（パスワードは README に公開）を入れます。\n"
              "共用・本番の DB に入れてよい場合だけ、--allow-remote を付けて実行してください。")
        sys.exit(1)
    if "--reset" in sys.argv:
        Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    today = business_date_of(SystemClock().now_utc())   # 値引きの日付は日本時間の暦日（K-35）
    with Session(engine) as session:
        seed(session, today)


if __name__ == "__main__":
    main()
