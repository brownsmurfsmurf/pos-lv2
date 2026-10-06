# 設計仕様書（要求忠実版・やさしい版）: 簡易POSアプリ（Lv1 + Lv2）

> この文書は「Lv2_簡易POSアプリ_設計仕様書_要求忠実版」を、初めて読む人向けに短く書き直したものです。
> API・テーブル・図の番号は元の文書と同じです。詳しい型定義や Mermaid ソースは元の文書を見てください。

## この文書の読み方

- **要件定義書**が「何を作るか」なら、**設計仕様書**は「どう作るか」です。要件定義書（要求忠実版）の番号（FR、SC、D、N、Q）をそのまま使います
- 課題で指定された項目（UML 4 種、ER 図、入力の上下限、エラー処理、API 一覧、セキュリティ）を、**要求にある機能の範囲だけ**で書いています
- **★** は、要求に書かれていないけれど課題の指定を満たすために「仮に決めた」値や事項です。要件定義書の確認事項（Q-n）と結びつけています

---

## 1. 全体の作り（システム構成）

![システム構成図](sdr_fig02_システム構成図.png)

3 つの層でできています。

| 層 | 何をするか | 使うもの |
|---|---|---|
| ブラウザ（レジ端末） | 画面を表示し、カメラでバーコードを読む。購入リストの内容を一時的に持つ | カメラ付きの端末 |
| pos-web | 画面を配る。ブラウザと処理側の間に立つ「BFF」（Backend For Frontend＝画面専用の中継役）として、ログイン情報を付け替え、入力を確認してから処理側へ渡す | Next.js |
| pos-api | 認証、金額計算、取引の保存。**金額計算の正解はここだけが持つ** | FastAPI、SQLAlchemy |
| データベース | すべてのデータを保存する | Azure Database for MySQL |

ブラウザが話す相手は pos-web だけです。pos-api は pos-web からの要求だけを受け（他からは CORS で拒否）、
データベースは pos-api からだけ接続を受けます。Azure では App Service の Always On（常に起動）を使い、
要件 N-03・N-04 を満たします（Free プランでは Always On が使えないので Basic 以上）。

---

## 2. 使い方（ユースケース）

![ユースケース図](sdr_fig03_ユースケース図.png)

使う人はレジ担当者だけです（要求に他の利用者は出てきません）。

| UC | できること | 要件 | 使う API |
|---|---|---|---|
| UC-01 | ログインする | FR-01 | API-01, 02 |
| UC-02 | 会員IDを読み込む（スキャン／手入力）。先に登録した商品にも値引きが付く | FR-02, FR-06-7 | API-04, 05 |
| UC-03 | 商品をスキャンして登録する | FR-03-1〜2, FR-04 | API-03, 05 |
| UC-04 | 商品コードを手入力して登録する | FR-03-3〜5, FR-04 | API-03, 05 |
| UC-05 | 購入リストを編集する（選ぶ・消す・数量変更） | FR-05 | API-05 |
| UC-06 | 購入を確定する（保存 → 税込・税抜合計を表示 → 閉じて空にする） | FR-07, FR-08 | API-06 |
| UC-07 | （内部）値引きと消費税を計算する | FR-06, FR-07 | API-05 |

---

## 3. 業務の流れ（アクティビティ図）

![アクティビティ図](sdr_fig04_アクティビティ_レジ取引.png)

1 回の会計の流れです。分かれ道と、その根拠を示します。

| 分かれ道 | どうなるか | 要件 |
|---|---|---|
| 会員がいるか | いなければ「その旨を伝える」。その後は未決（Q-3） | FR-02-6 |
| 商品がマスタにあるか | なければ「商品がマスタ未登録です」 | FR-03-4, 03-5 |
| 同じ商品がリストにあるか | あれば数量を増やす、なければ新しい行 | FR-04-4, 04-5 |
| 数量が 99 を超える | 動きは未決（Q-2） | FR-05-7 |
| リストが空で購入 | 動きは未決（Q-4） | FR-08-1 |
| 金額の照合が一致するか | 処理側で計算し直した金額と画面の金額が違えば保存せず 409 エラー | 課題指定 |

