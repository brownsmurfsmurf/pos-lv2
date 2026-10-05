"""設定と制約値（設計仕様書 10 章）。

制約値の正本は shared/limits.json。Frontend と Backend の双方が読む。
"""
from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "production"   # 設定し忘れても安全側（Swagger 非表示）。開発時は .env で development にする
    # 手元で動かすときの接続先。DB_HOST が設定されていれば使わない
    database_url: str = "sqlite:///./pos.db"
    # 講座の形（D-012）。Azure Database for MySQL につなぐときはこの 6 つを設定する
    db_user: str | None = None
    db_password: str | None = None
    db_host: str | None = None
    db_port: int = 3306
    db_name: str | None = None
    ssl_ca_path: str | None = None
    jwt_secret: str = ""   # 既定値は持たない。.env で 32 文字以上を設定する
    cors_allow_origins: str = "http://localhost:3000"
    limits_path: str | None = None

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.cors_allow_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    if len(s.jwt_secret) < 32:
        raise RuntimeError("JWT_SECRET が設定されていないか、32 文字未満です。.env を確認してください。")
    if s.db_host and not (s.db_user and s.db_password and s.db_name):
        raise RuntimeError("DB_HOST を設定した場合は DB_USER / DB_PASSWORD / DB_NAME も必要です。")
    return s


def _find_limits_file() -> Path:
    candidates: list[Path] = []
    env_path = os.environ.get("LIMITS_PATH")
    if env_path:
        candidates.append(Path(env_path))
    here = Path(__file__).resolve()
    candidates.append(here.parents[2] / "shared" / "limits.json")   # pos-app/shared/limits.json
    candidates.append(here.parents[1] / "limits.json")              # backend/limits.json（単体デプロイ時の写し）
    for c in candidates:
        if c.is_file():
            return c
    raise FileNotFoundError("shared/limits.json が見つかりません。LIMITS_PATH を設定してください。")


class Limits:
    """shared/limits.json を属性でアクセスできるようにしたもの。"""

    def __init__(self, data: dict):
        self.QTY_MIN: int = data["QTY_MIN"]
        self.QTY_MAX: int = data["QTY_MAX"]
        self.CART_MAX_LINES: int = data["CART_MAX_LINES"]
        self.PRODUCT_CODE_MAX: int = data["PRODUCT_CODE_MAX"]
        self.MEMBER_CODE_MAX: int = data["MEMBER_CODE_MAX"]
        self.LOGIN_ID_MAX: int = data["LOGIN_ID_MAX"]
        self.PASSWORD_MIN: int = data["PASSWORD_MIN"]
        self.PASSWORD_MAX: int = data["PASSWORD_MAX"]
        self.PRICE_MAX: int = data["PRICE_MAX"]
        self.TAX_ROUNDING: str = data["TAX_ROUNDING"]
        self.DISCOUNT_ROUNDING: str = data["DISCOUNT_ROUNDING"]
        self.DISCOUNT_SELECTION: str = data["DISCOUNT_SELECTION"]
        self.JWT_TTL_HOURS: int = data["JWT_TTL_HOURS"]
        self.SCAN_DEBOUNCE_MS: int = data["SCAN_DEBOUNCE_MS"]
        self.BODY_MAX_BYTES: int = data["BODY_MAX_BYTES"]
        self.BUSINESS_TIMEZONE: str = data["BUSINESS_TIMEZONE"]


@lru_cache
def get_limits() -> Limits:
    with _find_limits_file().open(encoding="utf-8") as f:
        return Limits(json.load(f))


LIMITS = get_limits()
