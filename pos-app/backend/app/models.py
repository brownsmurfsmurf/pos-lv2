"""ORM モデル（設計仕様書 6.3 の 8 テーブルと 1 対 1）。"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger, CheckConstraint, Date, DateTime, ForeignKey, Integer, Numeric, String,
    UniqueConstraint, func,
)
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base

# DB-2: 代理キー BIGINT UNSIGNED AUTO_INCREMENT。SQLite（テスト）では INTEGER。
PK = BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql").with_variant(Integer, "sqlite")
FK = BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql").with_variant(Integer, "sqlite")
# DB-5: コード類は utf8mb4_bin
CODE = String(32).with_variant(mysql.VARCHAR(32, collation="utf8mb4_bin"), "mysql")
CODE13 = String(13).with_variant(mysql.VARCHAR(13, collation="utf8mb4_bin"), "mysql")


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(6), nullable=False, server_default=func.now())


class MasterMixin(TimestampMixin):
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(6), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class Staff(MasterMixin, Base):
    __tablename__ = "staff"
    id: Mapped[int] = mapped_column(PK, primary_key=True, autoincrement=True)
    login_id: Mapped[str] = mapped_column(CODE, nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(60), nullable=False)
    name: Mapped[str] = mapped_column(String(50), nullable=False)


class Product(MasterMixin, Base):
    __tablename__ = "products"
    id: Mapped[int] = mapped_column(PK, primary_key=True, autoincrement=True)
    product_code: Mapped[str] = mapped_column(CODE13, nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    unit_price: Mapped[int] = mapped_column(Integer, nullable=False)  # ★ 税抜


class Member(MasterMixin, Base):
    __tablename__ = "members"
    id: Mapped[int] = mapped_column(PK, primary_key=True, autoincrement=True)
    member_code: Mapped[str] = mapped_column(CODE, nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20))
    address: Mapped[str | None] = mapped_column(String(200))
    gender: Mapped[str | None] = mapped_column(String(10))
    age: Mapped[int | None] = mapped_column(Integer)


class TaxRate(MasterMixin, Base):
    __tablename__ = "tax_rates"
    id: Mapped[int] = mapped_column(PK, primary_key=True, autoincrement=True)
    rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)


class Discount(MasterMixin, Base):
    __tablename__ = "discounts"
    __table_args__ = (CheckConstraint("end_date >= start_date", name="ck_discounts_period"),)
    id: Mapped[int] = mapped_column(PK, primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(FK, ForeignKey("products.id", ondelete="RESTRICT"), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    discount_type: Mapped[str] = mapped_column(String(10), nullable=False)  # percent / amount
    discount_value: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    product: Mapped[Product] = relationship()


class Transaction(TimestampMixin, Base):
    __tablename__ = "transactions"
    id: Mapped[int] = mapped_column(PK, primary_key=True, autoincrement=True)
    transacted_at: Mapped[datetime] = mapped_column(DateTime(6), nullable=False)
    staff_id: Mapped[int] = mapped_column(FK, ForeignKey("staff.id", ondelete="RESTRICT"), nullable=False)
    member_id: Mapped[int | None] = mapped_column(FK, ForeignKey("members.id", ondelete="RESTRICT"))
    subtotal_excl_tax: Mapped[int] = mapped_column(Integer, nullable=False)
    tax_amount: Mapped[int] = mapped_column(Integer, nullable=False)
    total_incl_tax: Mapped[int] = mapped_column(Integer, nullable=False)

    items: Mapped[list["TransactionItem"]] = relationship(back_populates="transaction", cascade="all")


class TransactionItem(TimestampMixin, Base):
    __tablename__ = "transaction_items"
    __table_args__ = (
        UniqueConstraint("transaction_id", "line_no", name="uq_transaction_items_line"),
        CheckConstraint("quantity BETWEEN 1 AND 99", name="ck_transaction_items_quantity"),
    )
    id: Mapped[int] = mapped_column(PK, primary_key=True, autoincrement=True)
    transaction_id: Mapped[int] = mapped_column(FK, ForeignKey("transactions.id", ondelete="RESTRICT"), nullable=False)
    line_no: Mapped[int] = mapped_column(Integer, nullable=False)
    product_id: Mapped[int] = mapped_column(FK, ForeignKey("products.id", ondelete="RESTRICT"), nullable=False)
    unit_price: Mapped[int] = mapped_column(Integer, nullable=False)  # DB-6: 購入時点の単価の写し
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    discount_amount: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    line_total: Mapped[int] = mapped_column(Integer, nullable=False)

    transaction: Mapped[Transaction] = relationship(back_populates="items")
    applications: Mapped[list["DiscountApplication"]] = relationship(back_populates="item", cascade="all")


class DiscountApplication(TimestampMixin, Base):
    __tablename__ = "discount_applications"
    id: Mapped[int] = mapped_column(PK, primary_key=True, autoincrement=True)
    transaction_item_id: Mapped[int] = mapped_column(
        FK, ForeignKey("transaction_items.id", ondelete="RESTRICT"), nullable=False
    )
    discount_id: Mapped[int] = mapped_column(FK, ForeignKey("discounts.id", ondelete="RESTRICT"), nullable=False)
    applied_amount: Mapped[int] = mapped_column(Integer, nullable=False)

    item: Mapped[TransactionItem] = relationship(back_populates="applications")