購入リストの状態は「idle（空）→ editing（編集中）→ committed（保存済み・ポップアップ表示中）→ idle」の 3 つです。

---

## 4. 画面の作り

画面と要素の番号は要件定義書の第4章（SC-01、SC-02-01〜21）と同じです。

| 画面 | URL | 入れる条件 |
|---|---|---|
| SC-01 ログイン | `/login` | ログイン済みなら `/pos` へ |
| SC-02 POS メイン | `/pos` | ログイン情報（Cookie）がなければ `/login` へ。本当のチェックは処理側の JWT 検証 |

SC-02 は次の部品（コンポーネント）に分けて作ります。

| 部品 | 要素 | 役割 |
|---|---|---|
| PosHeader | SC-02-01 | 担当者名 |
| MessageBar | SC-02-02 | 伝えるべきメッセージ |
| MemberPanel | SC-02-03〜06 | 会員IDの手入力・スキャン開始・会員名表示 |
| CameraPreview | SC-02-07 | カメラの映像。読み取った値を会員・商品の部品に渡す。同じコードの連続検出は 1.5 秒無視（★）。読み取った商品を追加ボタンなしでリストに入れるかは Q-5（★ 仮に自動追加） |
| ProductEntryPanel | SC-02-08〜13 | 商品コードの手入力・読み込み・追加・「1 件追加」表示 |
| CartTable | SC-02-14, 15 | 購入リストと選んだ行の強調 |
| SelectedItemPanel | SC-02-16〜18 | 選んだ商品の情報、数量変更（方式は Q-1）、削除 |
| TotalsPanel | SC-02-19 | 合計 |
| PurchaseButton | SC-02-20 | 購入 |
| ResultPopup | SC-02-21 | 税込・税抜合計の表示と「閉じる」 |

画面側は、購入リストが変わるたびに API-05 を呼び、返ってきた金額を表示します。**値引きの判定や税率の決定を画面側では行いません**（金額の正解は処理側だけ）。

---

## 5. データベース

![ER図](sdr_fig06_ER図.png)

ER 図（Entity Relationship＝テーブル同士の関係の図）のとおり 8 つのテーブルを作ります。

| テーブル | 主な列 | 要件 |
|---|---|---|
| staff（担当者） | login_id（担当者ID）、password_hash（パスワード。★ハッシュ化、Q-11）、name | D-01 |
| products（商品） | product_code（★13 桁、Q-21）、name、unit_price（★税抜） | D-02 |
| members（会員） | member_code（会員ID）、name、phone、address、gender、age（要求どおり年齢。Q-12） | D-03 |
| transactions（取引） | transacted_at（いつ）、staff_id（誰が処理）、member_id（誰が買った。空も可）、税抜合計・税額・税込合計 | D-04 |
| transaction_items（明細） | transaction_id、line_no、product_id、unit_price（**買った時点の単価を写す**）、quantity（1〜99）、discount_amount、line_total | D-05 |
| tax_rates（税率） | rate。有効な行は 1 件 | D-06 |
| discounts（値引き） | product_id、start_date、end_date、discount_type（percent / amount）、discount_value | D-07 |
| discount_applications（値引きの適用記録） | transaction_item_id、discount_id、applied_amount | D-08 |

共通のルール:

