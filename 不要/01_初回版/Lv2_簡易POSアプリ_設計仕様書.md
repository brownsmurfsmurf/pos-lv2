# 設計仕様書: 簡易POSアプリ（Lv1 + Lv2）

> 本書は「Lv2_簡易POSアプリ_要件定義書」（以下、要件定義書）を入力とし、実装に必要な
> 設計を定めたものである。要件定義書の識別子（FR / SC / D / DR / N / P / A）はそのまま参照する。

---

## 1. はじめに

### 1.1 目的

本書は、要件定義書（`Lv2_簡易POSアプリ_要件定義書.md` v1.2）が定めた「何を作るか」を、
「どう作るか」に落とし込む。実装者が本書と要件定義書だけを見てコードを書き始められる状態を目標とする。

### 1.2 入力と位置づけ

| 項目 | 内容 |
|---|---|
| 入力 | 要件定義書（FR-01〜FR-10、SC-01〜SC-06、D-01〜D-09、DR-1〜DR-5、N-01〜N-10、P-1〜P-5、A-1〜A-6、I-1〜I-8、Q-1〜Q-8） |
| 出力 | 本書（設計仕様書）、および図 12 枚（PNG。Mermaid ソースは付録 A） |
| 読者 | 課題の評価者、および本システムの実装者 |
| 範囲 | データベースの物理設計、API の入出力、画面のコンポーネントと状態、クラス構成、設定値、エラー処理、セキュリティ対策、インフラ配置。**ソースコードそのものは含まない** |
| 方針 | 要件定義書の識別子をそのまま参照し、すべての設計要素がどの要件に由来するかを辿れるようにする（13 章）。要件定義書で「仮定」としたもの（Q-1〜Q-8）は本書で設定値として確定する（10.2） |

### 1.3 識別子

要件定義書の識別子に加え、本書で次を新設する。

| 接頭辞 | 意味 | 章 |
|---|---|---|
| UC-nn | ユースケース | 3 |
| DB-n | データベースの共通規約 | 6.2 |
| API-nn / API-Pn | API とその方針 | 7 |
| BFF-n | BFF の責務 | 7.6 |
| SEC-nn | セキュリティ対策 | 12 |
| ERR-n | エラー処理の方針 | 11 |
| 大文字スネークケース（例 `QTY_MAX`） | 設定・制約値の定数 | 10 |
| U-n | 本書の未確定事項 | 14 |

### 1.4 図について

図はすべて Mermaid 記法から Mermaid CLI（ローカルの Chrome を用いて描画）で PNG を生成した。
ソースは付録 A に収め、修正時は付録 A を編集して再生成する。PNG を直接編集しない。

### 1.5 読む順序

実装に着手する場合は、2 章（構成）→ 6 章（データ）→ 7 章（API）→ 5 章（画面）→ 10・11 章（設定・エラー）→ 12 章（セキュリティ）の順を推奨する。
3・4・8・9 章の図は、各章の理解を補う位置づけである。

---

## 2. システム構成

### 2.1 全体構成図

![システム構成図](sd_fig02_システム構成図.png)

ブラウザが通信する相手は Next.js（pos-web）のみである。FastAPI（pos-api）は pos-web からの要求だけを受け、
MySQL は pos-api からの接続だけを受ける。3 層の各境界で、それぞれ別の手段（Cookie / X-BFF-Key + アクセス制限 / DB 認証 + TLS）で通信を保護する。

### 2.2 コンポーネント

| コンポーネント | 技術 | 役割 | 対応 |
|---|---|---|---|
| ブラウザ（レジ端末） | Chrome / Edge / Safari 最新版、カメラ付き | 画面の表示と操作。ZXing でバーコードを復号（映像はサーバへ送らない）。購入リストの状態を保持 | P-5, N-05, N-10 |
| pos-web | Next.js 16（App Router）、TypeScript 5.x、Zod、@zxing/library | 画面の配信。Route Handler による BFF（Cookie ⇄ Bearer 変換、入力検証、中継） | P-2, N-01, 7.6 |
| pos-api | FastAPI 0.141、Pydantic 2、SQLAlchemy 2、PyJWT、bcrypt | 認証・認可、金額計算の正本、取引の保存、マスタ管理、監査ログ | P-3, N-01, 9 章 |
| MySQL | Azure Database for MySQL Flexible Server 8.x | 全データの永続化（6 章） | P-4, N-02 |
| Key Vault | Azure Key Vault | 秘密情報の保管。App Service のアプリケーション設定から参照 | SEC-02, 12.9 |
| ログ | App Service ログストリーム | アプリケーションログ（11.5） | N-09 |

### 2.3 Azure 上の配置

要件定義書 7 章の選定（App Service、Always On）を具体化する。

| 資源 | 設定 | 理由 |
|---|---|---|
| App Service Plan | Basic B1、Linux、1 インスタンス。pos-web と pos-api の 2 アプリを同一プランに配置 | 要件定義書 7.3。Always On は Basic 以上 |
| pos-web（App Service） | ランタイム Node 24 LTS。Always On 有効。HTTPS Only。ヘルスチェック `/api/health`（BFF が API-24 を中継） | N-03 |
| pos-api（App Service） | ランタイム Python 3.11。起動 `gunicorn -k uvicorn.workers.UvicornWorker`。Always On 有効。HTTPS Only。ヘルスチェック `/api/v1/health`。**アクセス制限: pos-web の送信 IP のみ許可、その他は拒否** | N-03, N-04, SEC-07 |
| MySQL Flexible Server | Burstable B1ms、MySQL 8、`require_secure_transport=ON`、パブリックアクセスは pos-api の送信 IP のみ許可（ファイアウォール）。自動バックアップ 7 日、時刻は UTC | N-08, DB-6, 12.8 |
| Key Vault | シークレット: `jwt-secret`、`database-url`、`bff-shared-key`。両 App Service のマネージド ID に読み取り権限 | 12.9 |
| リージョン | Japan East（両 App Service と MySQL を同一リージョンに置き、遅延を抑える） | N-03 |
| 復元 | 障害時はポイントインタイムリストアで別サーバとして復元し、pos-api の `DATABASE_URL` を切り替える。目標 RPO 5 分（自動バックアップ＋バイナリログ）、RTO 1 時間。手順は運用手順書に記載し、四半期に 1 回リハーサルする | N-08 |

VNet 統合と Private Endpoint による完全な閉域化は、Basic プランでは利用できないため採用しない。
アクセス制限（IP）＋ X-BFF-Key ＋ TLS で代替する（14 章に記録）。

### 2.4 通信経路と保護

| 区間 | プロトコル | 認証 | 追加の制御 |
|---|---|---|---|
| ブラウザ → pos-web | HTTPS（TLS 1.2+） | Cookie `pos_session`（HttpOnly, Secure, SameSite=Strict） | CSP、HSTS、Origin 検査（状態変更時）、レート制限（ログイン） |
| pos-web（BFF）→ pos-api | HTTPS | `Authorization: Bearer <JWT>`、`X-BFF-Key` | アクセス制限（送信 IP）、CORS は pos-web オリジンのみ、`X-Request-Id` |
| pos-api → MySQL | TLS | DB ユーザ／パスワード（Key Vault） | ファイアウォール（送信 IP）、最小権限ユーザ（12.8） |
| App Service → Key Vault | HTTPS | マネージド ID | RBAC（読み取りのみ） |

### 2.5 リポジトリ構成

1 つのリポジトリで管理する（モノレポ）。定数の正本 `shared/limits.json` を両側から参照するため。

```
pos-lv2/
├─ frontend/        Next.js（画面 + BFF）
│  ├─ app/          (pos)/login, (pos)/pos, (admin)/..., api/**/route.ts
│  ├─ features/     cart, scanner, checkout, admin
│  ├─ lib/          apiClient, schemas(Zod), pricing, constants
│  └─ types/api.ts
├─ backend/         FastAPI
│  ├─ app/          routers, services, repositories, models, schemas, core
│  ├─ alembic/      マイグレーション
│  └─ tests/
├─ shared/limits.json   10 章の定数（正本）
├─ docs/            要件定義書・設計仕様書・図
└─ .github/workflows/   CI（lint, test, npm audit, pip-audit）
```

### 2.6 要件との対応

| 要件 | 構成 |
|---|---|
| P-1〜P-4（Web / Next.js / FastAPI / Azure・MySQL） | 2.2 |
| P-5, N-05, N-10（カメラ付き端末・ブラウザ） | ブラウザ側 ZXing、HTTPS |
| N-01（役割分担） | pos-web = 画面 + BFF、pos-api = 業務ロジック |
| N-03, N-04（応答速度・接続維持） | Always On、接続プール、同一リージョン、ヘルスチェック |
| N-06（複数レジ） | 端末はブラウザのみ。状態はサーバに持たず、取引 ID は DB が採番 |
| N-07（セキュリティ） | 2.4 の各区間 |
| N-08（バックアップ） | MySQL 自動バックアップ 7 日 |
| 要件定義書 7 章（技術選定） | 2.3 で具体化 |

---

## 3. ユースケース

### 3.1 アクター

| アクター | 説明 | 権限（role） | 要件 |
|---|---|---|---|
| レジ担当者 | ログインしてレジ操作（会員読み込み・商品登録・会計）を行う | cashier | FR-01〜FR-08, FR-10 |
| 管理者 | レジ担当者の操作に加え、マスタ・設定の管理画面を操作する | admin（cashier を包含） | FR-09 |

システム外の要素として、商品と会員証のバーコード（カメラで読み取る。A-4）、およびデータベース（MySQL）がある。

### 3.2 ユースケース図

![ユースケース図](sd_fig03_ユースケース図.png)

UC-14「値引きと消費税を算出する」はアクターが直接起動するものではなく、購入リストが変化する
ユースケースから `include` される内部ユースケースである（API-06）。

### 3.3 ユースケース一覧

| UC | 名称 | アクター | 概要 | 主な要件 | API | 画面 |
|---|---|---|---|---|---|---|
| UC-01 | ログインする | レジ担当者／管理者 | 担当者IDとパスワードで認証し POS 画面へ | FR-01-1〜5 | API-01 | SC-01 |
| UC-02 | ログアウトする | レジ担当者／管理者 | セッションを終了し SC-01 へ戻る | FR-01-6 | API-02 | SC-02-03 |
| UC-03 | 会員証を読み込む | レジ担当者 | 会員証のバーコードまたは手入力で会員IDを取引に設定。登録済み商品にも値引きを遡り適用 | FR-02-1〜8, FR-06-7 | API-05, API-06 | SC-02-05〜08 |
| UC-04 | 会員IDをクリアする | レジ担当者 | 誤読み込みからの復帰。値引きを解除 | FR-02-9 | API-06 | SC-02-24 |
| UC-05 | 商品をスキャンして登録する | レジ担当者 | カメラで JAN を読み取り、購入リストへ自動追加（同一商品は数量加算） | FR-03-1〜2, 6, FR-04 | API-04, API-06 | SC-02-09, 15, 16 |
| UC-06 | 商品コードを手入力して登録する | レジ担当者 | コード入力→読み込み→名称・単価表示→追加 | FR-03-3〜5, FR-04 | API-04, API-06 | SC-02-10〜14 |
| UC-07 | 購入リストを編集する | レジ担当者 | 行を選択し、削除または数量変更（1〜99） | FR-05-1〜9 | API-06 | SC-02-17〜20 |
| UC-08 | 会計を確定する（現金） | レジ担当者 | 購入ボタン→預かり金額→確定。Backend が再計算・照合して保存し、お釣りを表示 | FR-08, FR-10-1〜5 | API-07 | SC-02-22, 23 |
| UC-09 | 会計をキャンセルする | レジ担当者 | 確定前に会計ポップアップを閉じ、購入リストを保ったまま戻る。キャンセルは監査ログに残す | FR-10-6, N-09 | API-27 | SC-02-23-6 |
| UC-10 | 商品マスタを管理する | 管理者 | 商品の一覧・登録・更新・論理削除 | FR-09-1 | API-12〜15 | SC-03 |
| UC-11 | 会員マスタを管理する | 管理者 | 会員の一覧・登録・更新・論理削除 | FR-09-2 | API-16〜19 | SC-04 |
| UC-12 | 消費税率を設定する | 管理者 | 税率と適用開始日を追加・修正・削除（適用開始前のもののみ） | FR-09-3, FR-07-2 | API-10, 11, 25, 26 | SC-05 |
| UC-13 | 値引きを設定する | 管理者 | 対象商品・期間・方式・値を登録・更新・論理削除 | FR-09-4, FR-06-6 | API-20〜23 | SC-06 |
| UC-14 | 値引きと消費税を算出する | （内部） | 購入リストと会員IDから値引き・税率・合計を算出 | FR-06-1〜5, FR-07-1〜3 | API-06 | SC-02-16, 21 |

### 3.4 主要ユースケースの記述

#### UC-05 商品をスキャンして登録する

| 項目 | 内容 |
|---|---|
| 事前条件 | ログイン済み。カメラプレビュー（SC-02-09）が商品モードで動作している |
| 基本フロー | 1. 担当者が商品のバーコードをカメラにかざす → 2. ZXing が JAN を復号 → 3. API-04 で商品を検索 → 4. 購入リストに同一商品があれば数量 +1、なければ新規行 → 5. API-06 で値引き・合計を再計算 → 6. リスト・合計を更新し「1件追加」を表示 → 7. 連続して次の商品を読み取れる |
| 代替フロー A（未登録） | 3 で 404 → 「商品がマスタ未登録です」を共通メッセージ領域に表示。リストは変えない |
| 代替フロー B（上限） | 4 で数量が 99 を超える → 加算せず「上限は 99」を表示。追加フィードバックは出さない |
| 事後条件 | 購入リストと合計が最新の計算結果と一致している |

#### UC-08 会計を確定する（現金）

| 項目 | 内容 |
|---|---|
| 事前条件 | 購入リストに 1 行以上ある |
| 基本フロー | 1. 購入ボタン（Idempotency-Key を生成） → 2. 会計ポップアップに税抜・税込合計、預かり金額（初期値 = 税込合計）を表示 → 3. 担当者が預かり金額を入力 → 4. 確定 → 5. API-07 が Backend で再計算・照合し、取引・明細・値引き適用・冪等キー・監査ログを 1 トランザクションで保存 → 6. お釣りを表示 → 7. 閉じるで画面をクリアし次の取引へ |
| 代替フロー A（不足） | 3 で預かり金額 < 税込合計 → 不足額を表示し確定ボタンを無効化 |
| 代替フロー B（照合不一致） | 5 で 409 PRICE_MISMATCH → サーバ値で表示を差し替え、再確認を促す。保存されない |
| 代替フロー C（キャンセル） | 2〜4 の間にキャンセル → 購入リストを保ったまま SC-02 へ戻る（UC-09） |
| 代替フロー D（再送） | 通信断で応答が届かず再送 → 同じ Idempotency-Key のため二重登録されず、初回と同じ応答 |
| 事後条件 | 取引が保存され、以後マスタを変更しても金額が変わらない（DR-1） |

---

## 4. 業務フロー

### 4.1 レジ 1 取引の流れ（アクティビティ図）

ログイン後の SC-02 で、1 組の会計が完了して画面がクリアされるまでを 1 枚にまとめる。
分岐はすべて要件定義書の要件に対応させている。

![アクティビティ図: レジ1取引](sd_fig04a_アクティビティ_レジ取引.png)

| 分岐 | 条件 | 要件 |
|---|---|---|
| 会員が存在? | API-05 の結果。不存在なら会員IDは未設定のまま | FR-02-6 |
| マスタに存在? | API-04 の結果。不存在なら「マスタ未登録」 | FR-03-4, FR-03-5 |
| 同一商品がリストにある? | あれば数量加算、なければ新規行 | FR-04-4, FR-04-5 |
| 数量 + 1 が 99 以下? | 超える場合は加算せず上限を表示。追加フィードバックなし | FR-05-9, FR-03-6 |
| 数量が 1〜99? | 数量変更 UI での範囲外は拒否し直前の値を維持 | FR-05-6, FR-05-7, FR-05-9 |
| リストが空? | 空のまま購入ボタン → 「商品未登録」 | FR-08-6 |
| 預かり金額が税込合計以上? | 画面では不足中は確定ボタンを無効化する（SC-02-23-4）。図の分岐は Backend 側の再確認（API-07 手順 4）を表す | FR-10-3 |
| Backend 再計算と一致? | 不一致は 409。サーバ値で表示更新 | SEC-09, API-07 |
| キャンセル | 確定前のみ。リストは保持 | FR-10-6 |

補足: 手入力の場合、「マスタに存在?」の後に名称・単価を表示し、「追加」ボタン押下で
「同一商品がリストにある?」以降へ進む（FR-03-3）。スキャンの場合はこの表示を経ずに進む。

### 4.2 管理者のマスタ操作（アクティビティ図）

![アクティビティ図: 管理者](sd_fig04b_アクティビティ_管理者.png)

4 つの管理画面（SC-03〜SC-06）は同じ構成（一覧・新規登録／編集フォーム・削除・戻る）を持つため、
1 つの流れで表す。検証は BFF（Zod）と FastAPI（Pydantic）の 2 段で行い、成功時は監査ログを記録する。

### 4.3 購入リストの状態

Frontend が保持する取引の状態と、遷移の契機を示す。5 章の状態管理設計の前提となる。

| 状態 | 説明 | 遷移先と契機 |
|---|---|---|
| idle | 購入リストが空、会員なし | → editing（商品追加／会員読み込み） |
| editing | 商品または会員が登録されている。すべての編集操作が可能 | → checkout（購入ボタン。リストが空なら遷移せずエラー）／→ idle（全行削除かつ会員クリア） |
| checkout | 会計ポップアップ表示中。リスト・会員の編集は不可 | → editing（キャンセル）／→ committed（確定成功）／→ checkout（照合不一致・不足のまま） |
| committed | 取引が保存済み。お釣りを表示 | → idle（閉じる。画面クリア） |

checkout 中は会員IDの読み込み・クリアを受け付けない（FR-02-3, FR-02-9）。

---

## 5. 画面設計

### 5.1 方針

- 画面と要素の識別子は要件定義書 4 章（SC-01〜SC-06、SC-02-01〜24、SC-02-23-1〜6）をそのまま用いる。画面イメージと画面遷移図も要件定義書のものを再掲する
- 本章で新たに定めるのは、**Next.js のルート**、**コンポーネント分割**、**状態管理**、**入力・表示の規則**である
- 値引きの判定と税率の決定は Backend（API-06）だけが行う。Frontend の `lib/pricing.ts` は、API-06 が返した明細ごとの値引き額と税率を入力として、数量変更直後の小計・合計を即時に再集計する（FR-05-8）だけで、API-06 の応答が届いたらその値に置き換える。確定時は Backend の結果が正（SEC-09）

### 5.2 画面一覧とルート

| 画面 | ルート | ガード | 主なコンポーネント |
|---|---|---|---|
| SC-01 ログイン | `/login` | 未ログインのみ。ログイン済みは `/pos` へ | `LoginForm` |
| SC-02 POS メイン | `/pos` | Cookie 必須（middleware）。なければ `/login` | 5.3 |
| SC-03 商品マスタ | `/admin/products` | role=admin（`/api/auth/me` で確認）。cashier は `/pos` へ | `DataTable`, `EntityForm` |
| SC-04 会員マスタ | `/admin/members` | 同上 | 同上 |
| SC-05 消費税率 | `/admin/tax-rates` | 同上 | 同上 |
| SC-06 値引き設定 | `/admin/discounts` | 同上 | 同上 |

ガードは 2 段で行う。`middleware.ts` が Cookie の有無と `exp` を見て未ログインを `/login` へ送り、
`(admin)` レイアウトが `/api/auth/me` の `role` を見て cashier を `/pos` へ送る。いずれも利便性のための制御で、
権限の強制は API 側（SEC-05）が担う。

