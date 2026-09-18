"""DB 接続と UnitOfWork（設計仕様書 9 章、DB-4、N-04）。

- 接続プールを使い、要求ごとに接続を作り直さない（N-04）
- MySQL ではセッションの time_zone を +00:00 に固定し、日時は UTC で保存する（DB-4）
"""
from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import get_settings


class Base(DeclarativeBase):
    pass


def make_engine(url: str):
    kwargs: dict = {"pool_pre_ping": True}
    if url.startswith("sqlite"):
        from sqlalchemy.pool import StaticPool

        kwargs.update(connect_args={"check_same_thread": False})
        if ":memory:" in url or url.endswith("sqlite://"):
            kwargs.update(poolclass=StaticPool)
    else:
        kwargs.update(pool_size=5, max_overflow=5, pool_recycle=1800)
    engine = create_engine(url, **kwargs)

    if url.startswith("mysql"):
        @event.listens_for(engine, "connect")
        def _set_utc(dbapi_conn, _record):  # pragma: no cover - MySQL 接続時のみ
            cur = dbapi_conn.cursor()
            cur.execute("SET time_zone = '+00:00'")
            cur.close()
    return engine


engine = make_engine(get_settings().database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_session() -> Iterator[Session]:
    """FastAPI 依存関係。1 要求 = 1 セッション（UnitOfWork）。"""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def ping(session: Session) -> None:
    session.execute(text("SELECT 1"))
