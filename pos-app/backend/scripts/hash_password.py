"""パスワードの bcrypt ハッシュを表示する（SQL で担当者を追加するとき用）。

    python -m scripts.hash_password "新しいパスワード"
"""
import sys

from app.security import hash_password

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: python -m scripts.hash_password <password>")
        sys.exit(1)
    print(hash_password(sys.argv[1]))
