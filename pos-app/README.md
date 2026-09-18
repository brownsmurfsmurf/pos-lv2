# pos-app — Lv2 簡易POSアプリ（要求忠実版の実装）

`Lv2_簡易POSアプリ_設計仕様書_要求忠実版.md` をコンテキストにして生成したコードです。
要件番号（FR / SC / D / N / Q）、API 番号（API-01〜07）、テストケース番号（UT / IT）はコード中のコメントで仕様書と対応させています。

```
pos-app/
├─ shared/limits.json      制約値の正本（設計仕様書 10 章）。Frontend・Backend の双方が読む
├─ backend/                pos-api（FastAPI + SQLAlchemy）
│   ├─ app/
│   │   ├─ main.py         アプリ本体。CORS・Swagger 非表示・例外変換（11.3、SEC-04/06）
│   │   ├─ config.py       環境変数と limits.json
│   │   ├─ clock.py        Clock（UTC 現在時刻）と取引日（JST）の生成（6.1）
│   │   ├─ db.py           接続プール・UnitOfWork（N-04、DB-4）
│   │   ├─ models.py       8 テーブル（6.3）
│   │   ├─ schemas.py      Pydantic（7.3 の TypeScript 型と 1 対 1）
│   │   ├─ security.py     bcrypt・JWT（SEC-01〜03）
│   │   ├─ errors.py       エラーコード（11.2）
│   │   ├─ services/       AuthService / PricingService（金額計算の正本）/ TransactionService（照合・保存）
│   │   └─ routers/        API-01〜07
│   ├─ db/schema.sql       MySQL 用 DDL
│   ├─ scripts/seed.py     テーブル作成と初期データ（税率・値引きは SQL／シードで投入。6.4）
│   └─ tests/              pytest（UT-B-01〜55、IT-01〜32 の API 側）
└─ frontend/               pos-web（Next.js 16 / React 19 / Zod 4 / @zxing/library）
    ├─ src/app/api/**      BFF Route Handler（7.5）。Cookie ⇄ Bearer、Zod 400、5xx 正規化
    ├─ src/app/login, pos  SC-01、SC-02
    ├─ src/components/     SC-02 の部品（5.1）
    ├─ src/features/cart/  状態管理（5.2）
    ├─ src/features/scanner/ カメラとバーコード復号（SC-02-07）
    ├─ src/lib/            types / schemas / errors / apiClient / bff / pricing / limits
    └─ __tests__/          Jest（UT-F-01〜35、BFF の IT）
```

## 動かし方（ローカル）

### 1. Backend

```bash
cd pos-app/backend
python -m venv .venv
.venv/Scripts/pip install -r requirements-dev.txt      # macOS/Linux は .venv/bin/pip
copy .env.example .env                                  # DATABASE_URL / JWT_SECRET を設定
.venv/Scripts/python -m scripts.seed                    # テーブル作成 + 初期データ
.venv/Scripts/python -m uvicorn app.main:app --reload --port 8000
```

- `.env.example` は SQLite（`sqlite:///./pos.db`）で動く設定です。MySQL は `DATABASE_URL=mysql+pymysql://user:pass@host:3306/pos?charset=utf8mb4`
- `APP_ENV=development` のときだけ http://localhost:8000/docs が開きます（SEC-06）
- テスト: `.venv/Scripts/python -m pytest --cov=app`

### 2. Frontend

```bash
cd pos-app/frontend
npm install
copy .env.example .env.local                            # API_UPSTREAM_URL=http://localhost:8000
npm run dev                                             # http://localhost:3000 → /login
```

- テスト: `npm test` / カバレッジ: `npm run test:coverage`（Stmts・Lines 80%、Branches 70%、Funcs 90%）
- 型チェック: `npm run typecheck`
- `shared/limits.json` は `npm run dev` などの前に `src/lib/limits.json` へ自動で写されます

