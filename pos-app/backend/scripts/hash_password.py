"""担当者のパスワードを bcrypt でハッシュ化して表示する（設計仕様書 v2 の DB-5。★ K-17）。

    python -m scripts.hash_password

パスワードは画面から入力する（コマンドの履歴に残さないため）。8〜64 文字でなければ受け付けない。
表示されたハッシュを、SQL で staff.password_hash に入れる。
"""
import getpass
import sys

from app.config import LIMITS
from app.security import hash_password


def validate(password: str) -> None:
    if not (LIMITS.PASSWORD_MIN <= len(password) <= LIMITS.PASSWORD_MAX):
        raise ValueError(f"パスワードは {LIMITS.PASSWORD_MIN}〜{LIMITS.PASSWORD_MAX} 文字で指定してください")


if __name__ == "__main__":
    pw = getpass.getpass("新しいパスワード: ")
    try:
        validate(pw)
    except ValueError as e:
        print(e)
        sys.exit(1)
    print(hash_password(pw))
