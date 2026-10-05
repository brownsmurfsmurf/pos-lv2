# pos-app — Lv2 簡易POSアプリ

`ai-driven/設計仕様書_v2.md` をもとにしたコードです。根拠は、要件定義書 v2（FR / N / DT / P）、決定ログ（D-000〜D-012）、課題の指定項目の 3 つです。
要求にない機能（ログアウト、管理画面、支払い方法、レシートなど）は作っていません。

```
pos-app/
├─ shared/limits.json      仮の値（★）を 1 か所にまとめたもの。サーバと画面の両方が読む
├─ backend/                pos-api（FastAPI + SQLAlchemy）
│   ├─ app/
│   │   ├─ db.py               DB につなぐ所（接続先の組み立て、SSL、接続の使い回し）
│   │   ├─ config.py           設定値（.env から読む）
│   │   ├─ clock.py            取引日を作る所（UTC → 日本時間）
│   │   ├─ services/pricing_service.py   金額の計算（値引き・税・合計）
│   │   ├─ services/transaction_service.py  照合と保存
│   │   ├─ routers/            API-01〜07
│   │   ├─ models.py           9 テーブル
│   │   └─ schemas.py, security.py, errors.py, main.py
│   ├─ db/schema.sql           MySQL 用のテーブル定義
│   ├─ scripts/                seed（初期データ）、change_price（単価の変更）、hash_password、check_db
│   └─ tests/                  test_unit.py（UT-B-01〜41）、test_api.py（結合）、test_db_url.py
└─ frontend/               pos-web（Next.js）
    ├─ src/app/api/            BFF（画面とサーバの中継）
    ├─ src/app/login, pos      ログイン画面、POS 画面
    ├─ src/components/         画面の部品
    ├─ src/features/cart/      購入リストの状態
    ├─ src/features/scanner/   カメラとバーコード
    └─ __tests__/              UT-F-01〜31、BFF の結合テスト
```

## 手元で動かす

ターミナルを 2 つ使います（PowerShell）。

**1 つ目: サーバ**

```powershell
cd pos-app\backend
python -m venv .venv
.venv\Scripts\pip install -r requirements-dev.txt
Copy-Item .env.example .env
.venv\Scripts\python -m scripts.seed --reset
.venv\Scripts\python -m uvicorn app.main:app --port 8000
```

`.env` は、手元で試すだけなら `APP_ENV=development` と `JWT_SECRET`（32 文字以上）があれば動きます。DB は手元の `pos.db`（SQLite）を使います。

**2 つ目: 画面**

```powershell
cd pos-app\frontend
npm install
npm run dev
```

ブラウザで http://localhost:3000 を開き、ログインします。

## 初期データ（学習用）

`scripts/seed.py` が入れるデータです。テスト仕様書 v2 の E-1〜E-3 をそのまま試せます。

| 種類 | 値 |
|---|---|
| 担当者 | `staff01` / `pos-staff-01`、`staff02` / `pos-staff-02` |
| 商品 A | `4901234567894` 緑茶 500ml 150 円。会員は 20% 引き（期間内） |
| 商品 B | `4901234567900` 食パン 6枚切 188 円。値引きなし |
| 商品 C | `4901234567917` 牛乳 1L 240 円。20% 引きだが終了日は昨日 |
| 商品 D | `4901234567924` 卵 10個 270 円。会員は 20 円引き（期間内） |
| 会員 | `M0001`、`M0002` |
| 税率 | 10% |

担当者のパスワードはこの README に公開されている学習用の値です。共用・本番の DB には入れないでください。
`DB_HOST` を設定した状態では、`--allow-remote` を付けない限り seed は実行されません。

## Azure Database for MySQL につなぐ

`backend/.env` に、講座の教材と同じ 6 つの設定値を入れます（決定ログ D-012）。

| 設定値 | 入れるもの |
|---|---|
| `DB_USER` | ユーザー名 |
| `DB_PASSWORD` | パスワード。**そのまま**書く。`@` や `&` が入っていても変換しない |
| `DB_HOST` | サーバー名（`xxxx.mysql.database.azure.com`） |
| `DB_PORT` | 3306 |
| `DB_NAME` | データベース名 |
| `SSL_CA_PATH` | 証明書ファイル（.pem）の場所。空なら OS が持つ証明書で検証する |

パスワードの記号は、`app/db.py` の `build_database_url` が安全な形に変換します。
教材のように `f"mysql+pymysql://{user}:{password}@{host}..."` と文字列へ直接はめ込むと、パスワードの中の `@` が区切りとして解釈され、接続に失敗します。

つながるかどうかは、次で確かめられます。届かない場合は、理由（名前、IP の許可、ユーザー・パスワード、データベース名、SSL）を切り分けて表示します。

```powershell
.venv\Scripts\python -m scripts.check_db
```

テーブルは `db/schema.sql` を、使うデータベースを選んだうえで実行して作ります。

## 設定の変更（管理画面は作らない。設計仕様書 v2 の DB-5）

| 変えるもの | 方法 |
|---|---|
| 税率 | `UPDATE tax_rates SET rate = 8.00;` |
| 値引き | `INSERT INTO discounts (product_id, start_date, end_date, discount_type, discount_value) VALUES (...)`。日付は日本時間の暦日 |
| 商品の単価 | `python -m scripts.change_price <商品コード> <新しい単価>`。変更履歴も同時に残る |
| 担当者のパスワード | `python -m scripts.hash_password` でハッシュを作り、SQL で入れる。8〜64 文字 |

## テスト

```powershell
cd pos-app\backend
.venv\Scripts\python -m pytest
```

```powershell
cd pos-app\frontend
npm test
```

テストの番号は `ai-driven/テスト仕様書_v2.md` と同じです（UT-B-01〜41、UT-F-01〜31、IT-xx）。

## Azure に載せるとき（設計仕様書 v2 の 1 章）

- pos-web、pos-api とも App Service（Basic 以上、Always On を有効）
- pos-api の設定: `APP_ENV=production`、`JWT_SECRET`、`DB_USER` など 6 つ、`CORS_ALLOW_ORIGINS=https://<pos-web のホスト>`
- pos-web の設定: `API_UPSTREAM_URL=https://<pos-api のホスト>`、`NODE_ENV=production`
- 稼働確認のパス: `/api/v1/health`