- 金額は円の整数。日時は世界標準時（UTC）で保存し、表示するときに日本時間にする
- 明細に「買った時点の単価」を写しておくので、後で商品の単価を変えても過去の取引は変わらない（DR-1）
- 取引には適用した税率も保存する（★ Q-13）。明細には買った時点の商品名も写す（★ Q-14）。商品・会員は物理削除せず、取引から参照できるようにする（★ Q-15）
- 税率・値引きの変更手段は要求にないため、この設計では**管理画面を作らず、SQL で直接データを入れる**ことを最小の実装とする（Q-9）
- **値引き期間の判定に使う「取引日」の作り方**（講師指摘への対応）: 処理側が、今の時刻を UTC で 1 回取得し、日本時間（Asia/Tokyo）に変換した日付を使う。`date.today()`（サーバの時間帯に依存）や SQL の `CURDATE()`、画面側の時計は使わない。Azure のサーバは UTC で動くため、これをしないと日本時間の 0:00〜8:59 に前日と判定され、当日で終わる値引きが朝に効いてしまう

---

## 6. API（画面と処理側のやり取り）

### 6.1 決めごと

- ブラウザ → pos-web の `/api/...` → pos-api の `/api/v1/...`。ブラウザは pos-api を直接呼ばない
- ログイン情報（JWT）は pos-web が Cookie に入れ、pos-api へ渡すときに `Authorization: Bearer` ヘッダに付け替える
- 入力は 2 段で確認する。**型や形（数字か、13 桁か）**は pos-web の Zod と pos-api の Pydantic で確認して 400、**業務上の範囲（数量 1〜99 など）**は pos-api のサービス層で確認して 422

### 6.2 一覧

| # | メソッド・パス | 何をするか | 入力 → 出力 | エラー | 要件 |
|---|---|---|---|---|---|
| API-01 | POST `/auth/login` | ログイン | login_id, password → JWT と担当者情報（ブラウザには担当者情報だけ返す） | 401（ID・パスワードの誤り。どちらが違うかは言わない） | FR-01 |
| API-02 | GET `/auth/me` | ログイン中の担当者 | — → 担当者情報 | 401 | FR-01-5 |
| API-03 | GET `/products/{code}` | 商品を探す | 商品コード → 名称・単価 | 404 PRODUCT_NOT_FOUND | FR-03-4, 03-5 |
| API-04 | GET `/members/{code}` | 会員を探す | 会員ID → 氏名（住所などは返さない） | 404 MEMBER_NOT_FOUND | FR-02-4, 02-6 |
| API-05 | POST `/pricing/quote` | 値引き・税・合計を計算 | 会員ID（なしも可）、商品コードと数量の一覧 → 明細ごとの値引き額・小計、税抜合計・税額・税込合計 | 404、422（数量範囲外、税率未設定★） | FR-05-8, FR-06, FR-07 |
| API-06 | POST `/transactions` | 購入を確定して保存 | 画面に表示していた金額を含む購入リスト → 取引番号と合計 | 409 PRICE_MISMATCH（処理側の再計算と 1 円でも違う）、422 CART_EMPTY★ | FR-08、課題指定（照合） |
| API-07 ★ | GET `/health` | 動作確認（DB につながるか） | — → ok / 503 | — | N-03 |

### 6.3 金額の計算ルール（API-05 と API-06 で共通）

1. 行の金額 = 単価 × 数量
2. 会員がいて、期間内の値引きがあれば値引き額を出す（割合なら 行の金額 × 率、金額なら 値 × 数量）。端数と重なりは Q-7・Q-8（★ 仮に「切り捨て」「大きい 1 件」）
3. 小計 = 行の金額 − 値引き額
4. 税抜合計 = 小計の合計。税額 = 税抜合計 × 税率（端数は Q-6、★ 仮に切り捨て）。税込合計 = 税抜合計 + 税額

API-06 では、画面が表示していた金額を受け取り、処理側がこの規則で計算し直して照合します。1 円でも違えば保存せず 409 を返し、正しい金額を画面に送り返します。取引日と取引時刻は 1 回だけ取得し、判定と保存に同じ値を使います。

### 6.4 主な型（TypeScript）

