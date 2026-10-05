"""DB につながるかを確かめ、つながらない場合は理由を切り分ける。

使い方（backend フォルダで、.env に DB_USER などを入れた後）:
    python -m scripts.check_db

パスワードは画面に表示しない。.env から読むだけ。
"""
from __future__ import annotations

import socket
import sys

from sqlalchemy import text

from app.config import get_settings
from app.db import build_database_url, make_engine


def main() -> int:
    s = get_settings()
    url = build_database_url(s)
    print("接続先:", url.render_as_string(hide_password=True))

    if url.get_backend_name() != "mysql":
        print("DB_HOST が設定されていないので、手元の DB（SQLite）を使います。")
    else:
        # 1. サーバーまで届くか（パスワードは使わない）
        try:
            ip = socket.gethostbyname(url.host)
            print(f"1. サーバーの名前を引けた: {ip}")
        except OSError as e:
            print(f"1. サーバーの名前を引けない: {e}\n   → DB_HOST のつづりを確かめてください。")
            return 1
        sock = socket.socket()
        sock.settimeout(8)
        try:
            sock.connect((ip, url.port or 3306))
            print("2. ポートに届いた")
        except OSError as e:
            print(f"2. ポートに届かない: {type(e).__name__}\n"
                  "   → 接続元の IP アドレスが許可されていない可能性が高いです。運営に確認してください。")
            return 2
        finally:
            sock.close()

    # 3. ログインして 1 行読む
    try:
        engine = make_engine(url, s.ssl_ca_path)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("3. ログインできた。DB につながります。")
        return 0
    except Exception as e:  # noqa: BLE001
        msg = str(getattr(e, "orig", e))
        print("3. ログインできない:", msg[:200])
        if "1045" in msg or "Access denied" in msg:
            print("   → ユーザー名かパスワードが違います。.env の DB_USER / DB_PASSWORD を確かめてください。\n"
                  "     パスワードは変換せず、そのまま書きます。")
        elif "1049" in msg or "Unknown database" in msg:
            print("   → DB_NAME のデータベースがありません。名前を運営に確認してください。")
        elif "SSL" in msg.upper() or "certificate" in msg.lower():
            print("   → 暗号化通信の設定の問題です。SSL_CA_PATH を空にするか、正しい証明書ファイルを指定してください。")
        return 3


if __name__ == "__main__":
    sys.exit(main())
