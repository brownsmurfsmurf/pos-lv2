"""DB につなぐ所（設計仕様書 v2 の 1 章・4 章 DB-2、決定ログ D-012）。

ここで確かめること:
  1. パスワードを文字列にそのままはめ込んでいないか（@ や & が入っていても壊れないか）
  2. Azure の MySQL に暗号化（SSL）でつないでいるか
  3. 接続を使い回しているか（N-06）。日時を UTC で扱う設定になっているか（DB-2）
"""
from __future__ import annotations

import ssl
from collections.abc import Iterator

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import Settings, get_settings


class Base(DeclarativeBase):
    pass


def build_database_url(settings: Settings) -> URL:
    """接続先を組み立てる。

    講座の形（DB_USER / DB_PASSWORD / DB_HOST / DB_PORT / DB_NAME）が設定されていれば、それを使う。
    URL.create は、パスワードに含まれる記号（@ & : / など）を自動で安全な形に変換する。
    f"mysql+pymysql://{user}:{password}@{host}/..." のように文字列へ直接はめ込むと、
    パスワードの中の @ が「ここからホスト名」という区切りとして解釈され、接続に失敗する。
    """
    if settings.db_host:
        return URL.create(
            drivername="mysql+pymysql",
            username=settings.db_user,
            password=settings.db_password,   # 生のパスワードをそのまま渡す。変換は URL.create が行う
            host=settings.db_host,
            port=settings.db_port,
            database=settings.db_name,
            query={"charset": "utf8mb4"},
        )
    # DB_HOST がなければ、手元で動かすための接続先（既定は SQLite）を使う
    return make_url(settings.database_url)


def make_engine(url: URL | str, ssl_ca_path: str | None = None):
    url = make_url(url)
    backend = url.get_backend_name()
    kwargs: dict = {"pool_pre_ping": True}

    if backend == "sqlite":
        from sqlalchemy.pool import StaticPool

        kwargs["connect_args"] = {"check_same_thread": False}
        if url.database in (None, "", ":memory:"):
            kwargs["poolclass"] = StaticPool
    else:
        # N-06: 接続プール。起動時に作った接続を要求ごとに使い回す
        kwargs.update(pool_size=5, max_overflow=5, pool_recycle=1800)
        # Azure Database for MySQL は SSL 接続が必須
        # 証明書ファイルの指定があればそれで、なければ OS が持つ証明書で、サーバの証明書を検証する
        context = ssl.create_default_context(cafile=ssl_ca_path) if ssl_ca_path else ssl.create_default_context()
        kwargs["connect_args"] = {"ssl": context}

    engine = create_engine(url, **kwargs)

    if backend == "mysql":
        @event.listens_for(engine, "connect")
        def _set_utc(dbapi_conn, _record):  # pragma: no cover - MySQL 接続時のみ
            # DB-2: セッションの時間帯を UTC に固定する
            cur = dbapi_conn.cursor()
            cur.execute("SET time_zone = '+00:00'")
            cur.close()
    return engine


_settings = get_settings()
engine = make_engine(build_database_url(_settings), _settings.ssl_ca_path)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_session() -> Iterator[Session]:
    """FastAPI の依存関係。1 回の要求で 1 つのセッションを使う。"""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def ping(session: Session) -> None:
    session.execute(text("SELECT 1"))