```ts
type Money = number;   // 円の整数
interface ProductInfo { id: number; product_code: string; name: string; unit_price: Money }
interface MemberInfo  { id: number; member_code: string; name: string }
interface QuoteLine   { product_code: string; product_name: string; unit_price: Money; quantity: number;
                        discount: { discount_id: number; type: "percent" | "amount"; value: number; amount: Money } | null;
                        line_total: Money }
interface QuoteResult { tax_rate: number; lines: QuoteLine[]; subtotal_excl_tax: Money; tax_amount: Money; total_incl_tax: Money }
```

---

## 7. 動きの流れ（シーケンス図）

**ログイン（sdr_fig08_1）**: 画面 → BFF → API がパスワードを照合し JWT を発行 → BFF が Cookie に保存。失敗はどちらが違うか言わず 401。

![ログイン](sdr_fig08_1_ログイン.png)

**スキャン追加（sdr_fig08_2）**: バーコードを読む → API-03 で商品を探す → 同じ商品なら数量+1、なければ新しい行 → API-05 で再計算。未登録なら「商品がマスタ未登録です」。

![スキャン追加](sdr_fig08_2_スキャン追加.png)

**会員値引き（sdr_fig08_3）**: API-04 で会員を探す → 登録済みの行も含めて API-05 を呼び直し、値引きを付ける。

![会員値引き](sdr_fig08_3_会員値引き.png)

**購入確定（sdr_fig08_4）**: API-06 が取引日を 1 回取得して再計算・照合 → 一致なら 1 回のトランザクションで保存 → ポップアップ → 閉じて空にする。

![購入確定](sdr_fig08_4_購入確定.png)

---

---

## 8. プログラムの構造（クラス図）

![クラス図](sdr_fig09_クラス図.png)

| 層 | 主なもの | 役割 |
|---|---|---|
| Router | auth / products / members / pricing / transactions | HTTP を受け、入力を確認し、JWT を検証する |
| Service | AuthService | ログインと JWT |
| Service | **PricingService** | 金額計算の正解。税率・値引きの決定と合計の計算。API-05 と API-06 が共用。取引日も自分で作る（Clock から時刻をもらう） |
| Service | TransactionService | 照合と保存 |
| UnitOfWork | Session | データベースのトランザクション境界。接続を使い回す（N-04） |
| Model | 8 テーブルに対応するクラス | — |

`Clock` は「今の UTC 時刻を返すだけ」の部品で、テストでは好きな時刻に固定できます。

---

## 9. 決めた値（入力の上限・下限）

要求に書いてあるのは数量の 1〜99 だけです。それ以外は ★ 仮の値です。値は `shared/limits.json` に 1 か所で持ち、画面側と処理側の両方が読みます。

| 定数 | 値 | 意味 | 根拠 |
|---|---|---|---|
| QTY_MIN / QTY_MAX | 1 / 99 | 数量 | FR-05-6, 05-7（要求） |
| CART_MAX_LINES ★ | 100 | 1 回の会計の商品種類数 | 提案 |
| PRODUCT_CODE_MAX ★ | 13 桁の数字 | 商品コード | Q-21 |
| MEMBER_CODE_MAX ★ | 32 文字の英数字 | 会員ID | Q-21 |
| LOGIN_ID_MAX / PASSWORD_MIN / MAX ★ | 32 / 8 / 64 | 認証 | Q-11 |
| PRICE_MAX ★ | 9,999,999 円 | 単価・値引き額 | 実用上の上限 |
| TAX_ROUNDING / DISCOUNT_ROUNDING ★ | 切り捨て | 端数 | Q-6, Q-7 |
| DISCOUNT_SELECTION ★ | 大きい 1 件 | 値引きが重なったとき | Q-8 |
| JWT_TTL_HOURS ★ | 8 時間 | ログインの有効期間 | — |
| BUSINESS_TIMEZONE | Asia/Tokyo | 取引日を作る基準 | 5 章 |
| SCAN_DEBOUNCE_MS ★ | 1,500 | 同じバーコードの連続検出を無視する時間 | — |
| BODY_MAX_BYTES ★ | 1 MB | 送信データの上限 | セキュリティ |

