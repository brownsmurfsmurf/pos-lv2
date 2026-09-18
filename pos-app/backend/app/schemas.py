"""Pydantic スキーマ（設計仕様書 7.3 の TypeScript 型と 1 対 1）。

型・形式の検証はここで行い 400 VALIDATION_ERROR。業務範囲（数量 1〜99 など）はサービス層で 422。
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt, field_validator

from .config import LIMITS

PRODUCT_CODE_PATTERN = rf"^[0-9]{{1,{LIMITS.PRODUCT_CODE_MAX}}}$"
MEMBER_CODE_PATTERN = rf"^[A-Za-z0-9]{{1,{LIMITS.MEMBER_CODE_MAX}}}$"


class StaffInfo(BaseModel):
    id: int
    login_id: str
    name: str


class ProductInfo(BaseModel):
    id: int
    product_code: str
    name: str
    unit_price: int


class MemberInfo(BaseModel):
    """氏名のみ（表示に必要な範囲。住所等は返さない）。"""

    id: int
    member_code: str
    name: str


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    login_id: str = Field(min_length=1, max_length=LIMITS.LOGIN_ID_MAX)
    password: str = Field(min_length=1, max_length=LIMITS.PASSWORD_MAX)


class LoginResponse(BaseModel):
    access_token: str
    token_type: Literal["Bearer"] = "Bearer"
    expires_in: int
    staff: StaffInfo


class QuoteItemRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    product_code: str = Field(pattern=PRODUCT_CODE_PATTERN)
    quantity: StrictInt  # "2" や 1.5 は 400。範囲（1〜99）はサービス層で 422


class AppliedDiscount(BaseModel):
    discount_id: int
    type: Literal["percent", "amount"]
    value: float
    amount: int


class QuoteLine(BaseModel):
    product_code: str
    product_name: str
    unit_price: int
    quantity: int
    discount: AppliedDiscount | None
    line_total: int


class QuoteResult(BaseModel):
    tax_rate: float
    lines: list[QuoteLine]
    subtotal_excl_tax: int
    tax_amount: int
    total_incl_tax: int


def _no_duplicate_codes(items):
    codes = [i.product_code for i in items]
    if len(codes) != len(set(codes)):
        raise ValueError("product_code が重複しています")
    return items


class QuoteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    member_code: str | None = Field(default=None, pattern=MEMBER_CODE_PATTERN)
    items: list[QuoteItemRequest]

    @field_validator("items")
    @classmethod
    def _dup(cls, v):
        return _no_duplicate_codes(v)


class CommitItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    product_code: str = Field(pattern=PRODUCT_CODE_PATTERN)
    quantity: StrictInt
    unit_price: StrictInt
    discount_amount: StrictInt
    line_total: StrictInt


class CommitRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    member_code: str | None = Field(default=None, pattern=MEMBER_CODE_PATTERN)
    items: list[CommitItem]
    tax_rate: float
    subtotal_excl_tax: StrictInt
    tax_amount: StrictInt
    total_incl_tax: StrictInt

    @field_validator("items")
    @classmethod
    def _dup(cls, v):
        return _no_duplicate_codes(v)


class CommitResponse(BaseModel):
    transaction_id: int
    transacted_at: str  # ISO 8601 (UTC)
    subtotal_excl_tax: int
    tax_amount: int
    total_incl_tax: int


class HealthResponse(BaseModel):
    status: Literal["ok", "error"]
    db: Literal["ok", "error"]
