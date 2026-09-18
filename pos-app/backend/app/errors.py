"""エラーコード（設計仕様書 11.2）と業務例外。"""
from __future__ import annotations

from typing import Any


class AppError(Exception):
    """サービス層で発生する業務エラー。ルータ層で {error:{code,message,details}} に変換する。"""

    status_code: int = 422
    code: str = "APP_ERROR"
    message: str = ""

    def __init__(self, message: str | None = None, details: dict[str, Any] | None = None):
        super().__init__(message or self.message)
        if message:
            self.message = message
        self.details = details or {}


class AuthInvalidCredentials(AppError):
    status_code = 401
    code = "AUTH_INVALID_CREDENTIALS"
    message = "担当者IDまたはパスワードが違います"


class AuthRequired(AppError):
    status_code = 401
    code = "AUTH_REQUIRED"
    message = "再度ログインしてください"


class ProductNotFound(AppError):
    status_code = 404
    code = "PRODUCT_NOT_FOUND"
    message = "商品がマスタ未登録です"


class MemberNotFound(AppError):
    status_code = 404
    code = "MEMBER_NOT_FOUND"
    message = "該当する会員が見つかりません"


class QuantityOutOfRange(AppError):
    status_code = 422
    code = "QUANTITY_OUT_OF_RANGE"
    message = "数量は 1〜99 で指定してください"


class CartEmpty(AppError):
    status_code = 422
    code = "CART_EMPTY"
    message = "商品が登録されていません"


class CartTooManyLines(AppError):
    status_code = 422
    code = "VALIDATION_ERROR"
    message = "商品の種類が上限を超えています"


class TaxRateNotConfigured(AppError):
    status_code = 422
    code = "TAX_RATE_NOT_CONFIGURED"
    message = "消費税率が設定されていません"


class PriceMismatch(AppError):
    status_code = 409
    code = "PRICE_MISMATCH"
    message = "金額が更新されました。内容を確認して再度購入してください"


def error_body(code: str, message: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"error": {"code": code, "message": message, "details": details or {}}}