### 3. 初期データ（scripts/seed.py）

| 種別 | 値 |
|---|---|
| 担当者 | `staff01` / `pos-staff-01`、`staff02` / `pos-staff-02` |
| 商品 A（20% 引き・期間内） | `4901234567894` 緑茶 500ml 150円 |
| 商品 B（値引きなし） | `4901234567900` 食パン 6枚切 188円 |
| 商品 C（値引きの終了日が昨日） | `4901234567917` 牛乳 1L 240円 |
| 商品 D（20 円引き・期間内） | `4901234567924` 卵 10個 270円 |
| 商品 E | `4901234567931` ヨーグルト 400g 160円 |
| 会員 | `M0001` 山田 太郎、`M0002` 高橋 美咲 |
| 税率 | 10.00% |

税率・値引きの変更は SQL で行います（設計仕様書 6.4、Q-9）。例:

```sql
UPDATE tax_rates SET rate = 8.00 WHERE id = 1;
INSERT INTO discounts (product_id, start_date, end_date, discount_type, discount_value)
VALUES (2, '2026-10-01', '2026-10-31', 'amount', 20.00);
```

## 仕様書の「★（仮置き）」をコードでどう扱ったか

| 事項 | 実装 | 確認事項 |
|---|---|---|
| 端数は 1 円未満切り捨て、値引きは額が最大の 1 件 | `PricingService.discount_amount_for` / `applicable_discount` / `calc_totals` | Q-6〜Q-8 |
| 値引き額が行の金額を超える場合 | 行の金額を上限（小計を負にしない） | Q-7 |
| 数量 99 超 | 変更せず「数量は 1〜99 で指定してください」を表示 | Q-2 |
| 空の購入リストで購入 | 422 CART_EMPTY。購入ボタン自体も無効 | Q-4 |
| スキャンした商品 | 追加ボタンなしで購入リストへ（手入力は名称・単価を表示して追加ボタン） | Q-5 |
| 数量の変え方 | 直接入力と ± ボタンの両方 | Q-1 |
| 存在しない会員ID | 文言を表示し会員は未設定のまま | Q-3 |
| パスワード | bcrypt でハッシュ化。ログイン要求は最大 64 文字のみ検証 | Q-11 |
| 商品コード・会員ID | 13 桁の数字 / 32 文字の英数字 | Q-21 |
| 設定変更 | SQL で直接 | Q-9, Q-10 |

## 取引日（JST）の生成（講師指摘への対応）

- `app/clock.py` の `Clock` が UTC 現在時刻を返し、`business_date_of()` が `Asia/Tokyo` の日付に変換します
- `PricingService.new_context()` が取引時刻と取引日を **1 回だけ**取得し、API-06 は値引き判定と保存に同じ値を使います
- `date.today()`・SQL の `CURDATE()`・ブラウザの時計は使いません。MySQL 接続はセッションで `time_zone='+00:00'` を明示します
- 境界のテスト: `tests/test_pricing_service.py`（UT-B-30/31: UTC 14:59:59 → 適用、15:00:00 → 非適用）、`tests/test_api.py::test_it_16_jst_boundary_via_api`

## Azure への配置（設計仕様書 2 章）

- pos-web、pos-api とも **App Service（Basic 以上、Always On 有効）**。Functions（従量課金）は使わない（N-03、N-04）
- pos-api のアプリケーション設定: `APP_ENV=production`、`DATABASE_URL`、`JWT_SECRET`、`CORS_ALLOW_ORIGINS=https://<pos-web のホスト>`
- pos-web のアプリケーション設定: `API_UPSTREAM_URL=https://<pos-api のホスト>`、`NODE_ENV=production`（Cookie に Secure が付く）
- DB は Azure Database for MySQL Flexible Server。`backend/db/schema.sql` で作成し、`scripts/seed.py` か SQL で初期データを投入
- ヘルスチェックのパス: `/api/v1/health`
