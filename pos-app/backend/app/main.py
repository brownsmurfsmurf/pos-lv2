"""FastAPI アプリ本体（設計仕様書 2 章、11.3 例外の変換、12 章 SEC-04/06/07）。"""
from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import OperationalError

from .config import LIMITS, get_settings
from .errors import AppError, error_body
from .routers import auth, health, members, pricing, products, transactions

logger = logging.getLogger("pos-api")
settings = get_settings()

# SEC-06: 本番では Swagger / ReDoc / OpenAPI を無効化
docs_kwargs = {} if settings.is_development else {"docs_url": None, "redoc_url": None, "openapi_url": None}
app = FastAPI(title="pos-api", version="1.0.0", **docs_kwargs)

# SEC-04: CORS は Next.js のオリジンのみ。メソッド・ヘッダも限定
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.middleware("http")
async def limit_body_size(request: Request, call_next):
    """SEC-07: 要求本文の上限（BODY_MAX_BYTES）。"""
    length = request.headers.get("content-length")
    if length and length.isdigit() and int(length) > LIMITS.BODY_MAX_BYTES:
        return JSONResponse(status_code=400, content=error_body("VALIDATION_ERROR", "入力内容に誤りがあります",
                                                                 {"reason": "body too large"}))
    return await call_next(request)


# ---- 11.3 例外の変換 ----

@app.exception_handler(AppError)
async def app_error_handler(_: Request, exc: AppError):
    return JSONResponse(status_code=exc.status_code, content=error_body(exc.code, exc.message, exc.details))


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_: Request, exc: RequestValidationError):
    # 型・形式の不正は 400。フィールド名と理由のみ返し、入力値そのものは返さない
    details = {"fields": [{"loc": [str(x) for x in e.get("loc", [])], "type": e.get("type")} for e in exc.errors()]}
    return JSONResponse(status_code=400, content=error_body("VALIDATION_ERROR", "入力内容に誤りがあります", details))


@app.exception_handler(OperationalError)
async def db_error_handler(_: Request, exc: OperationalError):
    logger.error("database unavailable: %s", exc)
    return JSONResponse(status_code=503, content=error_body("SERVICE_UNAVAILABLE", "サービスに接続できません"))


@app.exception_handler(Exception)
async def unexpected_error_handler(_: Request, exc: Exception):
    logger.exception("unexpected error")   # ERR-4: 詳細はログのみ
    return JSONResponse(status_code=500, content=error_body("INTERNAL_ERROR", "処理に失敗しました。もう一度お試しください"))


# ---- ルータ（/api/v1） ----
API_PREFIX = "/api/v1"
for r in (auth.router, products.router, members.router, pricing.router, transactions.router, health.router):
    app.include_router(r, prefix=API_PREFIX)