### 5.3 SC-02 POS メイン画面のコンポーネント

![POSメイン画面（要件定義書 図1）](fig1_POSメイン画面.png)

| コンポーネント | 含む要素 | 読む状態 | 起こす操作 | API |
|---|---|---|---|---|
| `PosHeader` | SC-02-01 担当者名、02 管理画面、03 ログアウト | `staff` | ログアウト、管理画面へ遷移（admin のみ表示） | API-02 |
| `MessageBar` | SC-02-04 | `message` | 5 秒または次の操作で消去 | — |
| `MemberPanel` | SC-02-05〜08、24 | `member`, `status` | 手入力読み込み、会員証スキャン開始、クリア | API-05 → API-06 |
| `CameraPreview` | SC-02-09 | `scanMode`（product / member） | 復号結果を `MemberPanel` または `ProductEntryPanel` へ通知。同一コードは SCAN_DEBOUNCE_MS 内で無視。会員証モードは 1 件読み取り（会員の存否を問わず）・会員証スキャンボタンの再押下・MEMBER_SCAN_TIMEOUT_MS 経過のいずれかで商品モードへ戻る。商品モードで 13 桁の数字以外を読み取った場合は API-04 を呼ばず「商品がマスタ未登録です」を表示（FR-02-1, FR-03-5） | — |
| `ProductEntryPanel` | SC-02-10〜15 | `pendingProduct`（読み込んだ商品） | 手入力読み込み、追加。スキャン時は読み込みと追加を自動で連続実行 | API-04 → API-06 |
| `CartTable` | SC-02-16、17 | `lines`, `selectedLineNo`, `quote` | 行の選択 | — |
| `SelectedItemPanel` | SC-02-18〜20 | `lines[selected]` | 数量 ±／直接入力、削除 | API-06 |
| `TotalsPanel` | SC-02-21 | `quote` | — | — |
| `CheckoutButton` | SC-02-22 | `lines.length`, `status` | 空なら CART_EMPTY を表示、それ以外は checkout へ | — |
| `CheckoutDialog` | SC-02-23-1〜6 | `quote`, `tendered`, `commitResult` | 預かり金額入力、確定、キャンセル、閉じる | API-07 |

### 5.4 状態管理

購入リストの状態は 1 つのストア（`features/cart/store.ts`）に集約し、コンポーネントはそこから読む。
状態遷移は 4.3 に従う。

```ts
type CartStatus = "idle" | "editing" | "checkout" | "committed";   // 4.3
type ScanMode = "product" | "member";
interface CartLine { product_code: string; quantity: number }        // 入力（正本は Backend）

interface CartState {
  status: CartStatus;
  staff: StaffInfo;
  member: MemberInfo | null;
  scanMode: ScanMode;
  pendingProduct: ProductInfo | null;          // 手入力で読み込んだ、追加前の商品
  lines: CartLine[];
  quote: QuoteResult | null;                   // API-06 の最新結果（表示用）
  selectedLineNo: number | null;
  tendered: Money | null;
  idempotencyKey: string | null;               // checkout 開始時に生成、committed で破棄
  commitResult: CommitResponse | null;
  message: { code: string; text: string } | null;
}
```

| 操作 | 状態の変化 | 副作用 |
|---|---|---|
| 手入力の読み込み | `pendingProduct` を設定（名称・単価を表示） | API-04 |
| 商品追加（スキャン／追加ボタン） | `lines` に加算または追記。99 超なら変更せず `message`。`pendingProduct` を null に戻す（FR-04-2）。`pendingProduct` は新しい読み込み・スキャン成功・閉じるでも null に戻る | API-06 を QUOTE_DEBOUNCE_MS 後に呼び `quote` を更新。成功時に SC-02-15 を表示 |
| 行選択 | `selectedLineNo` | — |
| 数量変更・削除 | `lines` を更新 | API-06 → `quote` |
| 会員読み込み | `member` を設定 | API-05 → 成功で API-06（遡り適用） |
| 会員クリア | `member = null` | API-06（値引き解除） |
| 購入ボタン | `status = checkout`、`idempotencyKey` 生成、`tendered = quote.total_incl_tax` | — |
| キャンセル | `status = editing`、`idempotencyKey = null`（破棄）。次の購入ボタンで新しいキーを生成する | API-27 を非同期に呼び、監査ログ（TRANSACTION_CANCEL）を残す |
| 確定 | API-07。成功で `status = committed`、`commitResult` | 409 なら `quote` を `details.server` で置換し checkout に留まる |
| 閉じる | 全状態を初期化（`staff` 以外）、`status = idle` | フォーカスを会員ID入力（SC-02-05）へ（FR-08-4「次の会員ID読み込みから再開」） |

`quote` が古い（`lines` 変更後 API-06 の応答待ち）間は、確定ボタンを無効化して不整合な確定を防ぐ。

### 5.5 画面遷移

![画面遷移図（要件定義書 図2）](fig2_画面遷移図.png)

遷移の契機と対応要件は要件定義書 4.2 のとおり。本書での追加は 5.2 のガードのみ。

### 5.6 管理画面（SC-03〜SC-06）の共通コンポーネント

| コンポーネント | 役割 | 備考 |
|---|---|---|
| `DataTable<T>` | 一覧表示、検索欄（q）、ページング、行の編集・削除ボタン | `Page<T>` または配列を受け取る（税率はページングなし。適用開始日が本日以前の行は編集・削除ボタンを無効化） |
| `EntityForm<T>` | 新規登録／編集フォーム。Zod スキーマ（`lib/schemas.ts`）で項目ごとに検証し、エラーを項目の横に表示 | 7.5 の *CreateRequest / *UpdateRequest に対応 |
| `ConfirmDialog` | 削除前の確認。「過去の取引記録は残ります」を明示（DR-5） | — |
| `AdminLayout` | 戻る（`/pos`）、role 確認 | 5.2 |

画面ごとのフォーム項目は要件定義書 4.5 のとおり。追加の入力規則は 10.1 の定数に従う。

### 5.7 入力・表示の規則

| 項目 | 規則 | 根拠 |
|---|---|---|
| 金額の表示 | 3 桁区切り＋「円」（例 `1,207円`）。値引き額は `−120円` と赤字 | 要件定義書 図1 |
| 日時の表示 | JST、`YYYY/MM/DD HH:mm` | DB-6, APP_TIMEZONE_DISPLAY |
| 数値入力 | `inputmode="numeric"`。タブレットで数字キーボードを出す | N-05 |
| フォーカス | 商品追加後は商品コード入力（SC-02-10）へ、会計終了（閉じる）後は会員ID入力（SC-02-05）へ戻す。Enter キーで読み込み | 連続登録（FR-04-3）、FR-08-4 |
| 選択行の強調 | 背景色＋枠線。色だけに依存しない | FR-05-2 |
| 最小画面幅 | 1024px（タブレット横）。それ未満は左右 2 列を縦積みにする | N-05 |
| タッチ対象 | ボタンは 44px 以上 | タブレット操作 |
| 会員名の表示 | 氏名のみ。電話番号・住所は POS 画面に出さない | N-07 (4), API-05 |

### 5.8 要件との対応

| 要件 | 設計 |
|---|---|
| SC-01〜SC-06 | 5.2 ルートとガード |
| SC-02-01〜24, SC-02-23-1〜6 | 5.3 コンポーネント |
| FR-04, FR-05（購入リストの操作） | 5.4 状態管理 |
| FR-02-3, FR-02-9（会員操作の期限） | `status = checkout` で無効化 |
| FR-03-2（連続スキャン） | `CameraPreview` の常時動作、SCAN_DEBOUNCE_MS |
| FR-08-4（クリア） | 「閉じる」で全状態を初期化 |
| FR-10-6（キャンセル） | `status` を editing へ戻し `lines` を保持 |
| N-05, N-10 | 5.7 の端末向け規則 |

---

## 6. データ設計

要件定義書のデータ要件（D-01〜D-09、DR-1〜DR-5）を MySQL 8 の物理設計へ落とす。
各列の「対応」欄に要件定義書の項目番号を示す。

### 6.1 ER図

![ER図](sd_fig06_ER図.png)

`tax_rates` は取引と外部キーで結ばない。取引には適用時点の税率の**値**を写し取る（D-04-8）ため、
税率設定を後から変更しても過去の取引は影響を受けない（DR-1）。

### 6.2 共通規約

| # | 規約 | 内容 | 根拠 |
|---|---|---|---|
| DB-1 | 命名 | テーブル・列は英語の snake_case。テーブル名は複数形 | — |
| DB-2 | 主キー | 全テーブルに代理キー `id BIGINT UNSIGNED AUTO_INCREMENT`。業務キー（商品コード・会員ID・担当者ID）は別列に持ち UNIQUE 制約を付ける | N-06（採番の重複防止は DB が保証） |
| DB-3 | 論理削除 | マスタ・設定（staff / products / members / discounts / tax_rates）は `deleted_at DATETIME(6) NULL` による論理削除。NULL が有効行。取引系は削除しない | DR-5, DR-1 |
| DB-4 | 金額 | 円の整数 `INT`。小数は持たない | Q-1, Q-2 の端数処理を適用済みの値を保存 |
| DB-5 | 率 | 税率は `DECIMAL(5,2)`（例 10.00）。値引き値は `DECIMAL(10,2)`（割合なら %、金額なら円。`discount_type` で判別） | D-06-1, D-07-5〜6 |
| DB-6 | 日時 | `DATETIME(6)` に **UTC** で保存し、表示時に JST へ変換する。業務日付（税率・値引きの適用日）は `DATE`（JST）。DB 接続はセッションで `time_zone = '+00:00'` を明示し、DB サーバ側の TZ 設定に依存しない。業務日付との比較は SQL 側で日付を生成せず、Backend が作った取引日（6.5）をバインド変数で渡す | Azure のサーバ時刻が UTC |
| DB-7 | 文字コード | `utf8mb4`。文字列は `utf8mb4_0900_ai_ci`、コード類（`product_code` / `member_code` / `login_id`）は `utf8mb4_bin` | 大文字小文字の区別 |
| DB-8 | 監査列 | 全テーブルに `created_at DATETIME(6) NOT NULL`、マスタ・設定（DB-3 と同じ対象。tax_rates を含む）には `updated_at DATETIME(6) NOT NULL` を持つ | — |
| DB-9 | 外部キー | `ON DELETE RESTRICT`。業務テーブルでは物理削除を行わない。例外は `idempotency_keys` の期限切れ削除のみ（U-6） | DR-5 |
| DB-10 | スナップショット | 取引明細には商品の `product_code` / `product_name` / `unit_price` を、値引き適用記録には `discount_type` / `discount_value` を写し取る。FK も併せて持ち、マスタとの紐づけは残す | D-05-2〜4, D-08-2, DR-1 |

### 6.3 テーブル定義

型の後ろの `NN` は NOT NULL。`created_at` / `updated_at` / `deleted_at` は DB-3・DB-8 のとおりで、表からは省く（tax_rates のみ、削除条件が特殊なため `deleted_at` を明示する）。

#### staff（担当者）— D-01

| 列 | 型 | 制約 | 説明 | 対応 |
|---|---|---|---|---|
| id | BIGINT UNSIGNED | PK, AUTO_INCREMENT | 代理キー | — |
| login_id | VARCHAR(32) utf8mb4_bin | NN, UNIQUE | 担当者ID（ログイン識別子） | D-01-1 |
| password_hash | VARCHAR(60) | NN | bcrypt ハッシュ。平文は保持しない | D-01-2, N-07 |
| name | VARCHAR(50) | NN | 氏名。POS画面の担当者名表示に用いる | D-01-3 |
| role | ENUM('cashier','admin') | NN, 既定 'cashier' | 権限区分 | D-01-4, FR-09-5 |

#### products（商品マスタ）— D-02

| 列 | 型 | 制約 | 説明 | 対応 |
|---|---|---|---|---|
| id | BIGINT UNSIGNED | PK, AUTO_INCREMENT | 代理キー | — |
| product_code | VARCHAR(13) utf8mb4_bin | NN, UNIQUE | 商品コード（JAN 13 桁。Q-5） | D-02-1 |
| name | VARCHAR(100) | NN | 商品名称 | D-02-2 |
| unit_price | INT | NN, CHECK ≥ 0 | 税抜単価（円） | D-02-3 |

#### members（会員マスタ）— D-03

| 列 | 型 | 制約 | 説明 | 対応 |
|---|---|---|---|---|
| id | BIGINT UNSIGNED | PK, AUTO_INCREMENT | 代理キー | — |
| member_code | VARCHAR(32) utf8mb4_bin | NN, UNIQUE | 会員ID（会員証バーコードの値。CODE128） | D-03-1 |
| name | VARCHAR(50) | NN | 氏名 | D-03-2 |
| phone | VARCHAR(20) | NULL | 電話番号 | D-03-3 |
| address | VARCHAR(200) | NULL | 住所 | D-03-4 |
| gender | ENUM('male','female','other') | NULL | 性別 | D-03-5 |
| birth_date | DATE | NULL | 生年月日。年齢は表示時に算出 | D-03-6, I-4 |

#### transactions（取引）— D-04

| 列 | 型 | 制約 | 説明 | 対応 |
|---|---|---|---|---|
| id | BIGINT UNSIGNED | PK, AUTO_INCREMENT | 取引ID | D-04-1 |
| transacted_at | DATETIME(6) | NN | 購入確定日時（UTC） | D-04-2 |
| staff_id | BIGINT UNSIGNED | NN, FK → staff.id | レジ処理した担当者 | D-04-3 |
| member_id | BIGINT UNSIGNED | NULL, FK → members.id | 購入した会員。会員なしは NULL | D-04-4, DR-2 |
| subtotal_excl_tax | INT | NN | 税抜合計（値引き後） | D-04-5 |
| tax_amount | INT | NN | 消費税額 | D-04-6 |
| total_incl_tax | INT | NN | 税込合計 | D-04-7 |
| tax_rate | DECIMAL(5,2) | NN | 適用した消費税率（%） | D-04-8 |
| tendered_amount | INT | NN, CHECK ≥ total_incl_tax | 預かり金額 | D-04-9 |
| change_amount | INT | NN | お釣り（= tendered_amount − total_incl_tax） | D-04-10 |

#### transaction_items（取引明細）— D-05

| 列 | 型 | 制約 | 説明 | 対応 |
|---|---|---|---|---|
| id | BIGINT UNSIGNED | PK, AUTO_INCREMENT | 代理キー | — |
| transaction_id | BIGINT UNSIGNED | NN, FK → transactions.id | 親取引 | D-05-1 |
| line_no | INT | NN, UNIQUE(transaction_id, line_no) | 表示順（1 始まり） | — |
| product_id | BIGINT UNSIGNED | NN, FK → products.id | 商品（マスタへの紐づけ） | — |
| product_code | VARCHAR(13) | NN | 商品コード（購入時点の写し） | D-05-2 |
| product_name | VARCHAR(100) | NN | 商品名称（購入時点の写し） | D-05-3 |
| unit_price | INT | NN | 税抜単価（購入時点の写し） | D-05-4 |
| quantity | INT | NN, CHECK 1〜99 | 数量 | D-05-5, FR-05-6 |
| discount_amount | INT | NN, 既定 0 | 値引き額（円） | D-05-6 |
| line_total | INT | NN | 小計 = unit_price × quantity − discount_amount | D-05-7 |

#### tax_rates（消費税率設定）— D-06

| 列 | 型 | 制約 | 説明 | 対応 |
|---|---|---|---|---|
| id | BIGINT UNSIGNED | PK, AUTO_INCREMENT | 代理キー | — |
| rate | DECIMAL(5,2) | NN, CHECK 0〜100 | 税率（%） | D-06-1 |
| effective_from | DATE | NN, UNIQUE | 適用開始日（JST）。取引日時以前で最新の 1 件を適用 | D-06-2, FR-07-2 |
| created_by_staff_id | BIGINT UNSIGNED | NULL, FK → staff.id | 登録した管理者 | FR-09-3 |
| deleted_at | DATETIME(6) | NULL | 論理削除（適用開始前の設定のみ削除可。API-26） | DB-3 |

#### discounts（値引き設定）— D-07

| 列 | 型 | 制約 | 説明 | 対応 |
|---|---|---|---|---|
| id | BIGINT UNSIGNED | PK, AUTO_INCREMENT | 値引きID | D-07-1 |
| product_id | BIGINT UNSIGNED | NN, FK → products.id | 対象商品 | D-07-2 |
| name | VARCHAR(100) | NN | 販促企画名（管理画面での識別用。本書で追加） | — |
| start_date | DATE | NN | 適用開始日（JST） | D-07-3 |
| end_date | DATE | NN, CHECK ≥ start_date | 適用終了日（JST。当日を含む） | D-07-4 |
| discount_type | ENUM('percent','amount') | NN | 値引き方式 | D-07-5 |
| discount_value | DECIMAL(10,2) | NN, CHECK > 0 | 値引き値（percent は 0〜100） | D-07-6 |

> 同一商品で期間が重なる値引きの登録は許容する（複数該当時の選択は 6.5・DISCOUNT_SELECTION）。
> 管理画面は保存前に API-20（q = 対象商品コード）で既存の設定を取得し、期間が重なるものがあれば
> 警告を表示するが、保存は拒否しない（U-12）。

#### discount_applications（値引き適用記録）— D-08

| 列 | 型 | 制約 | 説明 | 対応 |
|---|---|---|---|---|
| id | BIGINT UNSIGNED | PK, AUTO_INCREMENT | 代理キー | — |
| transaction_item_id | BIGINT UNSIGNED | NN, UNIQUE, FK → transaction_items.id | 対象明細。1 明細に 1 件（Q-4） | D-08-1 |
| discount_id | BIGINT UNSIGNED | NN, FK → discounts.id | 適用した値引き設定 | D-08-2 |
| discount_type | ENUM('percent','amount') | NN | 適用時点の方式（写し） | D-08-2, DR-1 |
| discount_value | DECIMAL(10,2) | NN | 適用時点の値（写し） | D-08-2, DR-1 |
| applied_amount | INT | NN | 値引き額（円）。transaction_items.discount_amount と一致 | D-08-3 |

#### audit_logs（操作ログ）— D-09

| 列 | 型 | 制約 | 説明 | 対応 |
|---|---|---|---|---|
| id | BIGINT UNSIGNED | PK, AUTO_INCREMENT | 代理キー | — |
| occurred_at | DATETIME(6) | NN | 発生日時（UTC） | D-09-1 |
| action | VARCHAR(50) | NN | 操作種別コード（LOGIN / LOGOUT / LOGIN_FAILED / TRANSACTION_COMMIT / TRANSACTION_CANCEL / PRODUCT_CREATE・UPDATE・DELETE / MEMBER_CREATE・UPDATE・DELETE / TAX_RATE_CREATE・UPDATE・DELETE / DISCOUNT_CREATE・UPDATE・DELETE） | D-09-2 |
| staff_id | BIGINT UNSIGNED | NULL, FK → staff.id | 操作者。ログイン失敗時は NULL | D-09-3 |
| attempted_login_id | VARCHAR(32) | NULL | ログイン失敗時に入力された担当者ID | D-09-3 |
| target_type | VARCHAR(30) | NULL | 対象種別（transaction / product / member / tax_rate / discount） | D-09-4 |
| target_id | VARCHAR(64) | NULL | 対象の識別子 | D-09-4 |
| result | ENUM('success','failure') | NN | 結果 | D-09-5 |
| detail | VARCHAR(500) | NULL | 失敗理由・補足 | D-09-5 |
| ip_address | VARCHAR(45) | NULL | 要求元 IP（IPv6 対応長。本書で追加） | N-09 |

#### idempotency_keys（冪等キー）— 本書で追加

API-07 の二重送信防止（7.3）に用いる技術テーブル。業務データではないため ER 図には載せていない。

