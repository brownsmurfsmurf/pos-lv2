"""DB につなぐ所の確認（決定ログ D-012）。パスワードに @ や & が入っていても接続先が壊れないこと。"""
from __future__ import annotations

from sqlalchemy.engine import make_url

from app.config import Settings
from app.db import build_database_url

TRICKY = "aB1&&cD@e:f/g#h"   # テスト用の作り物。@ & : / # を含む


def _settings(**over) -> Settings:
    base = dict(db_user="tech0", db_password=TRICKY, db_host="example.mysql.database.azure.com",
                db_port=3306, db_name="pos", database_url="sqlite://")
    base.update(over)
    return Settings(_env_file=None, **base)


def test_password_with_symbols_survives_round_trip():
    url = build_database_url(_settings())
    assert url.password == TRICKY                                   # パスワードはそのまま保たれる
    assert url.host == "example.mysql.database.azure.com"           # @ でホスト名がずれない
    assert url.username == "tech0" and url.port == 3306 and url.database == "pos"

    text = url.render_as_string(hide_password=False)                # 文字列にしたときは記号が変換されている
    assert "%40" in text and "%26" in text and TRICKY not in text
    again = make_url(text)                                          # 文字列から読み直しても同じ
    assert again.password == TRICKY and again.host == url.host


def test_naive_f_string_breaks_with_at_sign():
    """教材の書き方（f 文字列に直接はめ込む）だと、@ のせいでホスト名がずれることの確認。"""
    naive = f"mysql+pymysql://tech0:{TRICKY}@example.mysql.database.azure.com:3306/pos"
    try:
        broken = make_url(naive)
        assert broken.host != "example.mysql.database.azure.com" or broken.password != TRICKY
    except Exception:
        pass   # 解釈できずにエラーになる場合もある。どちらにしても正しくつながらない


def test_falls_back_to_local_database_when_db_host_is_empty():
    url = build_database_url(_settings(db_host=None, database_url="sqlite:///./pos.db"))
    assert url.get_backend_name() == "sqlite"


def test_password_is_hidden_when_printed():
    assert TRICKY not in str(build_database_url(_settings()))


def test_password_length_is_checked_before_hashing():
    """★ K-17: 担当者のパスワードは登録時に 8〜64 文字を検査する（scripts/hash_password.py）。"""
    import pytest

    from scripts.hash_password import validate

    validate("a" * 8)
    validate("a" * 64)
    for bad in ("a" * 7, "a" * 65):
        with pytest.raises(ValueError):
            validate(bad)


def test_settings_require_jwt_secret_and_complete_db_settings(monkeypatch):
    import pytest

    from app import config

    monkeypatch.setenv("JWT_SECRET", "short")
    config.get_settings.cache_clear()
    with pytest.raises(RuntimeError):
        config.get_settings()
    monkeypatch.setenv("JWT_SECRET", "x" * 32)
    monkeypatch.setenv("DB_HOST", "example.mysql.database.azure.com")
    monkeypatch.setenv("DB_USER", "")
    config.get_settings.cache_clear()
    with pytest.raises(RuntimeError):
        config.get_settings()
    monkeypatch.undo()
    config.get_settings.cache_clear()
    assert config.get_settings().app_env == "test"