---

## 10. エラーの扱い

エラーはすべて `{ error: { code, message, details } }` の形で返し、画面は `code` を見て文言を決めます。

| コード | HTTP | いつ | 画面の文言 | 要件 |
|---|---|---|---|---|
| AUTH_INVALID_CREDENTIALS | 401 | ID か パスワードが違う | 担当者IDまたはパスワードが違います | FR-01-4 |
| AUTH_REQUIRED | 401 | ログインしていない・期限切れ | 再度ログインしてください | — |
| VALIDATION_ERROR | 400 | 型・形が不正 | 入力内容に誤りがあります | — |
| PRODUCT_NOT_FOUND | 404 | 商品が未登録 | 商品がマスタ未登録です | FR-03-5 |
| MEMBER_NOT_FOUND | 404 | 会員が未登録 | 該当する会員が見つかりません（その後は Q-3） | FR-02-6 |
| QUANTITY_OUT_OF_RANGE | 422 | 数量が 1〜99 の外 | 数量は 1〜99 で指定してください | FR-05-6, 05-7 |
| CART_EMPTY ★ | 422 | 明細が 0 行 | 商品が登録されていません | Q-4 |
| TAX_RATE_NOT_CONFIGURED ★ | 422 | 税率が未設定 | 消費税率が設定されていません | FR-07-2 |
| PRICE_MISMATCH | 409 | 画面と処理側の金額が違う | 金額が更新されました。内容を確認して再度購入してください | 課題指定 |
| INTERNAL_ERROR / SERVICE_UNAVAILABLE | 500 / 503 | 想定外・DB 接続不可 | 処理に失敗しました／サービスに接続できません | N-02 |

画面だけのもの: カメラが使えないときは「手入力で登録してください」と案内します（FR-03-3）。
API-06 の保存中にエラーが起きたら、途中まで保存せずすべて取り消します（N-02）。

---

## 11. セキュリティ（課題の指定項目）

| 指定 | 対策 |
|---|---|
| ログイン — JWT トークン | 処理側が署名付きの JWT（ログイン済みの証明書のような文字列）を発行。有効期間 8 時間 ★。pos-web が **HttpOnly Cookie**（JavaScript から読めない Cookie）に保存し、ブラウザの JavaScript には見せない |
| ログイン — 認証認可 | パスワードは bcrypt でハッシュ化して保存（★ Q-11）。失敗理由は区別しない。利用者はレジ担当者だけなので権限の区分は設けない（Q-10）。ログイン以外のすべての API で JWT を検証 |
| BFF（リバースプロキシ） | ブラウザは pos-web だけと通信し、pos-api の場所を知らない。pos-web が Cookie を Bearer ヘッダに付け替え、入力を Zod で確認してから中継 |
| CORS | pos-api は pos-web の URL からの要求だけ許可し、`*` は使わない。メソッドは GET / POST、ヘッダは Authorization と Content-Type だけ |
| Backend でも計算し Frontend の値と照合 | 値引き・税率・合計の計算は PricingService だけが行う。確定時に画面の金額を受け取り、計算し直して 1 円単位で照合。違えば保存せず 409 |
| Swagger Docs 非表示 | 本番では API の説明ページ（/docs, /openapi.json）を無効にする。開発環境だけ有効 |
| SQL インジェクション — 型定義（TypeScript） | Zod で「商品コードは数字だけ」「会員IDは英数字だけ」「数量は整数」のように型・文字種・長さを確認。SQL の断片になる文字列を通さない |
| SQL インジェクション — ORM | SQLAlchemy を使い、値は必ずバインド変数で渡す。文字列をつなげて SQL を作らない。Pydantic でも同じ確認をする |
| ライブラリの脆弱性 — バージョン調査 | 2026-09-07 時点の最新版を採用し、OSV.dev（公開の脆弱性データベース）に照会。**14 ライブラリすべて既知の脆弱性 0 件**。TypeScript は 7.0 が出ているが Next.js との互換が未確認のため 5.9 を採用。CI で `npm audit` / `pip-audit` を回す |