| 列 | 型 | 制約 | 説明 | 対応 |
|---|---|---|---|---|
| idempotency_key | CHAR(36) | PK | Frontend が生成した UUID v4 | 7.3 冪等性 |
| staff_id | BIGINT UNSIGNED | NN, FK → staff.id | 要求した担当者（他人のキーを流用させない） | SEC-05 |
| request_hash | CHAR(64) | NN | 要求本文の SHA-256。同キー・異本文の検出（409 DUPLICATE_REQUEST） | 7.3 |
| response_status | SMALLINT | NN | 保存した応答のステータス（201） | 7.3 |
| response_body | JSON | NN | 保存した応答本文（CommitResponse） | 7.3 |
| expires_at | DATETIME(6) | NN | `IDEMPOTENCY_TTL_HOURS` 後。期限切れは日次で削除 | 10 章 |

### 6.4 索引一覧

| テーブル | 索引 | 種別 | 目的 |
|---|---|---|---|
| staff | (login_id) | UNIQUE | ログイン時の検索 |
| products | (product_code) | UNIQUE | スキャン・手入力からの商品検索（FR-03-4）。1 秒以内の目標（要件定義書 6.1） |
| members | (member_code) | UNIQUE | 会員証読み込み（FR-02-1） |
| transactions | (transacted_at) | INDEX | 期間での集計・調査 |
| transactions | (staff_id), (member_id) | INDEX（FK） | 担当者別・会員別の照会 |
| transaction_items | (transaction_id, line_no) | UNIQUE | 明細の一意性と表示順 |
| transaction_items | (product_id) | INDEX（FK） | 商品別の販売実績 |
| tax_rates | (effective_from) | UNIQUE | 有効税率の決定（FR-07-2） |
| discounts | (product_id, start_date, end_date) | INDEX | 商品追加時の値引き判定（FR-06-1, FR-06-4） |
| discount_applications | (transaction_item_id) | UNIQUE | 1 明細 1 値引き（Q-4） |
| audit_logs | (occurred_at), (staff_id) | INDEX | 期間・担当者での追跡（N-09） |
| idempotency_keys | (expires_at) | INDEX | 期限切れキーの削除 |

### 6.5 有効な設定の決定規則

| 対象 | 規則 | 根拠 |
|---|---|---|
| 消費税率 | `deleted_at IS NULL` かつ `effective_from <= 取引日（JST）` を満たす行のうち `effective_from` が最大の 1 件。該当なしはエラー（税率未設定） | FR-07-2, D-06-2 |
| 値引き | 会員あり取引で、`product_id` が一致し `start_date <= 取引日（JST） <= end_date` かつ `deleted_at IS NULL` の行（end_date は当日を含む）。複数該当時は値引き額が最大の 1 件 | FR-06-1, FR-06-4, Q-4 |
| 取引日（JST）の決定 | 上 2 行で用いる「取引日（JST）」は **Backend の `PricingService` が 1 箇所で生成する**。現在時刻を UTC で 1 回取得し（`Clock.now()`）、`BUSINESS_TIMEZONE`（Asia/Tokyo）へ変換した日付を用いる。`date.today()`（サーバの TZ に依存）、SQL の `CURDATE()` / `NOW()`（DB サーバの TZ に依存）、Frontend の時計は使わない。API-07 では取引時刻 `transacted_at` を先に 1 回取得し、**その同じ瞬間**から取引日を作って税率判定・値引き判定・保存のすべてに用いる（1 リクエスト内で日付を 2 回取らない）。API-06 の見積時の日付とは取り直すため、JST 0:00 をまたぐと値引きが変わり得るが、その場合は照合不一致（409 PRICE_MISMATCH）で Frontend に再表示させる。Azure のサーバは UTC で動くため、JST 0:00〜8:59 は `date.today()` が前日を返す。境界テストは 9.3 参照 | DB-6, SEC-09, 10.4 |

### 6.6 データ要件との対応

| 要件 | 設計 |
|---|---|
| D-01-1〜4 | staff.login_id / password_hash / name / role |
| D-02-1〜3 | products.product_code / name / unit_price |
| D-03-1〜6 | members.member_code / name / phone / address / gender / birth_date |
| D-04-1〜10 | transactions の各列 |
| D-05-1〜7 | transaction_items の各列 |
| D-06-1〜2 | tax_rates.rate / effective_from |
| D-07-1〜6 | discounts の各列 |
| D-08-1〜3 | discount_applications の各列 |
| D-09-1〜5 | audit_logs の各列 |
| DR-1 | DB-10（スナップショット列）、tax_rates と取引を FK で結ばない |
| DR-2 | transactions.member_id NULL 許容 |
| DR-3 | transactions.transacted_at / staff_id / member_id、transaction_items の写し列 |
| DR-4 | tax_rates / discounts をテーブルとして保持し、管理画面（SC-05 / SC-06）から更新 |
| DR-5 | DB-3（論理削除）＋ DB-9（ON DELETE RESTRICT） |

---

## 7. API設計

### 7.1 方針

| # | 項目 | 内容 |
|---|---|---|
| API-P1 | 経路 | ブラウザ → Next.js Route Handler `/api/...`（BFF）→ FastAPI `/api/v1/...`。ブラウザから FastAPI へ直接アクセスさせない（12章） |
| API-P2 | 形式 | REST + JSON（`Content-Type: application/json; charset=utf-8`）。バージョンは `/v1` 固定 |
| API-P3 | 認証 | BFF が HttpOnly Cookie の JWT を `Authorization: Bearer <token>` に付け替えて FastAPI へ渡す。FastAPI は全 API（`/auth/login`・`/health` を除く）で JWT を検証する |
| API-P4 | 認可 | `role` クレームで判定。`cashier` はレジ業務 API、`admin` はそれに加え管理 API |
| API-P5 | 日時 | ISO 8601 の UTC 文字列（例 `2026-09-07T03:15:00.000000Z`）。表示時に JST へ変換 |
| API-P6 | 金額 | 円の整数（JSON number）。率は小数（10.00 = 10%） |
| API-P7 | 命名 | JSON キーは snake_case（DB 列名と一致させ、変換層を持たない） |
| API-P8 | 入力検証 | 型・形式（数値か、13 桁の数字か等）は Pydantic で検証し、違反は 400 VALIDATION_ERROR。業務上の範囲（数量・行数・預かり金額・期間）はサービス層で判定し、422 の業務コードを返す（11.4）。上下限は 10 章の定数を参照 |

### 7.2 API一覧

| # | メソッド | パス（`/api/v1` 以下） | 概要 | 認可 | 対応要件 |
|---|---|---|---|---|---|
| API-01 | POST | `/auth/login` | 担当者ID・パスワードで認証し JWT を発行 | なし | FR-01-1〜4 |
| API-02 | POST | `/auth/logout` | ログアウト（監査ログ記録。Cookie 破棄は BFF） | cashier | FR-01-6 |
| API-03 | GET | `/auth/me` | ログイン中の担当者情報 | cashier | FR-01-5, SC-02-01 |
| API-04 | GET | `/products/{code}` | 商品コードで商品を検索 | cashier | FR-03-4, FR-03-5 |
| API-05 | GET | `/members/{code}` | 会員IDで会員を検索（氏名のみ返す） | cashier | FR-02-4, FR-02-6 |
| API-06 | POST | `/pricing/quote` | 購入リスト＋会員IDから値引き・税・合計を算出 | cashier | FR-06, FR-07, FR-05-8 |
| API-07 | POST | `/transactions` | 取引を確定・保存（Frontend 計算値と照合） | cashier | FR-08, FR-10 |
| API-08 | GET | `/transactions/{id}` | 確定した取引の内容を取得 | cashier | FR-08-2 |
| API-09 | GET | `/tax-rates/current` | 本日有効な消費税率 | cashier | FR-07-2 |
| API-10 | GET | `/tax-rates` | 税率設定の一覧 | admin | FR-09-3 |
| API-11 | POST | `/tax-rates` | 税率設定を追加 | admin | FR-09-3 |
| API-12 | GET | `/products` | 商品一覧（検索・ページング） | admin | FR-09-1 |
| API-13 | POST | `/products` | 商品を登録 | admin | FR-09-1 |
| API-14 | PUT | `/products/{id}` | 商品を更新（商品コードは変更不可） | admin | FR-09-1 |
| API-15 | DELETE | `/products/{id}` | 商品を論理削除 | admin | FR-09-1, DR-5 |
| API-16 | GET | `/members` | 会員一覧 | admin | FR-09-2 |
| API-17 | POST | `/members` | 会員を登録 | admin | FR-09-2 |
| API-18 | PUT | `/members/{id}` | 会員を更新（会員IDは変更不可） | admin | FR-09-2 |
| API-19 | DELETE | `/members/{id}` | 会員を論理削除 | admin | FR-09-2, DR-5 |
| API-20 | GET | `/discounts` | 値引き設定の一覧 | admin | FR-09-4 |
| API-21 | POST | `/discounts` | 値引き設定を登録 | admin | FR-09-4 |
| API-22 | PUT | `/discounts/{id}` | 値引き設定を更新 | admin | FR-09-4 |
| API-23 | DELETE | `/discounts/{id}` | 値引き設定を論理削除 | admin | FR-09-4 |
| API-24 | GET | `/health` | 稼働確認（DB 接続を含む） | なし | N-02, N-03 |
| API-25 | PUT | `/tax-rates/{id}` | 税率設定を修正（適用開始前のもののみ） | admin | FR-09-3 |
| API-26 | DELETE | `/tax-rates/{id}` | 税率設定を論理削除（適用開始前のもののみ） | admin | FR-09-3 |
| API-27 | POST | `/transactions/cancel` | 会計キャンセルを監査ログに記録 | cashier | FR-10-6, N-09 |

### 7.3 共通仕様

**エラー応答**（全 API 共通。コードの一覧は 11 章）

```json
{
  "error": {
    "code": "PRODUCT_NOT_FOUND",
    "message": "商品がマスタ未登録です",
    "details": {}
  }
}
```

| HTTP | 用途 | 代表コード |
|---|---|---|
| 400 | 型・形式の不正（Pydantic 検証失敗） | VALIDATION_ERROR |
| 401 | 未認証・トークン無効／期限切れ | AUTH_REQUIRED, AUTH_INVALID_CREDENTIALS |
| 403 | 権限不足 | FORBIDDEN |
| 404 | 対象が存在しない（論理削除済みを含む） | PRODUCT_NOT_FOUND, MEMBER_NOT_FOUND, NOT_FOUND |
| 409 | 業務上の衝突 | PRICE_MISMATCH, DUPLICATE_CODE, DUPLICATE_REQUEST |
| 422 | 業務ルール違反 | QUANTITY_OUT_OF_RANGE, CART_EMPTY, CART_TOO_MANY_LINES, INSUFFICIENT_TENDER, TAX_RATE_NOT_CONFIGURED, INVALID_PERIOD |
| 413 | 要求本文が大きすぎる | PAYLOAD_TOO_LARGE |
| 429 | ログイン試行の制限超過（BFF が返す） | RATE_LIMITED |
| 500 | サーバ内部エラー（詳細は返さずログへ） | INTERNAL_ERROR |
| 503 | DB 接続不可 | SERVICE_UNAVAILABLE |
| 504 | FastAPI が応答しない（BFF が返す） | GATEWAY_TIMEOUT |

**冪等性**（API-07）

- Frontend は取引ごとに UUID v4 を生成し `Idempotency-Key` ヘッダで送る
- 同一キーの再送には、初回と同じ応答（201 と同じ本文）を返し、取引を二重登録しない
- 同一キーで本文が異なる場合は 409 DUPLICATE_REQUEST
- キーは 24 時間保持する（10 章 `IDEMPOTENCY_TTL_HOURS`）

**ページング**（API-12, 16, 20。API-10 は件数が少ないためページングなし）

| パラメータ | 型 | 既定 | 制約 |
|---|---|---|---|
| q | string | なし | 部分一致検索（商品: コード・名称、会員: 会員ID・氏名） |
| page | integer | 1 | ≥ 1 |
| size | integer | 50 | 1〜100 |

応答は `{ "items": [...], "page": 1, "size": 50, "total": 1234 }`。

**共通ヘッダ**

| ヘッダ | 方向 | 内容 |
|---|---|---|
| Authorization | 要求 | `Bearer <JWT>`（BFF が付与） |
| Idempotency-Key | 要求 | API-07 のみ必須 |
| X-Request-Id | 双方向 | BFF が生成し FastAPI がログと応答に載せる（障害調査用） |

### 7.4 共通型定義（TypeScript）

Frontend（BFF を含む）で用いる型。`int` はコメントで示し、実行時は Zod で検証する（12 章）。

```ts
// ---- 基本型 ----
type Money = number;          // 円の整数
type Rate = number;           // 百分率（10.00 = 10%）
type DateTimeUTC = string;    // ISO 8601, 例 "2026-09-07T03:15:00.000000Z"
type DateJST = string;        // "YYYY-MM-DD"
type Role = "cashier" | "admin";
type DiscountType = "percent" | "amount";

// ---- エラー ----
interface ApiError {
  error: { code: string; message: string; details: Record<string, unknown> };
}

// ---- ページング ----
interface Page<T> { items: T[]; page: number; size: number; total: number }

// ---- 主要エンティティ ----
interface StaffInfo { id: number; login_id: string; name: string; role: Role }
interface ProductInfo { id: number; product_code: string; name: string; unit_price: Money }
interface MemberInfo { id: number; member_code: string; name: string }   // 個人情報は氏名のみ
interface TaxRateInfo { id: number; rate: Rate; effective_from: DateJST }
interface DiscountInfo {
  id: number; product_code: string; name: string;
  start_date: DateJST; end_date: DateJST;
  discount_type: DiscountType; discount_value: number;
}

// ---- 価格計算 ----
interface QuoteItemRequest { product_code: string; quantity: number }          // quantity 1..99
interface AppliedDiscount { discount_id: number; type: DiscountType; value: number; amount: Money }
interface QuoteLine {
  product_code: string; product_name: string; unit_price: Money; quantity: number;
  discount: AppliedDiscount | null; line_total: Money;
}
interface QuoteResult {
  tax_rate: Rate; lines: QuoteLine[];
  subtotal_excl_tax: Money; tax_amount: Money; total_incl_tax: Money;
}
```

### 7.5 API詳細

各表の「制約」は 10 章の定数名で示す。

#### API-01 POST /auth/login

| 入力（body） | 型 | 必須 | 制約 |
|---|---|---|---|
| login_id | string | ○ | 1〜32 文字、半角英数字と `_-` |
| password | string | ○ | `PASSWORD_MIN`〜`PASSWORD_MAX` 文字 |

| 出力（200） | 型 | 説明 |
|---|---|---|
| access_token | string | JWT（HS256）。BFF が HttpOnly Cookie に格納し、ブラウザには返さない |
| token_type | "Bearer" | |
| expires_in | integer | 秒。`JWT_TTL_HOURS` × 3600 |
| staff | StaffInfo | ブラウザへはこれのみ返す |

エラー: 401 AUTH_INVALID_CREDENTIALS（ID・パスワードのどちらが誤りかは区別しない。FR-01-4）。
副作用: 成功・失敗ともに audit_logs へ記録（LOGIN / LOGIN_FAILED）。

```ts
interface LoginRequest { login_id: string; password: string }
interface LoginResponse { access_token: string; token_type: "Bearer"; expires_in: number; staff: StaffInfo }
// BFF → ブラウザ: { staff: StaffInfo } のみ
```

#### API-02 POST /auth/logout

入力なし。出力 204。副作用: audit_logs（LOGOUT）。BFF は Cookie を失効させる。

#### API-03 GET /auth/me

入力なし。出力 200: `StaffInfo`。JWT が無効なら 401。

#### API-04 GET /products/{code}

| 入力（path） | 型 | 必須 | 制約 |
|---|---|---|---|
| code | string | ○ | `PRODUCT_CODE_LENGTH` 桁の数字 |

出力 200: `ProductInfo`。エラー: 404 PRODUCT_NOT_FOUND（論理削除済みも 404。FR-03-5）、400 VALIDATION_ERROR（桁数・文字種）。

#### API-05 GET /members/{code}

| 入力（path） | 型 | 必須 | 制約 |
|---|---|---|---|
| code | string | ○ | 1〜`MEMBER_CODE_MAX` 文字、半角英数字 |

出力 200: `MemberInfo`（氏名のみ。電話番号・住所は返さない。N-07 (4)）。エラー: 404 MEMBER_NOT_FOUND（FR-02-6）。

#### API-06 POST /pricing/quote

購入リストの内容が変わるたび（追加・削除・数量変更・会員読み込み・会員クリア）に Frontend が呼ぶ。
値引きの判定と税率の決定はこの API が行い、Frontend はその結果を表示に用いる。

| 入力（body） | 型 | 必須 | 制約 |
|---|---|---|---|
| member_code | string \| null | — | 会員なしは null |
| items | QuoteItemRequest[] | ○ | 0〜`CART_MAX_LINES` 行（0 行は合計 0 を返す）。product_code は重複不可 |
| items[].product_code | string | ○ | `PRODUCT_CODE_LENGTH` 桁 |
| items[].quantity | integer | ○ | `QTY_MIN`〜`QTY_MAX` |

| 出力（200） | 型 | 説明 |
|---|---|---|
| tax_rate | Rate | 本日有効な税率（6.5） |
| lines[] | QuoteLine | 入力順。discount は適用なしなら null |
| subtotal_excl_tax | Money | Σ line_total |
| tax_amount | Money | floor(subtotal_excl_tax × tax_rate / 100)（Q-1） |
| total_incl_tax | Money | subtotal_excl_tax + tax_amount |

前提: 計算に用いる「取引日（JST）」は、要求を受けた時点の UTC 現在時刻を 1 回取得し `BUSINESS_TIMEZONE` へ変換して作る（6.5）。有効税率・値引きの判定はこの 1 つの値で行う。

計算規則（Backend の正本。Frontend は規則 3〜5 の集計のみを表示用に行い、規則 1〜2 の値引き判定は行わない）:

1. `line_gross = unit_price × quantity`
2. 会員ありで有効な値引きがある場合、`discount.amount = percent なら floor(line_gross × value / 100)、amount なら min(value × quantity, line_gross)`（Q-2。値引き額は行の金額を超えない）
3. `line_total = line_gross − discount.amount`
4. `subtotal_excl_tax = Σ line_total`（値引き後に課税。Q-3）
5. `tax_amount = floor(subtotal_excl_tax × tax_rate / 100)`、`total_incl_tax = subtotal_excl_tax + tax_amount`

エラー: 404 PRODUCT_NOT_FOUND / MEMBER_NOT_FOUND（details に該当コード）、422 QUANTITY_OUT_OF_RANGE / CART_TOO_MANY_LINES / TAX_RATE_NOT_CONFIGURED。

```ts
interface QuoteRequest { member_code: string | null; items: QuoteItemRequest[] }
type QuoteResponse = QuoteResult;
```

#### API-07 POST /transactions

会計ポップアップの「確定」で呼ぶ（FR-10-4）。Frontend が表示していた金額を**そのまま送り**、Backend がマスタから再計算して照合する。

| 入力（header） | 必須 | 制約 |
|---|---|---|
| Idempotency-Key | ○ | UUID v4 |

| 入力（body） | 型 | 必須 | 制約 |
|---|---|---|---|
| member_code | string \| null | — | |
| items[] | object | ○ | 0〜`CART_MAX_LINES` 行（0 行は 422 CART_EMPTY） |
| items[].product_code | string | ○ | |
| items[].quantity | integer | ○ | `QTY_MIN`〜`QTY_MAX` |
| items[].unit_price | Money | ○ | Frontend が表示していた単価 |
| items[].discount_amount | Money | ○ | 同・値引き額（なしは 0） |
| items[].line_total | Money | ○ | 同・小計 |
| tax_rate | Rate | ○ | 同・税率 |
| subtotal_excl_tax | Money | ○ | 同・税抜合計 |
| tax_amount | Money | ○ | 同・税額 |
| total_incl_tax | Money | ○ | 同・税込合計 |
| tendered_amount | Money | ○ | 預かり金額。0〜`TENDER_MAX` |

