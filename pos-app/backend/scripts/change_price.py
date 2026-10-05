"""商品の単価を変える手順（設計仕様書 v2 の DB-5、N-03、DT-7。★ K-19）。

単価の変更と、変更履歴の記録を、1 つのトランザクションで行う。
途中で失敗したら、単価も履歴も元のまま残る。

使い方（backend フォルダで）:
    python -m scripts.change_price 4901234567894 160

同じことを SQL で行う場合:
    START TRANSACTION;
    INSERT INTO product_price_histories (product_id, old_unit_price, new_unit_price)
      SELECT id, unit_price, 160 FROM products WHERE product_code = '4901234567894';
    UPDATE products SET unit_price = 160 WHERE product_code = '4901234567894';
    COMMIT;
"""
from __future__ import annotations

import sys

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import LIMITS
from app.models import Product, ProductPriceHistory


def change_price(session: Session, product_code: str, new_unit_price: int) -> ProductPriceHistory:
    if type(new_unit_price) is not int or not (0 <= new_unit_price <= LIMITS.PRICE_MAX):
        raise ValueError(f"単価は 0〜{LIMITS.PRICE_MAX} の整数で指定してください")   # ★ K-33
    try:
        product = session.execute(select(Product).where(Product.product_code == product_code)).scalar_one_or_none()
        if product is None:
            raise LookupError(f"商品コード {product_code} は登録されていません")
        history = ProductPriceHistory(
            product_id=product.id, old_unit_price=product.unit_price, new_unit_price=new_unit_price
        )
        session.add(history)
        session.flush()
        product.unit_price = new_unit_price
        session.commit()
        return history
    except Exception:
        session.rollback()
        raise


if __name__ == "__main__":
    if len(sys.argv) != 3 or not sys.argv[2].isdigit():
        print("usage: python -m scripts.change_price <商品コード> <新しい単価>")
        sys.exit(1)
    from app.db import SessionLocal

    with SessionLocal() as s:
        h = change_price(s, sys.argv[1], int(sys.argv[2]))
        print(f"単価を {h.old_unit_price} 円から {h.new_unit_price} 円に変更しました。")