主な採用バージョン: Next.js 16.3 / React 19.2 / TypeScript 5.9 / Zod 4.5 / @zxing/library 0.23 / FastAPI 0.141 / SQLAlchemy 2.0 / Pydantic 2.13 / PyMySQL 1.2 / PyJWT 2.13 / bcrypt 5.0 / Python 3.11 / Node 24。

---

## 12. 対応表（ヌケモレの確認）

### 12.1 課題の指定項目 → この文書

| 指定 | 章 | 図・成果物 |
|---|---|---|
| ユースケース図 | 2 | sdr_fig03 |
| アクティビティ図 | 3 | sdr_fig04 |
| シーケンス図 | 7 | sdr_fig08_1〜4 |
| クラス図 | 8 | sdr_fig09 |
| ER 図 | 5 | sdr_fig06 |
| 入力値・商品数の上限下限 | 9 | 定数表 |
| エラー処理 | 10 | コード表 |
| API 一覧（入力の型、出力） | 6 | API-01〜07、型定義 |
| JWT／認証認可／BFF／CORS／照合／Swagger 非表示／SQLi 対策／バージョン調査 | 11 | 対策表 |

### 12.2 要件 → この文書

| 要件 | 設計 |
|---|---|
| FR-01 | UC-01、API-01/02、SC-01、AuthService、11 章 |
| FR-02 | UC-02、API-04/05、MemberPanel、7 章（会員値引き） |
| FR-03 | UC-03/04、API-03、ProductEntryPanel、CameraPreview、7 章（スキャン） |
| FR-04 | 4 章の状態管理、API-05 |
| FR-05 | UC-05、CartTable、SelectedItemPanel、QTY_MIN/MAX |
| FR-06 | UC-07、6.3 計算ルール、PricingService、discounts |
| FR-07 | API-05、tax_rates、ResultPopup |
| FR-08 | UC-06、API-06、transactions / transaction_items、7 章（購入確定） |
| FR-09 | 5 章（変更手段は SQL） |
| SC-01〜02、D-01〜08、DR-1〜4 | 4 章、5 章 |
| N-01〜05 | 1 章（構成）、UnitOfWork、CameraPreview |
| I-1〜I-5、Q-1〜Q-21 | そのまま引き継ぐ。★ は Q に対応 |

---

## 13. 仮に決めたこと（★）と変更履歴

| 事項 | 該当 | 確認事項 |
|---|---|---|
| パスワードのハッシュ化と長さ | staff、PASSWORD_MIN/MAX | Q-11 |
| 単価を税抜で持つ | products.unit_price | Q-6 |
| 商品コード・会員IDの桁数 | PRODUCT_CODE_MAX、MEMBER_CODE_MAX | Q-21 |
| 明細行数・価格の上限 | CART_MAX_LINES、PRICE_MAX | — |
| 端数処理・値引きの選び方 | TAX_ROUNDING 等 | Q-6〜Q-8 |
| 空リストの確定を 422 に | CART_EMPTY | Q-4 |
| JWT 8 時間、動作確認 API、連続検出の抑止 | JWT_TTL_HOURS、API-07、SCAN_DEBOUNCE_MS | — |
| 設定変更は SQL で | 5 章 | Q-9, Q-10 |
| 税率・商品名を取引に写す、削除は論理削除 | 5 章 | Q-13〜Q-15 |
| スキャン商品の自動追加 | CameraPreview | Q-5 |

| 版 | 日付 | 内容 |
|---|---|---|
| v1.0 | 2026-09-14 | 設計仕様書 要求忠実版 v1.1 を初心者向けに短く書き直した。API・テーブル・図の番号は同じ。詳細な型定義・Mermaid ソースは元の文書を参照 |