Backend の処理順（手順 3〜5 で用いる取引時刻と取引日は、手順 2 の後に **1 回だけ**取得した同じ瞬間の値とする。6.5）:

1. Pydantic で型・形式を検証（400）。数量・行数・預かり金額の業務範囲はサービス層で判定し 422 を返す（API-P8）
2. Idempotency-Key を確認。既存なら保存済み応答を返す（同本文）／409 DUPLICATE_REQUEST（異本文）
3. API-06 と同じ規則で全額を再計算し、明細ごとの `unit_price` / `discount_amount` / `line_total` と 4 つの合計を Frontend の値と比較。**1 円でも差があれば 409 PRICE_MISMATCH** とし、details に Backend の `QuoteResult` を返す（Frontend は表示を差し替えて再確認を促す）。不一致は audit_logs（TRANSACTION_COMMIT, failure, detail=PRICE_MISMATCH）に記録する
4. `tendered_amount < total_incl_tax` なら 422 INSUFFICIENT_TENDER（FR-10-3）
5. 1 トランザクションで transactions → transaction_items → discount_applications → idempotency_keys（応答本文を保存）→ audit_logs（TRANSACTION_COMMIT, success）を INSERT し COMMIT する。写し列は Backend の再計算値。`line_no` は items の配列順に 1 から Backend が採番する
6. 201 を返す

| 出力（201） | 型 | 説明 |
|---|---|---|
| transaction_id | integer | D-04-1 |
| transacted_at | DateTimeUTC | D-04-2 |
| subtotal_excl_tax / tax_amount / total_incl_tax | Money | 確定値 |
| tendered_amount | Money | |
| change_amount | Money | tendered_amount − total_incl_tax（FR-10-2） |

```ts
interface CommitItem {
  product_code: string; quantity: number;
  unit_price: Money; discount_amount: Money; line_total: Money;
}
interface CommitRequest {
  member_code: string | null; items: CommitItem[];
  tax_rate: Rate; subtotal_excl_tax: Money; tax_amount: Money; total_incl_tax: Money;
  tendered_amount: Money;
}
interface CommitResponse {
  transaction_id: number; transacted_at: DateTimeUTC;
  subtotal_excl_tax: Money; tax_amount: Money; total_incl_tax: Money;
  tendered_amount: Money; change_amount: Money;
}
// 409 PRICE_MISMATCH の details: { server: QuoteResult }
```

#### API-08 GET /transactions/{id}

| 入力（path） | 型 | 必須 |
|---|---|---|
| id | integer | ○ |

出力 200: 取引と明細（`CommitResponse` に `staff: StaffInfo`、`member: MemberInfo | null`、`items: (CommitItem & { product_name: string; line_no: number })[]` を加えたもの）。404 NOT_FOUND。

#### API-09 GET /tax-rates/current

入力なし。出力 200: `TaxRateInfo`（6.5 の規則で決定）。422 TAX_RATE_NOT_CONFIGURED。

#### API-10 GET /tax-rates　/　API-11 POST /tax-rates

API-10: ページングなし。出力 200: `TaxRateInfo[]`（effective_from 降順）。

API-11 入力（body）:

| 項目 | 型 | 必須 | 制約 |
|---|---|---|---|
| rate | Rate | ○ | 0〜100、小数 2 桁まで |
| effective_from | DateJST | ○ | 本日以降（違反は 422 INVALID_PERIOD）。既存と重複不可（409 DUPLICATE_CODE） |

出力 201: `TaxRateInfo`。副作用: audit_logs（TAX_RATE_CREATE）。修正・削除は API-25 / API-26。

#### API-12〜15 商品マスタ

| API | 入力 | 出力 | エラー |
|---|---|---|---|
| API-12 GET /products | q, page, size（7.3） | 200 `Page<ProductInfo>`。論理削除済みは含めない | — |
| API-13 POST /products | body: product_code（`PRODUCT_CODE_LENGTH` 桁）、name（1〜100 文字）、unit_price（0〜`PRICE_MAX`） | 201 `ProductInfo` | 409 DUPLICATE_CODE |
| API-14 PUT /products/{id} | body: name、unit_price（product_code は変更不可） | 200 `ProductInfo` | 404 NOT_FOUND |
| API-15 DELETE /products/{id} | — | 204。`deleted_at` を設定 | 404 NOT_FOUND |

副作用: audit_logs（PRODUCT_CREATE / UPDATE / DELETE）。単価変更は確定済み取引に影響しない（DR-1）。

```ts
interface ProductCreateRequest { product_code: string; name: string; unit_price: Money }
interface ProductUpdateRequest { name: string; unit_price: Money }
```

#### API-16〜19 会員マスタ

| API | 入力 | 出力 | エラー |
|---|---|---|---|
| API-16 GET /members | q, page, size | 200 `Page<MemberDetail>` | — |
| API-17 POST /members | body: MemberCreateRequest | 201 `MemberDetail` | 409 DUPLICATE_CODE |
| API-18 PUT /members/{id} | body: MemberUpdateRequest（member_code は変更不可） | 200 `MemberDetail` | 404 |
| API-19 DELETE /members/{id} | — | 204（論理削除） | 404 |

管理 API のみ個人情報を返す（`MemberDetail`）。レジ用の API-05 は `MemberInfo`（氏名のみ）。

```ts
interface MemberDetail {
  id: number; member_code: string; name: string;
  phone: string | null; address: string | null;
  gender: "male" | "female" | "other" | null; birth_date: DateJST | null;
  age: number | null;   // birth_date から算出（I-4）
}
interface MemberCreateRequest {
  member_code: string; name: string;
  phone?: string | null; address?: string | null;
  gender?: "male" | "female" | "other" | null; birth_date?: DateJST | null;
}
type MemberUpdateRequest = Omit<MemberCreateRequest, "member_code">;
```

制約: member_code 1〜`MEMBER_CODE_MAX` 文字（半角英数字）、name 1〜50、phone 0〜20（数字と `-`）、address 0〜200、birth_date は過去日。

#### API-20〜23 値引き設定

| API | 入力 | 出力 | エラー |
|---|---|---|---|
| API-20 GET /discounts | page, size（q は商品コード・企画名） | 200 `Page<DiscountInfo>` | — |
| API-21 POST /discounts | body: DiscountCreateRequest | 201 `DiscountInfo` | 404 PRODUCT_NOT_FOUND, 422 INVALID_PERIOD |
| API-22 PUT /discounts/{id} | body: DiscountUpdateRequest | 200 `DiscountInfo` | 404, 422 |
| API-23 DELETE /discounts/{id} | — | 204（論理削除。確定済みの適用記録は残る） | 404 |

```ts
interface DiscountCreateRequest {
  product_code: string; name: string;
  start_date: DateJST; end_date: DateJST;
  discount_type: DiscountType; discount_value: number;
}
type DiscountUpdateRequest = Omit<DiscountCreateRequest, "product_code">;
```

制約: `start_date <= end_date`（違反は 422 INVALID_PERIOD）、percent は 0 < value ≤ 100、amount は 0 < value ≤ `PRICE_MAX`。

#### API-24 GET /health

入力なし。出力 200 `{ "status": "ok", "db": "ok" }`。DB へ `SELECT 1` を発行し、失敗時は 503 `{ "status": "degraded", "db": "error" }`。App Service のヘルスチェックに用いる（N-03）。

#### API-25 PUT /tax-rates/{id}　/　API-26 DELETE /tax-rates/{id}

管理画面の共通構成（一覧・登録・編集・削除。5.6）を税率にも揃える。ただし**適用開始日が本日以前の設定は修正・削除できない**（すでに取引が参照した可能性があるため。404 ではなく 422 INVALID_PERIOD）。

| API | 入力 | 出力 | エラー |
|---|---|---|---|
| API-25 PUT /tax-rates/{id} | body: rate、effective_from（本日以降。他の設定と重複不可） | 200 `TaxRateInfo` | 404 NOT_FOUND, 409 DUPLICATE_CODE, 422 INVALID_PERIOD |
| API-26 DELETE /tax-rates/{id} | — | 204。`deleted_at` を設定 | 404, 422 INVALID_PERIOD |

副作用: audit_logs（TAX_RATE_UPDATE / TAX_RATE_DELETE）。

#### API-27 POST /transactions/cancel

会計ポップアップのキャンセル（FR-10-6）を監査ログ（D-09-2「会計キャンセル」）に残すための記録専用 API。取引は保存しない。Frontend は応答を待たずに呼ぶ（失敗しても画面の動作に影響させない）。

| 入力（body） | 型 | 必須 | 制約 |
|---|---|---|---|
| idempotency_key | string | ○ | キャンセルした会計のキー（UUID v4） |
| total_incl_tax | Money | ○ | キャンセル時点の税込合計 |
| line_count | integer | ○ | 明細行数 |

出力 204。副作用: audit_logs（TRANSACTION_CANCEL, target_id = idempotency_key, detail = 合計と行数）。

```ts
interface TaxRateCreateRequest { rate: Rate; effective_from: DateJST }
type TaxRateUpdateRequest = TaxRateCreateRequest;                 // API-11, 25
interface CancelCheckoutRequest {
  idempotency_key: string; total_incl_tax: Money; line_count: number;   // API-27
}
```

税率の修正・削除の範囲は U-13 を参照。

### 7.6 BFF（Next.js Route Handler）の責務

| # | 責務 | 内容 |
|---|---|---|
| BFF-1 | 中継 | `/api/*` を受け、同じパスで FastAPI `/api/v1/*` へ転送する。ブラウザは FastAPI の URL を知らない |
| BFF-2 | 認証情報の変換 | ログイン成功時に `access_token` を HttpOnly・Secure・SameSite=Strict の Cookie に格納。以降の要求で Cookie → `Authorization: Bearer` に付け替える。ブラウザへ JWT 本体を返さない |
| BFF-3 | ログアウト | API-02 を呼んだ後、Cookie を失効させる |
| BFF-4 | 要求ID | `X-Request-Id` を生成して付与 |
| BFF-5 | 入力検証 | Zod スキーマ（7.4 の型と対応）で本文の**型・形式**を検証し、不正なら FastAPI へ送らず 400 を返す（12 章の多層防御）。数量などの業務範囲は検証せず Backend に委ねる（API-P8） |
| BFF-6 | 応答の透過 | FastAPI のステータスと本文をそのまま返す。500 系の本文は `INTERNAL_ERROR` / `SERVICE_UNAVAILABLE` / `GATEWAY_TIMEOUT` に正規化し、詳細を隠す（11.4） |

### 7.7 要件との対応

| 要件 | API |
|---|---|
| FR-01（ログイン・ログアウト） | API-01, 02, 03 |
| FR-02（会員読み込み） | API-05、API-06（値引き再計算） |
| FR-03（商品検索） | API-04 |
| FR-04, FR-05（購入リスト） | Frontend の状態管理＋API-06 |
| FR-06（値引き） | API-06（判定と算出）、API-20〜23（設定） |
| FR-07（消費税） | API-06, 09（適用）、API-10, 11（設定） |
| FR-08, FR-10（購入確定・現金決済・キャンセル） | API-07, 08, 27 |
| FR-09（マスタ管理） | API-10〜23, 25, 26 |
| N-02（データ保全） | API-07 の単一トランザクション、冪等性 |
| N-07（セキュリティ） | API-P3/P4、BFF-2、API-05 の情報最小化 |
| N-09（操作ログ） | 各 API の副作用として audit_logs |

---

## 8. シーケンス図

要求の経路はすべて「ブラウザ → BFF（Next.js Route Handler）→ FastAPI → MySQL」である（API-P1）。
BFF は Cookie の JWT を Bearer ヘッダへ付け替え、Zod で本文を検証してから中継する（7.6）。

### 8.1 ログイン（JWT 発行）

![シーケンス図: ログイン](sd_fig08_1_ログイン.png)

| 要点 | 内容 |
|---|---|
| 認証の主体 | FastAPI が bcrypt で照合し JWT を発行（SEC-01, SEC-02） |
| トークンの扱い | BFF が HttpOnly Cookie に格納。ブラウザは JWT 本体を受け取らない（SEC-03） |
| 失敗時 | ID 不存在とパスワード不一致を区別せず同じ 401（FR-01-4）。監査ログに attempted_login_id を残す |
| 関連 | API-01, SC-01, FR-01 |

### 8.2 バーコードスキャンから購入リスト追加

![シーケンス図: スキャン追加](sd_fig08_2_スキャン追加.png)

| 要点 | 内容 |
|---|---|
| 復号 | ブラウザ側の ZXing が JAN を商品コードに変換。カメラ映像はサーバへ送らない |
| 2 段の API | API-04 で商品の存在と名称・単価を得た後、API-06 で値引き・税・合計を算出。値引きの判定は Backend のみが行う |
| 自動追加 | スキャンは追加ボタンを経ず購入リストへ入る（FR-03-1）。手入力は名称・単価を表示した後に追加ボタン（FR-03-3） |
| 関連 | API-04, API-06, UC-05, UC-06 |

### 8.3 会員読み込みと値引きの遡り適用

![シーケンス図: 会員値引き](sd_fig08_3_会員値引き.png)

| 要点 | 内容 |
|---|---|
| カメラの共用 | 会員証スキャンボタンで一時的に会員証モードへ切り替え、1 件読むと商品モードへ戻る（FR-02-1） |
| 情報の最小化 | API-05 は氏名のみ返す（SEC-05, N-07 (4)） |
| 遡り適用 | 会員IDを得た直後に、登録済みの全行を含めて API-06 を呼び直す。Frontend は値引きを自前で判定しない（FR-06-7） |
| 関連 | API-05, API-06, UC-03 |

### 8.4 購入確定（Frontend 計算値と Backend 再計算の照合）

![シーケンス図: 購入確定](sd_fig08_4_購入確定.png)

| 要点 | 内容 |
|---|---|
| 照合 | Frontend が表示していた金額を送り、Backend がマスタから再計算して 1 円単位で比較。不一致は保存せず 409 と監査ログ（SEC-09） |
| 原子性 | transactions / transaction_items / discount_applications / idempotency_keys / audit_logs を 1 トランザクションで INSERT（N-02） |
| 冪等性 | 同じ Idempotency-Key の再送は保存済み応答を返す。通信断による二重売上を防ぐ |
| 保存値 | 写し列には Backend の再計算値を入れる。Frontend の送信値は照合にのみ使う |
| 関連 | API-07, UC-08, FR-08, FR-10 |

### 8.5 消費税率の変更（管理者）

![シーケンス図: 税率変更](sd_fig08_5_税率変更.png)

| 要点 | 内容 |
|---|---|
| 認可 | `require_role("admin")` を FastAPI 側で強制。cashier のトークンでは 403（SEC-05） |
| 有効化 | 追加した税率は、適用開始日以降の取引で API-06 / API-07 が自動的に採用する（6.5）。プログラムの変更は不要（FR-07-2） |
| 過去の取引 | tax_rate を写し取っているため影響を受けない（DR-1） |
| 関連 | API-11, UC-12, SC-05 |

---

## 9. クラス設計

### 9.1 Backend のレイヤ構成

| レイヤ | 責務 | 主な要素 | 禁止事項 |
|---|---|---|---|
| Router（FastAPI） | HTTP の受付、Pydantic による入出力の検証、認証・認可の依存関係 | `routers/auth.py`, `pricing.py`, `transactions.py`, `masters.py` | 業務ロジックを書かない |
| Service | 業務ロジック。金額計算、照合、監査ログ | `AuthService`, `PricingService`, `TransactionService`, `MasterService`, `AuditService` | SQL を直接書かない、HTTP を意識しない |
| Repository / UnitOfWork | SQLAlchemy Session の管理、トランザクション境界 | `UnitOfWork`, 各 Repository | 文字列連結による SQL |
| Model（SQLAlchemy ORM） | 6 章のテーブルと 1 対 1 | `Staff`, `Product`, `Member`, `Transaction`, … | — |
| Schema（Pydantic） | API の入出力型。7.4 の TypeScript 型と 1 対 1 | `LoginRequest`, `QuoteRequest`, `CommitRequest`, … | ORM モデルを直接返さない |

### 9.2 クラス図

![クラス図](sd_fig09_クラス図.png)

上段がドメインモデル（ORM。6 章のテーブルに対応）、下段がサービス層。破線は依存を示す。

### 9.3 サービスクラスの責務

| クラス | 責務 | 主なメソッド | 対応 |
|---|---|---|---|
| AuthService | 認証・トークン発行・検証、ロール判定 | `login()`, `verify_token()`, `require_role()`, `hash_password()` | FR-01, SEC-01〜05, API-01〜03 |
| PricingService | **金額計算の正本。** 有効税率・値引きの決定、明細と合計の算出。API-06 と API-07 の両方が同じインスタンスを使う。取引日（JST）は `Clock` 依存から得た UTC 時刻を変換して自身で作る（6.5） | `quote()`, `business_date(now_utc)`, `resolve_tax_rate()`, `resolve_discount()`, `calc_line()`, `calc_totals()` | FR-06, FR-07, 6.5, 7.5 計算規則, SEC-09 |
| Clock | 現在時刻（UTC）を返すだけの依存。本番は `datetime.now(timezone.utc)`、テストでは固定時刻を注入する | `now() -> datetime` | 6.5、日付境界テスト |
| TransactionService | 取引の確定。冪等性、再計算との照合、1 トランザクションでの保存。キャンセルの監査記録 | `commit()`, `verify_against_client()`, `get()`, `record_cancel()` | FR-08, FR-10, API-07, API-08, API-27, N-02 |
| MasterService | マスタ・設定の CRUD（論理削除）、重複・期間の検証。税率は適用開始前のもののみ修正・削除可 | `list_*()`, `create_*()`, `update_*()`, `soft_delete_*()`（products / members / tax_rates / discounts） | FR-09, API-10〜23, 25, 26, DR-5 |
| AuditService | 操作ログの記録。他サービスから呼ばれる | `record()` | N-09, D-09 |
| UnitOfWork | Session の生成とトランザクション境界。接続プールを保持 | `begin()`, `commit()`, `rollback()` | N-04, SEC-13 |

PricingService の計算は純粋関数として実装し、DB アクセス（税率・値引きの取得）と分離する。
これにより集計部分（規則 3〜5）は Frontend の `lib/pricing.ts` と同じ入力に対して同じ出力を返すことを単体テストで検証できる（12.6）。値引きの判定（規則 2）は Backend のみが持つ。

**日付境界のテスト（必須）**: `Clock` に固定時刻を注入し、`end_date = 9 月 9 日` の値引きについて、
UTC `2026-09-09T14:59:59`（JST 9 日 23:59:59）では適用され、UTC `2026-09-09T15:00:00`（JST 10 日 0:00:00）では
適用されないことを検証する。`start_date` についても同じ境界で逆の結果を検証する。この境界は日中の手動テストでは
踏めないため、自動テストに含める。

### 9.4 Pydantic スキーマと TypeScript 型の対応

| Pydantic（Backend） | TypeScript（Frontend / BFF, 7.4） | 用途 |
|---|---|---|
| `StaffInfo` | `StaffInfo` | API-01, 03 |
| `ProductInfo`, `ProductCreate`, `ProductUpdate` | `ProductInfo`, `ProductCreateRequest`, `ProductUpdateRequest` | API-04, 12〜14 |
| `MemberInfo`, `MemberDetail`, `MemberCreate`, `MemberUpdate` | 同名 | API-05, 16〜18 |
| `QuoteRequest`, `QuoteResult`, `QuoteLine`, `AppliedDiscount` | 同名 | API-06 |
| `CommitRequest`, `CommitItem`, `CommitResponse` | 同名 | API-07 |
| `TaxRateInfo`, `TaxRateCreate`, `TaxRateUpdate` | `TaxRateInfo`, `TaxRateCreateRequest`, `TaxRateUpdateRequest` | API-09〜11, 25, 26 |
| `CancelCheckoutRequest` | 同名 | API-27 |
| `DiscountInfo`, `DiscountCreate`, `DiscountUpdate` | 同名 | API-20〜22 |
| `ErrorResponse` | `ApiError` | 全 API |
| `Page[T]` | `Page<T>` | 一覧 API |

両者の整合は、FastAPI が生成する OpenAPI（開発環境のみ有効。SEC-10）から TypeScript 型を生成して
確認する（`openapi-typescript`）。手書きの 7.4 と差分が出た場合は 7.4 を正として修正する。

### 9.5 Frontend のクラス図

![Frontend クラス図](sd_fig09b_Frontendクラス図.png)

`CartStore` が状態（5.4）と操作を集約し、`BarcodeScanner` と `CheckoutDialog` はそこへ通知する。
`PricingView` は API-06 の結果から合計を再集計するだけで、値引きの判定は持たない。
BFF の `BffRoute` は `Schemas`（Zod）で検証してから FastAPI へ中継する。

### 9.6 Frontend のモジュール構成

| モジュール | 責務 | 対応 |
|---|---|---|
| `types/api.ts` | 7.4 の型定義 | API 全般 |
| `lib/schemas.ts` | Zod スキーマ（型と 1 対 1）。BFF と画面の両方で使う | SEC-11 |
| `lib/apiClient.ts` | `/api/*` への fetch ラッパ。`X-Request-Id` 付与、`ApiError` の型付き例外化 | 7.3 |
| `lib/pricing.ts` | API-06 の応答（値引き額・税率）を入力として小計・合計を再集計する（7.5 規則 3〜5 のみ）。値引きの判定は持たない。API-06 の応答と一致することをテストで確認 | SEC-09, FR-05-8 |
| `features/cart/store.ts` | 購入リスト・会員・状態（4.3）の管理。選択行、数量加算、上限判定 | FR-04, FR-05 |
| `features/scanner/useBarcodeScanner.ts` | ZXing のラッパ。商品モード／会員証モードの切替、連続読み取り、同一コードの連続検出の抑止 | FR-02-1, FR-03-1〜2 |
| `features/checkout/` | 会計ポップアップ、Idempotency-Key の生成と保持、409 時の表示差し替え | FR-10 |
| `app/api/**/route.ts` | BFF（7.6）。Cookie ⇄ Bearer、Zod 検証、FastAPI への中継 | BFF-1〜6 |
| `app/(pos)/`, `app/(admin)/` | 画面（5 章）。`(admin)` は role=admin のときのみ到達可能 | SC-01〜06 |

---

## 10. 設定・制約値

本章の定数は Backend（`app/core/config.py`、pydantic-settings）と Frontend（`lib/constants.ts`）の
両方で用いる。両者の値がずれると照合（SEC-09）が失敗するため、**`shared/limits.json` を単一の正本**とする。
Backend は起動時に、Frontend はビルド時にこの JSON をそのまま読み込み、値をコードに書き写さない。
CI では JSON のスキーマ検査（必須キーと型）を行い、Backend・Frontend のテストが同じ JSON を参照していることを確認する（U-10）。

### 10.1 入力値・数量の下限・上限

| 定数 | 値 | 適用箇所 | 根拠 |
|---|---|---|---|
| QTY_MIN | 1 | 明細の数量 | FR-05-6, FR-05-7 |
| QTY_MAX | 99 | 明細の数量（数量変更・スキャン加算の両方） | FR-05-6, FR-05-9 |
| CART_MAX_LINES | 100 | 1 取引の明細行数（商品の種類数） | 本書で決定。A-6 の店舗規模で 1 会計に 100 種類を超えることは想定しない。要求サイズの上限にもなる |
| PRODUCT_CODE_LENGTH | 13 | 商品コードの桁数（数字のみ `^[0-9]{13}$`） | Q-5（JAN / EAN-13） |
| MEMBER_CODE_MIN / MAX | 1 / 32 | 会員ID（`^[A-Za-z0-9]{1,32}$`） | Q-5（CODE128）、D-03-1 |
| LOGIN_ID_MAX | 32 | 担当者ID（`^[A-Za-z0-9_-]{1,32}$`） | D-01-1 |
| PASSWORD_MIN / MAX | 8 / 64 | パスワード | Q-6 |
| PRODUCT_NAME_MAX | 100 | 商品名称 | D-02-2 |
| PERSON_NAME_MAX | 50 | 担当者・会員の氏名 | D-01-3, D-03-2 |
| PHONE_MAX | 20 | 電話番号（`^[0-9-]{0,20}$`） | D-03-3 |
| ADDRESS_MAX | 200 | 住所 | D-03-4 |
| DISCOUNT_NAME_MAX | 100 | 値引き企画名 | 6.3 discounts.name |
| PRICE_MIN / PRICE_MAX | 0 / 9,999,999 | 単価（円）、金額値引きの値 | INT の範囲内で十分な上限。小売の単価として現実的 |
| TENDER_MIN / TENDER_MAX | 0 / 9,999,999 | 預かり金額 | 同上。合計金額の理論上限 = PRICE_MAX × QTY_MAX × CART_MAX_LINES は超え得るが、現実の会計では発生しない（発生時は 422） |
| TAX_RATE_MIN / MAX | 0.00 / 100.00 | 消費税率（小数 2 桁） | D-06-1 |
| DISCOUNT_PERCENT_MIN / MAX | 0.01 / 100.00 | 割合値引き | D-07-6 |
| SEARCH_Q_MAX | 50 | 一覧検索の文字列長 | 7.3 |
| PAGE_SIZE_DEFAULT / MAX | 50 / 100 | 一覧のページサイズ | 7.3 |
| BODY_MAX_BYTES | 1,048,576 | 要求本文の上限（BFF・FastAPI） | 12.9 |

### 10.2 金額計算の確定値

要件定義書 9.3 の仮定（Q-1〜Q-4）を設定値として確定する。値を変える場合はここを変えるだけで、
Backend と Frontend の計算が同時に切り替わる。

| 定数 | 値 | 意味 | 元の仮定 |
|---|---|---|---|
| TAX_ROUNDING | floor | 消費税額の端数は切り捨て | Q-1 |
| TAX_CALC_UNIT | transaction | 税は取引合計に対して 1 回計算（明細ごとではない） | Q-1 |
| DISCOUNT_ROUNDING | floor | 割合値引き額の端数は切り捨て（顧客有利） | Q-2 |
| DISCOUNT_BEFORE_TAX | true | 値引き後の金額に課税する | Q-3 |
| DISCOUNT_SELECTION | max_amount | 同一商品に複数の値引きが該当する場合、値引き額が最大の 1 件のみ適用 | Q-4 |
| DISCOUNT_CAP_TO_LINE | true | 値引き額は行の金額（単価 × 数量）を超えない | 7.5 API-06 規則 2 |

### 10.3 認証・セッション

| 定数 | 値 | 用途 | 根拠 |
|---|---|---|---|
| JWT_ALG | HS256 | 署名アルゴリズム | SEC-02 |
| JWT_TTL_HOURS | 8 | トークン有効期間（1 シフト） | SEC-02 |
| SESSION_COOKIE_NAME | pos_session | BFF が発行する Cookie 名 | SEC-03 |
| BCRYPT_COST | 12 | ハッシュのコスト係数 | SEC-01 |
| LOGIN_RATE_LIMIT | 10 回 / 60 秒（login_id 単位・IP 単位） | 総当たり対策 | SEC-04 |
| IDEMPOTENCY_TTL_HOURS | 24 | 冪等キーの保持期間 | 7.3 |

### 10.4 タイムアウト・接続・性能

| 定数 | 値 | 用途 | 根拠 |
|---|---|---|---|
| BFF_UPSTREAM_TIMEOUT_MS | 5,000 | BFF → FastAPI の応答待ち。超過は 504 | 要件定義書 6.1 の目標（2 秒以内）に対する余裕 |
| MEMBER_SCAN_TIMEOUT_MS | 10,000 | 会員証モードで読み取れないまま経過したら商品モードへ自動復帰 | FR-02-1 の復帰規則を補完 |
| DB_POOL_SIZE / DB_MAX_OVERFLOW | 5 / 5 | SQLAlchemy 接続プール | N-04。B1ms の接続数上限に収める |
| DB_POOL_RECYCLE_SEC | 1,800 | 接続の再生成間隔 | MySQL 側のアイドル切断より短くする |
| DB_POOL_PRE_PING | true | 取得時に生存確認 | 切断済み接続の再利用を防ぐ |
| SCAN_DEBOUNCE_MS | 1,500 | 同一バーコードの連続検出を無視する時間 | カメラが同じコードを毎フレーム読むため（9.5） |
| QUOTE_DEBOUNCE_MS | 200 | 数量の連打時に API-06 の呼び出しをまとめる | 要件定義書 6.1 の応答速度、無駄な要求の抑制 |
| BUSINESS_TIMEZONE | Asia/Tokyo | 取引日（税率・値引きの適用判定に用いる日付）の基準。Backend が UTC 現在時刻をこの TZ へ変換して日付を作る（6.5） | DB-6, 6.5 |
| APP_TIMEZONE_DISPLAY | Asia/Tokyo | 画面表示の日時の基準（BUSINESS_TIMEZONE とは役割を分ける） | 5.7 |

### 10.5 環境変数一覧

秘密情報（★）は App Service のアプリケーション設定に置き、Key Vault 参照で注入する。リポジトリには置かない（12.9）。

| 変数 | 側 | 内容 | 秘密 |
|---|---|---|---|
| APP_ENV | 両方 | `development` / `production`。Swagger の表示可否（SEC-10）、ログレベルを切り替える | |
| API_UPSTREAM_URL | BFF | FastAPI のベース URL（例 `https://pos-api.azurewebsites.net`） | |
| BFF_SHARED_KEY | 両方 | `X-BFF-Key` の値 | ★ |
| JWT_SECRET | Backend | JWT 署名鍵（32 バイト以上の乱数） | ★ |
| DATABASE_URL | Backend | `mysql+pymysql://user:pass@host/db?charset=utf8mb4&ssl=true` | ★ |
| CORS_ALLOW_ORIGINS | Backend | Next.js のオリジン（カンマ区切り） | |
| LOG_LEVEL | 両方 | `INFO`（本番）/ `DEBUG`（開発） | |
| NEXT_PUBLIC_APP_NAME | Frontend | 画面表示用の名称 | |

`NEXT_PUBLIC_` で始まる変数はブラウザに露出する。秘密情報にこの接頭辞を付けない。

### 10.6 要件との対応

| 要件 | 設定 |
|---|---|
| FR-05-6, FR-05-7, FR-05-9 | QTY_MIN / QTY_MAX |
| FR-07-2 | 税率はデータ（tax_rates）で保持。丸め規則のみ設定値 |
| FR-06-6 | 値引きはデータ（discounts）で保持。選択・丸め規則のみ設定値 |
| N-03, N-04 | DB_POOL_*, BFF_UPSTREAM_TIMEOUT_MS |
| N-07 | JWT_*, BCRYPT_COST, LOGIN_RATE_LIMIT, 秘密情報の置き場所 |
| Q-1〜Q-6（要件定義書 9.3） | 10.2 の確定値、PASSWORD_MIN / MAX、PRODUCT_CODE_LENGTH、MEMBER_CODE_MAX |

---

## 11. エラー処理

### 11.1 方針

| # | 方針 | 内容 |
|---|---|---|
| ERR-1 | 2 段の検証 | 入力は BFF（Zod）と FastAPI（Pydantic）の両方で検証する。BFF で弾けるものはサーバへ送らない。ただし FastAPI は BFF を信頼せず、単独でも同じ判定を行う（SEC-11, SEC-12） |
| ERR-2 | 共通形式 | すべてのエラーは 7.3 の形式 `{ error: { code, message, details } }` で返す。Zod のエラーも同形式に変換する |
| ERR-3 | コードで判定、文言は Frontend | Frontend は `code` を見て動作を決め、表示文言は 11.2 の辞書から引く。サーバの `message` は開発者向けで、画面にはそのまま出さない |
| ERR-4 | 表示場所 | POS 画面のエラー・通知は共通メッセージ領域（SC-02-04）に 1 件ずつ表示し、次の操作か 5 秒で消える。管理画面のフォーム検証エラーは項目の横に表示する |
| ERR-5 | 詳細の隠蔽 | 500 系はスタックトレース・SQL・内部パスを返さない。`X-Request-Id` を画面に表示し、問い合わせ時にログと突き合わせる |
| ERR-6 | 記録 | 業務上の失敗（認証失敗・照合不一致）は audit_logs へ、技術的な例外はアプリケーションログへ記録する（11.5） |
| ERR-7 | 状態の保護 | エラー発生時に購入リストの内容を失わない。会計中のエラーは checkout 状態に留まり、キャンセルで editing へ戻れる（4.3） |

### 11.2 エラーコード一覧

| コード | HTTP | 発生 API | 条件 | 画面の文言 | 画面の動作 | 監査ログ |
|---|---|---|---|---|---|---|
| AUTH_INVALID_CREDENTIALS | 401 | API-01 | ID 不存在またはパスワード不一致（区別しない） | 担当者IDまたはパスワードが違います | SC-01 に留まる（FR-01-4） | LOGIN_FAILED |
| AUTH_REQUIRED | 401 | 全 API | Cookie なし、JWT 不正・期限切れ | セッションが切れました。再度ログインしてください | SC-01 へ遷移。購入リストは破棄 | — |
| FORBIDDEN | 403 | 管理 API、X-BFF-Key 不一致 | role 不足、または BFF 以外からの要求 | この操作を行う権限がありません | 操作を中止 | — |
| VALIDATION_ERROR | 400 | 全 API | 型・形式・桁数の不正（Zod / Pydantic） | 入力内容に誤りがあります | `details.fields[]` を項目の横に表示（管理画面）／共通領域（POS） | — |
| PRODUCT_NOT_FOUND | 404 | API-04, 06, 07, 21 | 商品コードが未登録または論理削除済み | 商品がマスタ未登録です | リストは変えない（FR-03-5）。API-07 なら会計を中止し該当行を強調 | — |
| MEMBER_NOT_FOUND | 404 | API-05, 06, 07 | 会員IDが未登録または論理削除済み | 該当する会員が見つかりません。会員なしで続けるか、もう一度読み込んでください | 会員IDは未設定のまま（FR-02-6） | — |
| NOT_FOUND | 404 | 管理 API, API-08 | 指定 id が存在しない | 対象が見つかりません | 一覧を再取得 | — |
| QUANTITY_OUT_OF_RANGE | 422 | API-06, 07 | 数量が QTY_MIN〜QTY_MAX 外 | 数量は 1〜99 で指定してください | 直前の数量を維持（FR-05-9） | — |
| CART_EMPTY | 422 | API-07 | 明細 0 行 | 商品が登録されていません | 会計を開かない（FR-08-6） | — |
| CART_TOO_MANY_LINES | 422 | API-06, 07 | 明細が CART_MAX_LINES 超 | 1 回の会計で登録できる商品は 100 種類までです | 追加を拒否 | — |
| TAX_RATE_NOT_CONFIGURED | 422 | API-06, 07, 09 | 本日有効な税率がない | 消費税率が設定されていません。管理者に連絡してください | 会計不可 | — |
| INSUFFICIENT_TENDER | 422 | API-07 | 預かり金額 < 税込合計 | 預かり金額が不足しています（不足 n 円） | 確定ボタン無効、不足額表示（FR-10-3） | — |
| INVALID_PERIOD | 422 | API-11, 21, 22, 25, 26 | end_date < start_date、本日より前の effective_from、または適用開始日が本日以前の税率設定への修正・削除 | 適用終了日は開始日以降にしてください／適用開始日は本日以降にしてください／この税率は適用が始まっているため変更できません | 項目の横に表示（削除時は共通領域） | — |
| PRICE_MISMATCH | 409 | API-07 | Frontend の金額と Backend 再計算が不一致 | 金額が更新されました。内容を確認して再度確定してください | `details.server` で表示を差し替え、checkout に留まる（SEC-09） | TRANSACTION_COMMIT failure |
| DUPLICATE_REQUEST | 409 | API-07 | 同じ Idempotency-Key で本文が異なる | 同じ会計が処理中です。画面を更新してください | 会計を閉じ、API-08 で状態を確認 | — |
| DUPLICATE_CODE | 409 | API-11, 13, 17, 25 | UNIQUE 制約違反（商品コード・会員ID・税率の適用開始日） | 同じコード（日付）が既に登録されています | 項目の横に表示 | — |
| RATE_LIMITED | 429 | API-01（BFF） | LOGIN_RATE_LIMIT 超過 | 試行回数が多すぎます。1 分ほど待ってからお試しください | SC-01 に留まる | — |
| PAYLOAD_TOO_LARGE | 413 | 全 API | 本文が BODY_MAX_BYTES 超 | 送信データが大きすぎます | 操作を中止 | — |
| GATEWAY_TIMEOUT | 504 | 全 API（BFF） | FastAPI が BFF_UPSTREAM_TIMEOUT_MS 内に応答しない | サーバの応答がありません。しばらく待って再試行してください | API-07 なら同じ Idempotency-Key で再送可 | — |
| SERVICE_UNAVAILABLE | 503 | 全 API | DB 接続不可（API-24 も同値） | サービスに接続できません。しばらく待ってから再試行してください | 画面上部に継続表示 | — |
| INTERNAL_ERROR | 500 | 全 API | 想定外の例外 | 処理に失敗しました。もう一度お試しください（問い合わせ番号: {request_id}） | 操作を中止 | — |

Frontend のみで発生するもの（サーバに送らない）:

| コード | 条件 | 文言 | 動作 |
|---|---|---|---|
| CAMERA_PERMISSION_DENIED | ブラウザがカメラ利用を拒否 | カメラを使用できません。手入力で商品コードを登録してください | プレビュー領域に案内を表示。手入力（FR-03-3）は使える |
| CAMERA_UNAVAILABLE | カメラが存在しない、HTTPS でない | カメラが利用できない環境です | 同上。N-10 の localhost 例外を開発時の案内に含める |
| MEMBER_ALREADY_SET | 会員IDが設定済みで再読み込み | 会員は既に読み込まれています | 2 件目を無視（FR-02-8） |

### 11.3 Frontend の事前チェック

サーバへ送る前に Frontend で防ぐもの。**サーバ側の検証を省略する理由にはしない**（ERR-1）。

| チェック | 該当 | 動作 |
|---|---|---|
| 数量 1〜99 | 数量変更 UI、スキャン加算 | 0・空欄・99 超はいずれも受け付けず「数量は 1〜99 で指定してください（0 にする場合は削除）」を表示し、直前の数量を維持（FR-05-7, FR-05-9） |
| 商品モードで 13 桁の数字以外を読み取った | スキャン | API-04 を呼ばず「商品がマスタ未登録です」を表示（FR-02-1） |
| リストが空 | 購入ボタン | 押下時に CART_EMPTY の文言を表示し、会計を開かない |
| 預かり金額 ≥ 税込合計 | 確定ボタン | 不足中は無効化し、不足額を表示 |
| 商品コード 13 桁の数字 | 手入力の読み込み | 満たさない場合は API-04 を呼ばず文言表示 |
| 会員ID 1〜32 の英数字 | 手入力の読み込み | 空欄のまま読み込みボタンを押した場合は検証せず会員なしで進む（FR-02-7）。文字が入っていて形式を満たさない場合のみ文言表示 |
| 同一バーコードの連続検出 | スキャン | SCAN_DEBOUNCE_MS 内の同一コードは無視 |

### 11.4 例外処理の実装方針

**FastAPI**

| 例外 | 変換先 |
|---|---|
| `AppError(code, status, message, details)`（業務例外。サービス層が送出） | そのまま共通形式へ |
| `RequestValidationError`（Pydantic。型・形式の違反） | 400 VALIDATION_ERROR。`details.fields = [{name, reason}]` |
| `AppError`（サービス層の業務範囲違反。数量・行数・預かり金額・期間） | 422 と 11.2 の業務コード（QUANTITY_OUT_OF_RANGE など） |
| `sqlalchemy.exc.IntegrityError`（UNIQUE 違反） | 409 DUPLICATE_CODE |
| `sqlalchemy.exc.OperationalError`（接続断） | 503 SERVICE_UNAVAILABLE。接続はプールが再生成 |
| その他の例外 | 500 INTERNAL_ERROR。スタックトレースは request_id 付きでログのみ |

API-07 では、`BEGIN` 以降の例外はすべてロールバックし、部分的な取引を残さない（N-02）。

**BFF（Next.js Route Handler）**

| 事象 | 変換先 |
|---|---|
| Zod 検証失敗 | 400 VALIDATION_ERROR（FastAPI と同じ形式） |
| Cookie なし・期限切れ（`exp` を BFF でも確認） | 401 AUTH_REQUIRED。FastAPI へ送らない |
| FastAPI が応答しない | 504 GATEWAY_TIMEOUT |
| FastAPI の 5xx | 本文を `INTERNAL_ERROR` / `SERVICE_UNAVAILABLE` に正規化し、詳細を落とす（BFF-6） |
| FastAPI の 4xx | 本文をそのまま透過 |

### 11.5 ログ出力

| 種別 | 置き場所 | 内容 | 含めないもの |
|---|---|---|---|
| アプリケーションログ | App Service のログストリーム（stdout、JSON 1 行） | 時刻、level、request_id、method、path、status、duration_ms、staff_id、code | パスワード、JWT、会員の電話番号・住所、SQL 文、スタックトレース（ERROR 時のみ別行で出力） |
| 操作ログ（監査） | audit_logs テーブル（D-09） | 誰が・いつ・何を・結果 | 同上 |
| アクセスログ | App Service の HTTP ログ | 標準のまま | — |

保持期間: アプリケーションログは App Service の設定で 30 日、audit_logs は N-09 のとおり 90 日以上。

### 11.6 障害時の振る舞い

| 事象 | システムの振る舞い | 担当者の対応 |
|---|---|---|
| DB に接続できない | API-24 が 503。全 API が SERVICE_UNAVAILABLE。画面上部に継続表示 | 復旧を待つ。購入リストはブラウザ内に保持される |
| 確定要求の応答が届かない | Frontend は同じ Idempotency-Key で最大 2 回再送。それでも不明なら API-08 で確認を促す | 二重登録は起きない |
| FastAPI の再起動（デプロイ等） | App Service のヘルスチェックが API-24 を監視し、復帰まで要求を回さない | — |
| カメラが使えない | 手入力に切り替え可能 | FR-03-3 の手順で登録 |
| 税率が未設定 | 会計不可（TAX_RATE_NOT_CONFIGURED） | 管理者が SC-05 で登録 |

### 11.7 要件との対応

| 要件 | エラー処理 |
|---|---|
| FR-01-4 | AUTH_INVALID_CREDENTIALS（区別しない文言） |
| FR-02-6, FR-02-8 | MEMBER_NOT_FOUND, MEMBER_ALREADY_SET |
| FR-03-5 | PRODUCT_NOT_FOUND |
| FR-05-6〜9 | QUANTITY_OUT_OF_RANGE、11.3 の事前チェック |
| FR-08-6 | CART_EMPTY |
| FR-10-3 | INSUFFICIENT_TENDER |
| N-02 | API-07 のロールバック、冪等再送 |
| N-07 | 詳細の隠蔽（ERR-5）、ログの衛生（11.5） |
| N-09 | audit_logs との役割分担（ERR-6） |
| SC-02-04 | ERR-4 の表示規則 |

---

## 12. セキュリティ設計

要件定義書の N-07（セキュリティ）と、課題で指定された対策項目を設計に落とす。
対策には SEC 番号を付け、12.11 で指定項目との対応を示す。

### 12.1 守るもの・脅威・対策の全体像

| 資産 | 脅威 | 対策 | SEC |
|---|---|---|---|
| 担当者の認証情報 | パスワード漏えい、なりすまし | bcrypt ハッシュ、JWT の HttpOnly Cookie 保持、汎用的なエラー文言、ログイン試行の制限 | SEC-01〜04 |
| 管理機能（税率・単価） | 権限のない者による改ざん | role による認可を FastAPI 側で強制、管理画面の表示制御は補助 | SEC-05 |
| 取引金額 | Frontend の改ざんによる不正値引き | Backend で全額を再計算し照合。不一致は拒否して記録 | SEC-09 |
| 会員の個人情報 | 過剰な露出 | レジ API は氏名のみ返す。管理 API は admin のみ。ログに個人情報を出さない | SEC-05, SEC-14 |
| データベース | SQL インジェクション、不正接続 | 型検証（TypeScript/Zod・Pydantic）＋ ORM のバインド変数、最小権限の DB ユーザ、接続元の限定（ファイアウォール・TLS） | SEC-11〜13 |
| バックエンド API | 直接アクセス、CORS 悪用、情報漏えい | BFF 経由に限定、CORS を BFF オリジンのみ、Swagger 非表示、エラー詳細の隠蔽 | SEC-06〜08, SEC-10 |
| 依存ライブラリ | 既知の脆弱性 | バージョン固定、`npm audit` / `pip-audit`、定期更新 | SEC-15 |

### 12.2 認証（ログイン・JWT）

| # | 対策 | 内容 |
|---|---|---|
| SEC-01 | パスワードの保護 | bcrypt（コスト `BCRYPT_COST` = 12）でハッシュ化し `staff.password_hash` に保持。平文・可逆暗号は用いない（D-01-2） |
| SEC-02 | JWT の発行 | API-01 成功時に FastAPI が HS256 で署名。クレーム: `sub`（staff.id）、`login_id`、`role`、`iat`、`exp`（`JWT_TTL_HOURS` = 8 時間後）、`jti`（UUID）。署名鍵は App Service のアプリケーション設定（Key Vault 参照）から読み、リポジトリに置かない |
| SEC-03 | JWT の保持 | BFF が `Set-Cookie: pos_session=<JWT>; HttpOnly; Secure; SameSite=Strict; Path=/` で保持。JavaScript から読めないため XSS で盗まれない。`localStorage` は使わない。ブラウザへ JWT 本体を返さない（BFF-2）。Path を `/` とするのは、5.2 の `middleware.ts` が `/pos` `/admin` へのページ要求でも Cookie を読んでガードするため |
| SEC-04 | ログイン試行の制限 | BFF で `login_id` ごと・IP ごとに `LOGIN_RATE_LIMIT`（10 回／分）を超える試行を 429 で拒否。失敗理由は「ID またはパスワードが違います」に統一し、ID の存在を推測させない（FR-01-4）。失敗は audit_logs（LOGIN_FAILED）に記録（D-09） |
| — | 有効期限と失効 | 8 時間で自動失効（1 シフト）。リフレッシュトークンは持たない。ログアウトは Cookie 削除＋監査ログ。サーバ側の失効リストは持たない（14 章に記録。必要になれば `jti` を Redis 等で管理） |

### 12.3 認可（RBAC）

| # | 対策 | 内容 |
|---|---|---|
| SEC-05 | ロールによる認可 | FastAPI の依存関係 `require_role("cashier")` / `require_role("admin")` を各ルータに付与。`admin` は `cashier` の権限を包含する。JWT の `role` に加え、要求ごとに `staff` を DB で参照し `deleted_at IS NULL` を確認する（削除された担当者のトークンを無効化）。Frontend の「管理画面ボタンを管理者のみ表示」（SC-02-02）は利便性のためで、防御は API 側で行う |

### 12.4 BFF（リバースプロキシ）

| # | 対策 | 内容 |
|---|---|---|
| SEC-06 | ブラウザと API の分離 | ブラウザは Next.js のオリジンとのみ通信する。FastAPI の URL・ポートはブラウザに露出しない（7.6 BFF-1） |
| SEC-07 | API への到達経路の限定 | FastAPI（App Service）に**アクセス制限**を設定し、Next.js（App Service）の送信 IP からの要求のみ許可する。加えて BFF は共有秘密ヘッダ `X-BFF-Key` を付け、FastAPI は一致しない要求を 403 で拒否する（多層防御。ネットワーク制限が使えない環境でも最低限の防御が残る） |
| — | CSRF | Cookie は `SameSite=Strict` のため他サイトからの要求に付かない。さらに BFF は状態を変える要求（POST/PUT/DELETE）で `Origin` ヘッダが自オリジンと一致することを確認する |

### 12.5 CORS

| # | 対策 | 内容 |
|---|---|---|
| SEC-08 | FastAPI の CORS | `CORSMiddleware` の `allow_origins` を Next.js のオリジン（例 `https://pos-web.azurewebsites.net`）のみとし、`*` は使わない。`allow_credentials=False`、`allow_methods` は使用する 4 メソッド、`allow_headers` は `Authorization, Content-Type, Idempotency-Key, X-Request-Id, X-BFF-Key` に限定。設計上ブラウザが FastAPI を直接呼ぶことはないため、この設定は「誤って直接呼ばれても他オリジンからは拒否される」保険である |
| — | Next.js 側 | ブラウザと BFF は同一オリジンのため CORS は発生しない。`next.config` で他オリジンを許可しない |

### 12.6 金額の二重計算と照合

| # | 対策 | 内容 |
|---|---|---|
| SEC-09 | Backend を正本とする再計算 | 値引きの判定・税率の決定・全金額の算出は API-06 の規則（7.5）に従い Backend が行う。Frontend は API-06 が返した値引き額と税率から合計を再集計して表示するが、確定時（API-07）には Frontend の値を送り、Backend がマスタから**独立に再計算**して 1 円単位で照合する。不一致は 409 PRICE_MISMATCH とし、保存しない。不一致の発生は audit_logs（TRANSACTION_COMMIT, result=failure, detail=PRICE_MISMATCH）に記録し、改ざんの試行や Frontend の不具合を追跡できるようにする |
| — | 保存値 | transaction_items・discount_applications に写し取る値は Backend の再計算値であり、Frontend の送信値ではない |

### 12.7 API ドキュメントの非公開

| # | 対策 | 内容 |
|---|---|---|
| SEC-10 | Swagger / ReDoc / OpenAPI の無効化 | 本番では `FastAPI(docs_url=None, redoc_url=None, openapi_url=None)`。環境変数 `APP_ENV=development` のときのみ有効にする。API 一覧を攻撃者に与えない |

### 12.8 SQL インジェクション対策

| # | 層 | 対策 |
|---|---|---|
| SEC-11 | Frontend / BFF（TypeScript） | 7.4 の型に対応する **Zod スキーマ**で本文を検証（BFF-5）。商品コードは `^[0-9]{13}$`、会員IDは `^[A-Za-z0-9]{1,32}$`、数量は整数、のように**型・文字種・長さ**を制限し、SQL の断片になり得る文字列を API へ送らない。数量 1〜99 などの業務範囲は BFF では弾かず Backend のサービス層に委ねる（API-P8。422 の業務コードを到達可能にするため） |
| SEC-12 | Backend（Pydantic） | 全入力を Pydantic モデルで再検証（型、`constr(pattern=...)` による文字種・桁数）。BFF を経由しない要求にも同じ検証が効く。数量・行数などの業務範囲はサービス層で 10 章の定数と照合し 422 を返す（API-P8） |
| SEC-13 | データアクセス（ORM） | **SQLAlchemy 2.x** の ORM / Core を用い、値は常にバインド変数で渡す。文字列連結・f-string で SQL を組み立てることを禁止（コードレビュー項目）。`q` の部分一致検索は `%` `_` をエスケープしてから `LIKE` に渡す。生 SQL は Alembic のマイグレーションに限定 |
| — | DB 権限 | アプリ用 DB ユーザは対象スキーマの SELECT / INSERT / UPDATE のみ。DELETE は `idempotency_keys` に限り許可（期限切れキーの削除。U-6）。DDL 不可。マイグレーションは別ユーザで実行 |
| — | エラー隠蔽 | DB のエラー文言をクライアントへ返さない（BFF-6。INTERNAL_ERROR / SERVICE_UNAVAILABLE に正規化）。SQL 文はログに残さない |

### 12.9 その他の基本対策

| 対策 | 内容 |
|---|---|
| HTTPS 強制 | 両 App Service で「HTTPS Only」と TLS 1.2 以上。HTTP は 301 で HTTPS へ。カメラ API の前提でもある（N-10） |
| セキュリティヘッダ | Next.js から `Strict-Transport-Security`、`X-Content-Type-Options: nosniff`、`Content-Security-Policy: default-src 'self'; frame-ancestors 'none'`（ZXing は自ホストから配信）、`Referrer-Policy: no-referrer` を返す |
| XSS | React の既定エスケープに従い `dangerouslySetInnerHTML` を使わない。商品名・会員名は表示時にそのまま文字列として描画 |
| 秘密情報 | JWT 署名鍵、DB 接続文字列、`X-BFF-Key` は App Service のアプリケーション設定（Key Vault 参照）に置く。`.env` はリポジトリに含めない（`.gitignore`） |
| 要求サイズ | BFF・FastAPI とも本文 `BODY_MAX_BYTES`（1 MB）を超える要求を 413 で拒否 |
| ログの衛生 | パスワード・JWT・会員の電話番号・住所をログに出さない。`X-Request-Id` で要求を追跡（N-09） |
| Cookie の範囲 | `Path=/`（SEC-03）。静的資産（`/_next/static`）への送信は避けられないが、HttpOnly のため漏えい面は増えない |
| SEC-14 個人情報の最小化 | レジ用 API（API-05）は会員の氏名のみ返し、電話番号・住所・生年月日は管理 API（admin のみ）でしか返さない。POS 画面にも表示しない（5.7）。ログに出さない（11.5） |

### 12.10 依存ライブラリの脆弱性管理

**採用バージョン（確認日 2026-09-07。npm / PyPI レジストリを照会）**

| 区分 | ライブラリ | 採用 | 最新安定版（確認時） | 備考 |
|---|---|---|---|---|
| Frontend | Next.js | 16.3.x | 16.3.4 | App Router。セキュリティ修正が頻繁なためマイナー内で追従 |
| Frontend | React / React DOM | 19.2.x | 19.2.8 | Next.js 16 の対応版 |
| Frontend | TypeScript | 5.9.x（確認時 5.9.3） | 7.0.2 | 7.0 は新実装のコンパイラ（2026 年公開）。Next.js・ESLint との互換を確認してから移行。着手時は 5.9 を採用 |
| Frontend | Zod | 4.5.x | 4.5.4 | BFF・画面の入力検証 |
| Frontend | @zxing/library | 0.23.x | 0.23.0（2026-04） | コミュニティ製。更新頻度が低いため、リリースの有無を月次で確認。代替候補: ブラウザ標準 BarcodeDetector（Safari 非対応のため現時点では不採用。N-10） |
| Backend | Python | 3.11 | — | 開発環境 3.11.9。App Service の Python 3.11 ランタイム |
| Backend | FastAPI | 0.141.x | 0.141.1（2026-07） | |
| Backend | Uvicorn | 0.52.x | 0.52.4（2026-08） | ASGI サーバ。App Service では gunicorn 経由で起動 |
| Backend | SQLAlchemy | 2.0.x | 2.0.52（2026-08） | ORM。接続プール（N-04） |
| Backend | Pydantic / pydantic-settings | 2.13.x / 2.15.x | 2.13.5 / 2.15.0 | 入力検証・設定読み込み |
| Backend | PyMySQL | 1.2.x | 1.2.0（2026-05） | MySQL ドライバ（純 Python。ビルド不要） |
| Backend | PyJWT | 2.13.x | 2.13.0（2026-05） | JWT の署名・検証 |
| Backend | bcrypt | 5.0.x | 5.0.0（2025-09） | パスワードハッシュ |
| Backend | Alembic | 1.19.x | 1.19.2（2026-09） | スキーマ移行 |
| 検査 | pip-audit | 2.10.x | 2.10.1 | Python 依存の脆弱性検査 |
| 実行環境 | Node.js | 24 LTS | — | 開発環境 v24.15.0。App Service の Node 24 ランタイム |

**既知の脆弱性の照会結果（OSV.dev、2026-09-07）**

採用バージョンについて、OSV（Open Source Vulnerabilities。GitHub Advisory / PyPA Advisory 等を統合した公開データベース）に
パッケージ名とバージョンで照会した。

| ライブラリ | 照会バージョン | 該当する既知の脆弱性 |
|---|---|---|
| next 16.3.4 / react 19.2.8 / react-dom 19.2.8 / zod 4.5.4 / @zxing/library 0.23.0 | 左記 | **0 件** |
| fastapi 0.141.1 / uvicorn 0.52.4 / sqlalchemy 2.0.52 / pydantic 2.13.5 / pydantic-settings 2.15.0 / pymysql 1.2.0 / pyjwt 2.13.0 / bcrypt 5.0.0 / alembic 1.19.2 | 左記 | **0 件** |

TypeScript 5.9.3 は型チェッカーであり実行時コードに含まれないため照会対象外。
この結果は照会時点のものであり、SEC-15 の継続的な検査（`npm audit` / `pip-audit`）で更新する。

**運用ルール**

| # | ルール | 内容 |
|---|---|---|
| SEC-15 | バージョン固定 | `package-lock.json` をコミットし `npm ci` で再現。Python は `requirements.txt` に `==` で固定（`pip-compile` で生成） |
| SEC-15 | 継続的な検査 | CI（GitHub Actions）で `npm audit --audit-level=high` と `pip-audit` を実行し、High 以上があれば失敗させる。Dependabot を有効にし、セキュリティ更新は週次、通常更新は月次でまとめて取り込む |
| SEC-15 | 更新の判断 | パッチ・マイナーは CI 通過で取り込む。メジャー（Next.js 17、TypeScript 7 など）は互換性を検証してから。@zxing/library はメンテナンス状況を月次で確認し、停止が続く場合は代替を検討 |
| SEC-15 | ランタイム | Node.js・Python は LTS／サポート期間内の版のみ使う。App Service のランタイム廃止予告に追従する |

### 12.11 指定項目との対応

| 課題の指定項目 | 設計上の対応 |
|---|---|
| ログイン — JWT トークン | SEC-02（発行・クレーム・署名鍵）、SEC-03（HttpOnly Cookie 保持）、有効期限 8 時間 |
| ログイン — 認証認可 | SEC-01（bcrypt）、SEC-04（試行制限・汎用エラー）、SEC-05（RBAC・削除済み担当者の無効化） |
| POSレジ — BFF（リバースプロキシ） | SEC-06、SEC-07、7.6 BFF-1〜6 |
| POSレジ — CORS | SEC-08 |
| POSレジ — Backend でも計算し Frontend の値と照合 | SEC-09、API-06 の計算規則、API-07 の照合手順 |
| POSレジ — Swagger Docs 非表示 | SEC-10 |
| SQL インジェクション対策 — 型定義（Frontend / TypeScript） | SEC-11（Zod スキーマ、文字種・長さの制限） |
| SQL インジェクション対策 — ORM | SEC-13（SQLAlchemy バインド変数、生 SQL 禁止、LIKE エスケープ）＋ SEC-12（Pydantic） |
| フレームワーク・ライブラリ・OSS の脆弱性 — Ver 調査 | 12.10 の採用バージョン表（確認日付き）、SEC-15 の運用ルール |

---

## 13. 要件・指定項目との対応表

### 13.1 要件定義書の要件 → 本書の設計

| 要件 | 内容 | 設計要素 |
|---|---|---|
| FR-01 | ログイン・ログアウト | UC-01, 02／API-01〜03／SC-01（5.2）／AuthService（9.3）／SEC-01〜05／シーケンス 8.1 |
| FR-02 | 会員IDの読み込み・クリア | UC-03, 04／API-05, 06／`MemberPanel`, `CameraPreview`（5.3）／FR-02-1 のカメラ共用 = `scanMode`／シーケンス 8.3 |
| FR-03 | 商品の検索（スキャン・手入力） | UC-05, 06／API-04／`ProductEntryPanel`／SCAN_DEBOUNCE_MS／シーケンス 8.2 |
| FR-04 | 購入リストへの追加 | 5.4 状態管理（数量加算・新規行）／API-06／QTY_MAX |
| FR-05 | 購入リストの操作 | UC-07／`CartTable`, `SelectedItemPanel`／QTY_MIN / MAX／QUANTITY_OUT_OF_RANGE |
| FR-06 | 会員特典の値引き | UC-14／API-06 計算規則／PricingService／discounts, discount_applications（6.3）／10.2 DISCOUNT_* |
| FR-07 | 消費税 | API-06, 09〜11／tax_rates（6.3）／6.5 有効税率／10.2 TAX_*／シーケンス 8.5 |
| FR-08 | 購入の確定・記録 | UC-08／API-07, 08／transactions, transaction_items（6.3）／TransactionService／シーケンス 8.4 |
| FR-09 | マスタ・設定の管理 | UC-10〜13／API-10〜23, 25, 26／SC-03〜06（5.6）／MasterService／SEC-05／アクティビティ 4.2 |
| FR-10 | 現金決済・キャンセル | UC-08, 09／API-07（tendered_amount）、API-27（キャンセルの監査記録）／`CheckoutDialog`／INSUFFICIENT_TENDER／状態 checkout（4.3） |
| SC-01〜06 | 画面 | 5.2 ルート、5.3・5.6 コンポーネント |
| D-01〜D-09 | 保持する情報 | 6.3 テーブル定義（各列に D 番号を併記）、6.6 |
| DR-1〜DR-5 | データの制約 | 6.2 DB-3, DB-9, DB-10、6.1（税率を FK で結ばない） |
| N-01 | 役割分担 | 2.2、9.1 レイヤ、7.6 BFF |
| N-02 | データ保全 | API-07 の単一トランザクション、冪等性（7.3、idempotency_keys）、11.4 ロールバック |
| N-03 | 応答速度 | 2.3 Always On・同一リージョン、10.4 タイムアウト、6.4 索引 |
| N-04 | 接続維持 | 10.4 DB_POOL_*、UnitOfWork |
| N-05, N-10 | 端末・ブラウザ | 2.2、5.7、12.9 HTTPS、CAMERA_* エラー |
| N-06 | 同時利用 | DB-2（AUTO_INCREMENT）、2.6 |
| N-07 | セキュリティ | 12 章全体 |
| N-08 | バックアップ | 2.3 MySQL 自動バックアップ |
| N-09 | 操作ログ | audit_logs（6.3）、AuditService、11.5 |
| P-1〜P-5 | 前提条件 | 2.2、2.3 |
| A-1〜A-6 | 運用上の前提 | 2.1（複数端末）、10.1 CART_MAX_LINES（店舗規模） |
| I-1〜I-8 | 要件定義書の解釈 | そのまま継承。I-4 は members.birth_date、I-5 は products.unit_price（税抜）、I-6 は API-07 の確定タイミング |
| Q-1〜Q-8 | 要件定義書の仮定 | 10.2（Q-1〜4）、10.1（Q-5, Q-6）、10.4・要件定義書 6.1（Q-7）、API-07（Q-8）で確定 |

### 13.2 課題の指定項目 → 本書の章

| 指定項目 | 章・節 | 成果物 |
|---|---|---|
| ユースケース図 | 3.2 | sd_fig03 |
| アクティビティ図 | 4.1, 4.2 | sd_fig04a, sd_fig04b |
| シーケンス図 | 8.1〜8.5 | sd_fig08_1〜5 |
| クラス図 | 9.2（Backend）、9.5（Frontend） | sd_fig09, sd_fig09b |
| ER図 | 6.1 | sd_fig06 |
| 設定 — 入力値や商品数の下限・上限の定義 | 10.1, 10.2 | 定数表（`shared/limits.json`） |
| 設定 — エラー処理 | 11 章 | エラーコード 21 件＋Frontend 3 件、例外変換表 |
| 設定 — API一覧表（入力項目：キーとバリューの型定義、出力項目） | 7.2 一覧、7.4 共通型、7.5 各 API の入力表・出力表・TypeScript 型 | API-01〜27 |
| セキュリティ — ログイン：JWT トークン | 12.2 SEC-02, 03 | |
| セキュリティ — ログイン：認証認可 | 12.2 SEC-01, 04、12.3 SEC-05 | |
| セキュリティ — POSレジ：BFF（リバースプロキシ） | 12.4 SEC-06, 07、7.6 | |
| セキュリティ — POSレジ：CORS | 12.5 SEC-08 | |
| セキュリティ — POSレジ：Backend でも計算し Frontend の値と照合 | 12.6 SEC-09、7.5 API-06/07、8.4 | |
| セキュリティ — POSレジ：Swagger Docs 非表示 | 12.7 SEC-10 | |
| セキュリティ — SQL インジェクション：型定義（Frontend / TypeScript） | 12.8 SEC-11、7.4、`lib/schemas.ts` | |
| セキュリティ — SQL インジェクション：ORM | 12.8 SEC-13（SQLAlchemy）、SEC-12（Pydantic） | |
| セキュリティ — フレームワーク・ライブラリ・OSS の脆弱性：Ver 調査 | 12.10 採用バージョン表と OSV.dev 照会結果（確認日 2026-09-07。既知の脆弱性 0 件）、SEC-15 | |

### 13.3 対応の確認

- 要件定義書の FR / SC / D / DR / N / P / A の全識別子は 13.1 のいずれかの行に対応する
- 課題の指定項目 17 件は 13.2 のとおり、すべて本書の節と成果物に対応する
- 本書で新たに決めた事項（要件定義書に根拠がないもの）は 14.1 に列挙する

---

## 14. 未確定事項・変更履歴

### 14.1 本書で決定した事項（要件定義書に根拠がないもの）

実装前に発注者（課題出題者）の確認を得たい事項。確認が取れるまでは本書の決定で進める。

| # | 事項 | 本書の決定 | 影響 | 優先度 |
|---|---|---|---|---|
| U-1 | JWT の失効 | 8 時間で自動失効。サーバ側の失効リストは持たない。ログアウトは Cookie 削除のみ | 退職者等の即時無効化は担当者の論理削除（SEC-05 の DB 確認）で代替 | 中 |
| U-2 | ネットワークの閉域化 | VNet 統合・Private Endpoint は Basic プランで不可のため未採用。アクセス制限（IP）＋ X-BFF-Key ＋ TLS で代替 | 本番運用で要件が上がれば Standard 以上へ | 中 |
| U-3 | 管理画面の同時更新 | 楽観ロックなし（管理者 1 名想定） | 複数管理者になれば `updated_at` 比較を追加 | 低 |
| U-4 | TypeScript のメジャー版 | 5.x を採用。7.0（新コンパイラ）は Next.js の対応確認後 | ビルド速度 | 低 |
| U-5 | バーコードライブラリ | @zxing/library 0.23（最終リリース 2026-04）。更新停止時は BarcodeDetector や他ライブラリへ | Safari 対応の維持 | 中 |
| U-6 | 冪等キーの削除 | `idempotency_keys.expires_at` 経過分を日次で削除。実行手段は FastAPI 起動時のスケジューラ（APScheduler）とし、App Service の WebJob は Linux で使えないため採らない。アプリ用 DB ユーザには `idempotency_keys` に限り DELETE 権限を与える（12.8） | 運用 | 低 |
| U-7 | 初期データ | 初回デプロイ時に管理者 1 名と税率 1 件（10.00%、本日）を Alembic のデータマイグレーションで投入。なければ会計不可（TAX_RATE_NOT_CONFIGURED） | 初期構築 | 高 |
| U-8 | 1 会計の上限 | CART_MAX_LINES = 100 種類、TENDER_MAX = 9,999,999 円 | 業務上の妥当性 | 低 |
| U-9 | ログイン試行制限 | 10 回／分。恒久ロックなし | セキュリティと運用の均衡 | 中 |
| U-10 | 定数の共有方法 | `shared/limits.json` を Frontend・Backend が読み込む。CI で一致検査 | ビルド構成 | 低 |
| U-11 | 要件定義書のスコープ外 | 返品・取消、レシート印刷、購入履歴の照会画面、カード・QR 決済は本書でも対象外 | — | — |
| U-12 | 値引き期間の重なり | 同一商品で期間が重なる値引き設定の登録を許容し、適用時は値引き額が最大の 1 件を選ぶ（DISCOUNT_SELECTION）。登録時は管理画面が API-20 で既存設定を確認して警告のみ表示 | 販促運用 | 低 |
| U-13 | 税率設定の修正・削除の範囲 | 適用開始日が本日以前の税率は修正・削除不可（API-25 / 26）。誤登録の訂正は新しい設定の追加で行う | 運用 | 低 |

### 14.2 要件定義書の仮定（Q-1〜Q-8）の扱い

| Q | 内容 | 本書 |
|---|---|---|
| Q-1 | 税の端数・計算単位 | TAX_ROUNDING = floor、TAX_CALC_UNIT = transaction（10.2） |
| Q-2 | 割合値引きの端数 | DISCOUNT_ROUNDING = floor |
| Q-3 | 値引きと課税の順序 | DISCOUNT_BEFORE_TAX = true |
| Q-4 | 値引きの重複 | DISCOUNT_SELECTION = max_amount、discount_applications は 1 明細 1 件 |
| Q-5 | バーコード規格 | PRODUCT_CODE_LENGTH = 13（JAN）、MEMBER_CODE_MAX = 32（CODE128） |
| Q-6 | パスワード規則 | PASSWORD_MIN = 8、ロックなし、レート制限で補う（U-9） |
| Q-7 | 応答速度の目標 | 要件定義書 6.1 のとおり。BFF_UPSTREAM_TIMEOUT_MS = 5,000 |
| Q-8 | 保存タイミング | API-07（会計ポップアップの確定）で保存。購入ボタンでは保存しない |

いずれも設定値として外部化しているため、発注者の回答が異なった場合は `shared/limits.json` の変更で対応できる。

### 14.3 変更履歴

| 版 | 日付 | 内容 |
|---|---|---|
| v1.0 | 2026-09-07 | 初版。要件定義書 v1.2 を入力とし、システム構成、ユースケース図、アクティビティ図 2 枚、画面設計、ER 図とテーブル定義（9＋1 テーブル）、API 24 本の入出力と TypeScript 型、シーケンス図 5 枚、クラス図、設定・制約値、エラーコード 24 件、セキュリティ対策と依存ライブラリのバージョン調査（2026-09-07 時点）、要件・指定項目との対応表を定めた |
| v1.1 | 2026-09-07 | 文脈を持たない第三者（Backend 実装者・Frontend 実装者・採点者・整合性検査の 4 視点）による読者テストの指摘を反映。Cookie の Path を `/` に変更（middleware ガードとの矛盾を解消）。冪等キーの生成時期を購入ボタン押下時に統一し、キャンセルで破棄。税率の修正・削除 API（API-25, 26）と会計キャンセルの監査 API（API-27）を追加。0 行の会計を 422 CART_EMPTY に到達させるため入力制約を見直し、型検証（400）と業務範囲（422）の役割を API-P8 で明文化。アプリ用 DB ユーザに idempotency_keys の DELETE 権限を追加。会員ID空入力での会員なし進行、商品モードでの会員証読み取り、数量 0・空欄、会員証モードのタイムアウト、pendingProduct のクリア、line_no の採番、値引き期間の重なりを明文化。SEC-14（個人情報の最小化）を定義。OSV.dev による既知脆弱性の照会結果を追加。Frontend のクラス図（9.5）を追加し、Backend クラス図と ER 図の列をテーブル定義に合わせた。再検証で残った波及漏れ（追加 API の 11.2・13.1・9.4・A.3 への反映、Zod と Pydantic の検証範囲の明確化、型定義の追加）を修正 |
| v1.2 | 2026-09-09 | レビュー指摘「6.5 の取引日（JST）の生成元が未定義」を反映。取引日は Backend の PricingService が UTC 現在時刻を BUSINESS_TIMEZONE へ変換して 1 箇所で生成し、`date.today()`・SQL の `CURDATE()`・Frontend の時計を使わないことを 6.5・DB-6・7.5・9.3・10.4 に明記。API-07 では取引時刻と取引日を同じ瞬間から作る。`Clock` 依存を追加し、JST 0:00 前後（UTC 14:59:59 / 15:00:00）の境界テストを必須とした |

---

## 付録 A. 図の Mermaid ソース

再生成方法（ローカルの Chrome を用いる。Chromium のダウンロードは不要）:

```bash
npm install @mermaid-js/mermaid-cli
# puppeteer.json: { "executablePath": "C:/Program Files/Google/Chrome/Application/chrome.exe", "args": ["--no-sandbox"] }
npx mmdc -p puppeteer.json -i <name>.mmd -o <name>.png -b white -s 2 -w 1600
```

注意: Mermaid のメッセージ内で `;` は文の区切りと解釈されるため使わない（`,` で代替）。

### A.1 システム構成図（sd_fig02）

```mermaid
flowchart LR
  subgraph STORE["店舗 (レジ端末 複数台)"]
    BR["ブラウザ<br/>Chrome / Edge / Safari<br/>Next.js 画面 + ZXing(バーコード復号)"]
    CAM["カメラ"] --> BR
  end

  subgraph AZ["Microsoft Azure (Japan East)"]
    subgraph PLAN["App Service Plan Basic B1 (Always On)"]
      WEB["App Service: pos-web<br/>Next.js 16 (Node 24)<br/>画面配信 + BFF (Route Handler)"]
      API["App Service: pos-api<br/>FastAPI (Python 3.11, gunicorn+uvicorn)<br/>業務ロジック・金額計算の正本"]
    end
    DB[("Azure Database for MySQL<br/>Flexible Server (B1ms)<br/>utf8mb4 / SSL 必須 / 自動バックアップ 7日")]
    KV["Key Vault<br/>JWT_SECRET, DATABASE_URL, BFF_SHARED_KEY"]
    LOG["App Service ログ<br/>(アプリログ 30日)"]
  end

  BR -- "HTTPS<br/>Cookie(HttpOnly JWT)" --> WEB
  WEB -- "HTTPS<br/>Authorization: Bearer<br/>X-BFF-Key, X-Request-Id<br/>(アクセス制限: pos-web の送信IPのみ)" --> API
  API -- "TLS<br/>SQLAlchemy 接続プール" --> DB
  KV -. "アプリケーション設定<br/>(Key Vault 参照)" .-> WEB
  KV -. "アプリケーション設定" .-> API
  WEB -. stdout .-> LOG
  API -. stdout .-> LOG
  BR -. "直接アクセス不可<br/>(CORS + アクセス制限 + X-BFF-Key)" .-x API
```

### A.2 ユースケース図（sd_fig03）

```mermaid
flowchart LR
  cashier(["レジ担当者<br/>(cashier)"])
  admin(["管理者<br/>(admin)"])
  subgraph POS["簡易POSアプリ"]
    direction TB
    UC01(["UC-01 ログインする"])
    UC02(["UC-02 ログアウトする"])
    UC03(["UC-03 会員証を読み込む"])
    UC04(["UC-04 会員IDをクリアする"])
    UC05(["UC-05 商品をスキャンして登録する"])
    UC06(["UC-06 商品コードを手入力して登録する"])
    UC07(["UC-07 購入リストを編集する<br/>(選択・削除・数量変更)"])
    UC08(["UC-08 会計を確定する(現金)"])
    UC09(["UC-09 会計をキャンセルする"])
    UC10(["UC-10 商品マスタを管理する"])
    UC11(["UC-11 会員マスタを管理する"])
    UC12(["UC-12 消費税率を設定する"])
    UC13(["UC-13 値引きを設定する"])
    UC14(["UC-14 値引きと消費税を算出する"])
  end
  cashier --> UC01
  cashier --> UC02
  cashier --> UC03
  cashier --> UC04
  cashier --> UC05
  cashier --> UC06
  cashier --> UC07
  cashier --> UC08
  cashier --> UC09
  admin --> UC10
  admin --> UC11
  admin --> UC12
  admin --> UC13
  admin -. "レジ担当者の権限を含む" .-> cashier
  UC03 -. "include" .-> UC14
  UC05 -. "include" .-> UC14
  UC06 -. "include" .-> UC14
  UC07 -. "include" .-> UC14
  UC08 -. "include" .-> UC14
```

### A.3 アクティビティ図: レジ 1 取引（sd_fig04a）

```mermaid
flowchart TD
  S(["開始: ログイン済み・SC-02 初期状態"]) --> P{"次の操作"}
  P -->|"会員証スキャン / ID手入力"| C["会員IDを読み込む<br/>API-05"]
  C --> D{"会員が存在?"}
  D -->|"いいえ"| E["メッセージ表示<br/>会員IDは未設定のまま"] --> P
  D -->|"はい"| F["会員名表示<br/>API-06 で値引きを遡り適用"] --> P
  P -->|"会員IDクリア"| F2["会員なしに戻す<br/>API-06 で値引き解除"] --> P
  P -->|"商品スキャン / コード手入力+読み込み"| G["商品を検索<br/>API-04"]
  G --> H{"マスタに存在?"}
  H -->|"いいえ"| I["メッセージ表示: マスタ未登録"] --> P
  H -->|"はい (スキャンは自動追加、手入力は追加ボタン)"| J{"同一商品が<br/>リストにある?"}
  J -->|"はい"| K{"数量 + 1 が 99 以下?"}
  K -->|"いいえ"| L["メッセージ表示: 上限 99<br/>追加フィードバックなし"] --> P
  K -->|"はい"| M["数量を加算"]
  J -->|"いいえ"| N["新しい行を追加"]
  M --> O["API-06 で再計算<br/>リスト・合計を更新<br/>追加フィードバック表示"]
  N --> O
  O --> P
  P -->|"行を選択して削除 / 数量変更"| Q{"数量が 1〜99?"}
  Q -->|"いいえ"| Q2["メッセージ表示: 範囲外<br/>直前の数量を維持"] --> P
  Q -->|"はい"| O
  P -->|"購入ボタン"| R{"リストが空?"}
  R -->|"はい"| T["メッセージ表示: 商品未登録"] --> P
  R -->|"いいえ"| U["会計ポップアップ<br/>税抜・税込合計を表示<br/>預かり金額 初期値=税込合計"]
  U --> V{"操作"}
  V -->|"キャンセル"| CX["API-27 で監査ログ記録<br/>(応答を待たない)"] --> P
  V -->|"預かり金額を変更"| U
  V -->|"確定"| W{"預かり金額が税込合計以上?"}
  W -->|"いいえ"| X["不足額を表示<br/>確定ボタン無効"] --> U
  W -->|"はい"| Y["API-07 で確定<br/>(Idempotency-Key)"]
  Y --> Z{"Backend 再計算と一致?"}
  Z -->|"いいえ (409)"| Z2["サーバ値で表示を更新<br/>再確認を促す"] --> U
  Z -->|"はい (201)"| AA["取引保存済み<br/>お釣りを表示"]
  AA --> AB["閉じる: 画面をすべてクリア"]
  AB --> S
  P -->|"ログアウト"| AC(["SC-01 へ"])
```

### A.4 アクティビティ図: 管理者のマスタ操作（sd_fig04b）

```mermaid
flowchart TD
  S(["管理者でログイン済み (role=admin)"]) --> A["SC-02 の管理画面ボタン<br/>(cashier には表示しない)"]
  A --> B{"対象を選択"}
  B -->|"商品"| C1["SC-03 商品マスタ一覧<br/>API-12"]
  B -->|"会員"| C2["SC-04 会員マスタ一覧<br/>API-16"]
  B -->|"税率"| C3["SC-05 税率一覧<br/>API-10"]
  B -->|"値引き"| C4["SC-06 値引き一覧<br/>API-20"]
  C1 --> D{"操作"}
  C2 --> D
  C3 --> D
  C4 --> D
  D -->|"新規登録 / 編集"| E["入力フォーム"]
  E --> F{"Zod 検証 OK?"}
  F -->|"いいえ"| G["項目ごとにエラー表示"] --> E
  F -->|"はい"| H["POST / PUT<br/>FastAPI: role=admin 確認<br/>Pydantic 再検証"]
  H --> I{"結果"}
  I -->|"409 重複 / 422 期間不正"| G
  I -->|"201 / 200"| J["監査ログ記録<br/>一覧を再取得"] --> D
  D -->|"削除"| K["確認ダイアログ"]
  K -->|"OK"| L["DELETE (論理削除)<br/>過去の取引記録は保持"] --> J
  K -->|"取消"| D
  D -->|"戻る"| M(["SC-02 へ"])
```

### A.5 ER 図（sd_fig06）

```mermaid
erDiagram
  staff ||--o{ transactions : "処理する"
  members |o--o{ transactions : "購入する(会員なし可)"
  transactions ||--|{ transaction_items : "含む"
  products ||--o{ transaction_items : "スナップショット元"
  products ||--o{ discounts : "対象"
  transaction_items ||--o| discount_applications : "値引き適用"
  discounts ||--o{ discount_applications : "適用元"
  staff |o--o{ audit_logs : "操作者"
  staff |o--o{ tax_rates : "登録者"

  staff {
    bigint id PK
    varchar login_id UK "担当者ID D-01-1"
    varchar password_hash "bcrypt D-01-2"
    varchar name "氏名 D-01-3"
    enum role "cashier/admin D-01-4"
    datetime deleted_at "論理削除"
  }
  products {
    bigint id PK
    varchar product_code UK "JAN13桁 D-02-1"
    varchar name "D-02-2"
    int unit_price "税抜 D-02-3"
    datetime deleted_at "論理削除"
  }
  members {
    bigint id PK
    varchar member_code UK "会員ID D-03-1"
    varchar name "D-03-2"
    varchar phone "D-03-3"
    varchar address "D-03-4"
    enum gender "D-03-5"
    date birth_date "生年月日 D-03-6"
    datetime deleted_at "論理削除"
  }
  transactions {
    bigint id PK "取引ID D-04-1"
    datetime transacted_at "D-04-2"
    bigint staff_id FK "D-04-3"
    bigint member_id FK "NULL可 D-04-4"
    int subtotal_excl_tax "D-04-5"
    int tax_amount "D-04-6"
    int total_incl_tax "D-04-7"
    decimal tax_rate "適用税率 D-04-8"
    int tendered_amount "預かり D-04-9"
    int change_amount "お釣り D-04-10"
  }
  transaction_items {
    bigint id PK
    bigint transaction_id FK "D-05-1"
    int line_no "表示順"
    bigint product_id FK
    varchar product_code "写し D-05-2"
    varchar product_name "写し D-05-3"
    int unit_price "写し D-05-4"
    int quantity "1-99 D-05-5"
    int discount_amount "D-05-6"
    int line_total "D-05-7"
  }
  tax_rates {
    bigint id PK
    decimal rate "D-06-1"
    date effective_from UK "D-06-2"
    bigint created_by_staff_id FK
    datetime deleted_at "論理削除"
  }
  discounts {
    bigint id PK "D-07-1"
    bigint product_id FK "D-07-2"
    varchar name "企画名(追加)"
    date start_date "D-07-3"
    date end_date "D-07-4"
    enum discount_type "percent/amount D-07-5"
    decimal discount_value "D-07-6"
    datetime deleted_at "論理削除"
  }
  discount_applications {
    bigint id PK
    bigint transaction_item_id FK "UK D-08-1"
    bigint discount_id FK "D-08-2"
    enum discount_type "写し"
    decimal discount_value "写し"
    int applied_amount "D-08-3"
  }
  audit_logs {
    bigint id PK
    datetime occurred_at "D-09-1"
    varchar action "D-09-2"
    bigint staff_id FK "NULL可 D-09-3"
    varchar attempted_login_id "失敗時"
    varchar target_type "D-09-4"
    varchar target_id "D-09-4"
    enum result "success/failure D-09-5"
    varchar detail "失敗理由"
    varchar ip_address "要求元IP(追加)"
  }
```

### A.6 シーケンス図: ログイン（sd_fig08_1）

```mermaid
sequenceDiagram
  autonumber
  actor U as レジ担当者
  participant B as ブラウザ (SC-01)
  participant F as BFF (Next.js)
  participant A as FastAPI
  participant DB as MySQL
  U->>B: 担当者ID・パスワード入力、ログイン
  B->>F: POST /api/auth/login {login_id, password}
  F->>F: Zod 検証・レート制限 (SEC-04)
  F->>A: POST /api/v1/auth/login<br/>+ X-BFF-Key, X-Request-Id
  A->>A: Pydantic 検証
  A->>DB: SELECT staff WHERE login_id=? AND deleted_at IS NULL
  DB-->>A: staff 行 (password_hash, role)
  A->>A: bcrypt.verify(password, password_hash)
  alt 認証成功
    A->>A: JWT 発行 (sub, login_id, role, exp=+8h, jti)
    A->>DB: INSERT audit_logs (LOGIN, success)
    A-->>F: 200 {access_token, expires_in, staff}
    F->>F: Set-Cookie pos_session=JWT<br/>HttpOnly, Secure, SameSite=Strict, Path=/
    F-->>B: 200 {staff}
    B->>B: SC-02 へ遷移、担当者名を表示 (SC-02-01)
  else 認証失敗 (ID なし / パスワード不一致)
    A->>DB: INSERT audit_logs (LOGIN_FAILED, attempted_login_id)
    A-->>F: 401 AUTH_INVALID_CREDENTIALS
    F-->>B: 401 (同一文言)
    B->>B: エラー表示 (SC-01-04)、SC-01 に留まる
  end
```

### A.7 シーケンス図: スキャンから購入リスト追加（sd_fig08_2）

```mermaid
sequenceDiagram
  autonumber
  actor U as レジ担当者
  participant B as ブラウザ (SC-02)
  participant F as BFF
  participant A as FastAPI
  participant DB as MySQL
  U->>B: 商品のバーコードをカメラにかざす
  B->>B: ZXing が JAN(EAN-13) を復号 → 商品コード
  B->>F: GET /api/products/{code}
  F->>A: GET /api/v1/products/{code} (Bearer)
  A->>DB: SELECT products WHERE product_code=? AND deleted_at IS NULL
  alt 存在する
    DB-->>A: 商品行
    A-->>F: 200 ProductInfo
    F-->>B: 200 ProductInfo
    B->>B: 同一商品が購入リストにあれば数量+1、なければ新規行<br/>(99 超なら拒否しメッセージ表示、以降を中止)
    B->>F: POST /api/pricing/quote {member_code, items[]}
    F->>A: POST /api/v1/pricing/quote
    A->>DB: SELECT tax_rates (本日有効), products, discounts (期間内)
    DB-->>A: 行
    A->>A: 明細ごとの値引き・小計、税抜合計・税額・税込合計を算出 (7.5 規則)
    A-->>F: 200 QuoteResult
    F-->>B: 200 QuoteResult
    B->>B: 購入リスト・合計を更新 (SC-02-16, 21)<br/>「1件追加されました」を表示 (SC-02-15)
  else マスタ未登録
    DB-->>A: 0 行
    A-->>F: 404 PRODUCT_NOT_FOUND
    F-->>B: 404
    B->>B: 「商品がマスタ未登録です」を表示 (SC-02-04)
  end
  Note over B: 手入力の場合は「読み込み」で API-04 を呼び名称・単価を表示し、<br/>「追加」ボタンで同じ判定と API-06 を実行する (FR-03-3)
```

### A.8 シーケンス図: 会員読み込みと値引きの遡り適用（sd_fig08_3）

```mermaid
sequenceDiagram
  autonumber
  actor U as レジ担当者
  participant B as ブラウザ (SC-02)
  participant F as BFF
  participant A as FastAPI
  participant DB as MySQL
  Note over B: 購入リストに商品 3 点が登録済み (会員なし)
  U->>B: 「会員証スキャン」→ カメラを会員証モードへ
  B->>B: ZXing が CODE128 を復号 → 会員ID、商品モードへ復帰
  B->>F: GET /api/members/{code}
  F->>A: GET /api/v1/members/{code}
  A->>DB: SELECT members WHERE member_code=? AND deleted_at IS NULL
  alt 会員が存在する
    DB-->>A: 会員行
    A-->>F: 200 MemberInfo (氏名のみ)
    F-->>B: 200 MemberInfo
    B->>B: 会員名を表示 (SC-02-08)、会員IDを取引に設定
    B->>F: POST /api/pricing/quote {member_code, items[3 点]}
    F->>A: POST /api/v1/pricing/quote
    A->>DB: SELECT discounts WHERE product_id IN (...) AND 期間内 AND deleted_at IS NULL
    DB-->>A: 該当する値引き
    A->>A: 会員ありのため対象行に値引きを適用 (複数なら最大額の 1 件)
    A-->>F: 200 QuoteResult (lines[].discount)
    F-->>B: 200 QuoteResult
    B->>B: 登録済みの 3 行に値引き額を表示、合計を更新 (FR-06-7 遡り適用)
  else 会員が存在しない
    DB-->>A: 0 行
    A-->>F: 404 MEMBER_NOT_FOUND
    F-->>B: 404
    B->>B: メッセージ表示。会員IDは未設定のまま (FR-02-6)
  end
```

### A.9 シーケンス図: 購入確定（sd_fig08_4）

```mermaid
sequenceDiagram
  autonumber
  actor U as レジ担当者
  participant B as ブラウザ (SC-02)
  participant F as BFF
  participant A as FastAPI
  participant DB as MySQL
  U->>B: 購入ボタン
  B->>B: Idempotency-Key (UUID) を生成 (checkout 開始)
  B->>B: 会計ポップアップ表示 (税抜・税込合計、預かり金額=税込合計)
  U->>B: 預かり金額を入力し「確定」
  B->>F: POST /api/transactions {items[], 合計, tendered_amount}<br/>Idempotency-Key
  F->>F: Zod 検証 (型・形式。業務範囲は Backend)
  F->>A: POST /api/v1/transactions (Bearer, Idempotency-Key)
  A->>A: Pydantic 検証、role=cashier 以上、staff 有効確認 (SEC-05)
  A->>DB: SELECT idempotency_keys WHERE key=?
  alt 既存キー (再送)
    DB-->>A: 保存済み応答
    A-->>F: 201 (初回と同じ本文)
  else 新規キー
    A->>DB: SELECT products / tax_rates / discounts (マスタから再取得)
    DB-->>A: 行
    A->>A: 全額を再計算し Frontend の値と 1 円単位で照合 (SEC-09)
    alt 不一致
      A->>DB: INSERT audit_logs (TRANSACTION_COMMIT, failure, PRICE_MISMATCH)
      A-->>F: 409 PRICE_MISMATCH {details.server: QuoteResult}
      F-->>B: 409
      B->>B: サーバ値で表示を差し替え、再確認を促す
    else 一致
      A->>A: tendered_amount が total_incl_tax 以上か確認 (不足なら 422)
      A->>DB: BEGIN
      A->>DB: INSERT transactions (再計算値, tax_rate, tendered, change)
      A->>DB: INSERT transaction_items × n (写し列)
      A->>DB: INSERT discount_applications (値引きがある行)
      A->>DB: INSERT idempotency_keys (key, 応答)
      A->>DB: INSERT audit_logs (TRANSACTION_COMMIT, success)
      A->>DB: COMMIT
      A-->>F: 201 CommitResponse (transaction_id, change_amount)
      F-->>B: 201
      B->>B: お釣りを表示 (SC-02-23-3)
      U->>B: 閉じる
      B->>B: 画面をすべてクリア、次の会員ID読み込みから再開 (FR-08-4)
    end
  end
```

### A.10 シーケンス図: 消費税率の変更（sd_fig08_5）

```mermaid
sequenceDiagram
  autonumber
  actor M as 管理者
  participant B as ブラウザ (SC-05)
  participant F as BFF
  participant A as FastAPI
  participant DB as MySQL
  M->>B: 税率 12.00、適用開始日 2027-04-01 を入力し保存
  B->>F: POST /api/tax-rates {rate, effective_from}
  F->>F: Zod 検証 (0〜100、本日以降)
  F->>A: POST /api/v1/tax-rates (Bearer)
  A->>A: JWT 検証、require_role(admin) (SEC-05)
  alt role が cashier
    A-->>F: 403 FORBIDDEN
    F-->>B: 403
  else role が admin
    A->>DB: SELECT tax_rates WHERE effective_from=?
    alt 同日の設定が既にある
      A-->>F: 409 DUPLICATE_CODE
      F-->>B: 409 → エラー表示
    else 重複なし
      A->>DB: INSERT tax_rates (rate, effective_from, created_by_staff_id)
      A->>DB: INSERT audit_logs (TAX_RATE_CREATE)
      A-->>F: 201 TaxRateInfo
      F-->>B: 201 → 一覧を再取得して表示
    end
  end
  Note over A,DB: 以後の API-06 / API-07 は取引日に応じて<br/>「適用開始日が取引日以前で最新の 1 件」を採用 (6.5)。<br/>過去の取引は tax_rate を写し取っているため変わらない (DR-1)
```

### A.11 クラス図（sd_fig09）

```mermaid
classDiagram
  direction TB

  class Staff {
    +int id
    +str login_id
    +str password_hash
    +str name
    +Role role
    +datetime deleted_at
  }
  class Product {
    +int id
    +str product_code
    +str name
    +int unit_price
    +datetime deleted_at
  }
  class Member {
    +int id
    +str member_code
    +str name
    +str phone
    +str address
    +Gender gender
    +date birth_date
    +datetime deleted_at
    +age() int
  }
  class Transaction {
    +int id
    +datetime transacted_at
    +int staff_id
    +int member_id
    +int subtotal_excl_tax
    +int tax_amount
    +int total_incl_tax
    +Decimal tax_rate
    +int tendered_amount
    +int change_amount
  }
  class TransactionItem {
    +int id
    +int transaction_id
    +int line_no
    +int product_id
    +str product_code
    +str product_name
    +int unit_price
    +int quantity
    +int discount_amount
    +int line_total
  }
  class TaxRate {
    +int id
    +Decimal rate
    +date effective_from
    +int created_by_staff_id
    +datetime deleted_at
  }
  class Discount {
    +int id
    +int product_id
    +str name
    +date start_date
    +date end_date
    +DiscountType discount_type
    +Decimal discount_value
    +datetime deleted_at
  }
  class DiscountApplication {
    +int id
    +int transaction_item_id
    +int discount_id
    +DiscountType discount_type
    +Decimal discount_value
    +int applied_amount
  }
  class AuditLog {
    +int id
    +datetime occurred_at
    +str action
    +int staff_id
    +str attempted_login_id
    +str target_type
    +str target_id
    +Result result
    +str detail
    +str ip_address
  }

  Transaction "1" *-- "1..*" TransactionItem : items
  TransactionItem "1" o-- "0..1" DiscountApplication : discount
  Staff "1" <-- "0..*" Transaction : staff
  Member "0..1" <-- "0..*" Transaction : member
  Product "1" <-- "0..*" TransactionItem : product
  Product "1" <-- "0..*" Discount : product
  Discount "1" <-- "0..*" DiscountApplication : discount
  Staff "0..1" <-- "0..*" AuditLog : staff

  class AuthService {
    +login(login_id, password) TokenResult
    +verify_token(token) StaffClaims
    +require_role(role) Dependency
    +hash_password(raw) str
  }
  class PricingService {
    +quote(items, member_code, on_date) QuoteResult
    +resolve_tax_rate(on_date) TaxRate
    +resolve_discount(product, on_date) Discount
    +calc_line(product, qty, discount) QuoteLine
    +calc_totals(lines, rate) Totals
  }
  class TransactionService {
    +commit(req, idem_key, staff) Transaction
    +verify_against_client(server, client) None
    +get(id) Transaction
    +record_cancel(idem_key, staff, summary) None
  }
  class MasterService {
    +list_products(q, page, size) Page
    +create_product(req) Product
    +update_product(id, req) Product
    +soft_delete_product(id) None
    +list_members(q, page, size) Page
    +create_member(req) Member
    +update_member(id, req) Member
    +soft_delete_member(id) None
    +list_tax_rates() List
    +create_tax_rate(req) TaxRate
    +update_tax_rate(id, req) TaxRate
    +soft_delete_tax_rate(id) None
    +list_discounts(q, page, size) Page
    +create_discount(req) Discount
    +update_discount(id, req) Discount
    +soft_delete_discount(id) None
  }
  class AuditService {
    +record(action, staff_id, target, result, detail) None
  }
  class UnitOfWork {
    +Session session
    +begin()
    +commit()
    +rollback()
  }

  TransactionService ..> PricingService : 再計算
  TransactionService ..> AuditService
  TransactionService ..> UnitOfWork
  AuthService ..> AuditService
  MasterService ..> AuditService
  MasterService ..> UnitOfWork
  PricingService ..> Product
  PricingService ..> TaxRate
  PricingService ..> Discount
  TransactionService ..> Transaction : 生成
```

### A.12 Frontend クラス図（sd_fig09b）

```mermaid
classDiagram
  direction LR

  class CartStore {
    +CartStatus status
    +StaffInfo staff
    +MemberInfo member
    +ScanMode scanMode
    +ProductInfo pendingProduct
    +List~CartLine~ lines
    +QuoteResult quote
    +number selectedLineNo
    +Money tendered
    +string idempotencyKey
    +CommitResponse commitResult
    +addProduct(product) void
    +changeQuantity(lineNo, qty) void
    +removeLine(lineNo) void
    +setMember(member) void
    +clearMember() void
    +openCheckout() void
    +cancelCheckout() void
    +commit() Promise~CommitResponse~
    +reset() void
  }
  class ApiClient {
    +get(path) Promise~T~
    +post(path, body, headers) Promise~T~
    -newRequestId() string
  }
  class PricingView {
    +recalcTotals(quote, lines) Totals
  }
  class BarcodeScanner {
    +start(mode) void
    +stop() void
    +onDecode(callback) void
    -debounceSameCode(code) boolean
    -memberTimeout Timer
  }
  class CheckoutDialog {
    +Money tendered
    +Money change
    +confirm() void
    +cancel() void
    +close() void
  }
  class Schemas {
    +LoginRequest ZodSchema
    +QuoteRequest ZodSchema
    +CommitRequest ZodSchema
    +MemberCreateRequest ZodSchema
  }
  class BffRoute {
    +handle(request) Response
    -cookieToBearer(request) Headers
    -validate(schema, body) void
    -proxy(path, init) Response
  }

  CartStore ..> ApiClient : API-04/05/06/07/27
  CartStore ..> PricingView : 合計の再集計
  BarcodeScanner --> CartStore : 復号結果を通知
  CheckoutDialog --> CartStore : 確定/キャンセル/閉じる
  ApiClient --> BffRoute : /api/*
  BffRoute ..> Schemas : Zod 検証
```
