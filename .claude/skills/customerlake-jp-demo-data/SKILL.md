---
name: customerlake-jp-demo-data
description: CustomerLake デモ用の日本語データセット（アパレル・航空会社・ゲーム・保険）を、指定されたワークスペースのカタログに作り、テーブル設計と CustomerLake の設定をまとめた設計書のノートブックを出力する。「CustomerLake のデモデータを用意して」「日本語のデモデータを自分の FEVM に入れて」「CustomerLake を触るためのデータを作って」で使う。
---

# CustomerLake 日本語デモデータの準備

このリポジトリの `data/` にある Parquet から、指定のカタログに業種ごとのスキーマとテーブルを作る。最後に、テーブル設計と CustomerLake の設定を Markdown で書いた設計書のノートブックをワークスペースに出力する。

使う人はコーディングエージェントを持つ社員（エンジニアとは限らない）。質問は1回に1つか2つ、選択肢と既定値を添えて聞く。用語は短く言い換える（例：スキーマ＝カタログの中のフォルダ）。

## 会話の流れ

### 1. ワークスペース
- 聞く：「どのワークスペースに作りますか？ URL か、CLI のプロファイル名を教えてください」
- 確かめる：`databricks current-user me --profile <P>`
- 失敗したら、本人に `! databricks auth login --host <URL> --profile <P>` を実行してもらう（ブラウザでのログインが要るので代わりにできない）

### 2. カタログ（既存か新規か）
- 先に一覧を見せる：`databricks catalogs list --profile <P>`（`MANAGED_CATALOG` のものだけ、名前と作成者）
- 聞く：「既存のカタログに作りますか？ 新しく作りますか？」
  - FEVM なら、ワークスペースを作ったときに付く既定のカタログ（例 `<ワークスペース名>_catalog`）があることが多い。あればそれを第一候補として示す
- **既存**：`databricks grants get-effective catalog <C> --profile <P>` で、本人に `ALL_PRIVILEGES` か `CREATE_SCHEMA`＋`USE_CATALOG` があるかを確かめる
- **新規**：名前を聞いてから `--create-catalog` を付けて実行する。Default Storage の環境では SQL から作れず止まることがある。そのときは「Catalog Explorer の「+」→「Create catalog」で Default Storage を選んで作ってください」と案内し、作れたら続ける。FEVM で CREATE CATALOG の権限がなければ、go/fevm の Template Catalog →「Standalone Catalog」を案内する（作るのは本人。ワークスペースと同じリージョンを選ぶ）
- 注意：CustomerLake には、データのカタログとは別に「専用のカタログ」（オーディエンスのビューと同期の記録の置き場）も要る。公式の手順では新しく作る。今は作らなくてよく、CustomerLake の設定のときに作ると伝える

### 3. スキーマ（名前の確認）
次の表を見せて聞く：「スキーマはこうしますが、いいですか？ 名前を変えたいものがあれば教えてください。不要な業種があれば外せます」

| 業種 | スキーマ（既定） | 主なテーブル |
|---|---|---|
| アパレル小売 | `apparel` | users 16万 / transactions 294万 / loyalty_accounts / subscriptions / user_product_affinity |
| 航空会社レイクエア | `travel` | users 6万 / bookings / flight_segments 226万 / ancillary_purchases / loyalty_activity / users_attended_event |
| ゲーム ブリック | `gaming` | users 2万 / game_sessions 58万 / tactics_matches / transactions / marketing_events |
| 保険 | `insurance` | members_golden 5万 / policies / claims / interactions 48万 / campaign_activity / member_source_records / distribution_partners |

- 名前を変えるなら `--schema-map apparel=<名前>,travel=<名前>` の形にする（書かない業種は既定のまま）
- 入れる先に同じ名前のスキーマがあれば、`databricks tables list <C> <S> --profile <P>` で中身を見せ、上書きしてよいか確かめる（同名のテーブルは `CREATE OR REPLACE` で作り直す）

### 4. 設計書のノートブックの保存先
- 聞く：「設計書のノートブックをワークスペースのどこに保存しますか？」
- 既定値：`/Users/<本人のメール>/customerlake-jp-demo/CustomerLake_設計書`（メールは手順1の `current-user me` で分かる）

### 5. 実行の前に確認する
ここまでの内容（ワークスペース、カタログ、スキーマ名、保存先）を1つの表で見せて、「この内容で作ります。数分〜十数分かかります」と伝えて了解をもらう。

### 6. データを入れる（バックグラウンドで実行）
```bash
uv venv .venv && uv pip install --python .venv/bin/python pyarrow pandas   # 初回だけ
.venv/bin/python -I tools/load_to_workspace.py --profile <P> --catalog <C> [--schema-map ...] [--create-catalog] [業種 ...]
```
- 行数が README の表と合っているかを見る
- 日付は「今日が最新」になるようにずれる。イベントテーブル用の日時の列（例 `order_ts`）と ID の列（例 `session_id`）も足される

### 7. 設計書のノートブックを出す
```bash
.venv/bin/python -I tools/make_design_notebook.py --catalog <C> [--schema-map ...] [業種 ...] \
  --profile <P> --counts --workspace-path "<保存先>"
```
中身：カタログ全体の一覧 → 業種ごとに、ビジネスドメイン・用途・想定する施策 → テーブル一覧（役割・用途・行数）→ テーブルごとの設計（カラム物理名・論理名・型・説明）→ CustomerLake の設定（エンティティ、関係とカーディナリティ、イベントテーブル、プロファイル属性と表示名、集計する属性と Genie に頼む文章、デモで作るオーディエンス）→ 行数を確かめるセル

### 8. 報告する
- 作ったスキーマとテーブル数、行数の確認結果
- 設計書のノートブックのリンク（`<ワークスペースのURL>/#workspace<保存先>`）
- 次にやること：Previews で「CustomerLake Campaign Agents」を ON にする → CustomerLake を開き、設計書の「CustomerLake の設定」のとおりにエンティティを作る

## 守ること
- グローバルのデモ環境（fevm-customer）には書き込まない。`tools/export_source.py` は読むだけ
- 本人の確認なしに既存のテーブルを上書きしない
- CustomerLake の画面の操作（エンティティの作成など）は API がないので本人がやる。設計書のとおりの値を伝えて手伝う

## CustomerLake の設定でつまずきやすいところ
- イベントテーブルは、関係を追加するときのカーディナリティでは選べない。つないだあと、エンティティの「テーブル」タブで対象のテーブルの「︙」→ イベントテーブルを設定、で登録する。日時の列は TIMESTAMP 型でないと選べない（DATE の列しかない表には、このデータで日時の列を足してある）
- 「属性を定義する」で選ぶのは、中心のテーブルと 1:1 のテーブルの列だけ。1:many のテーブル（注文など）は、あとで「＋新しい属性」から集計して作る
- 表示名は列名から英語で自動入力される。デモでは日本語に直す（設計書の「プロファイル属性」の表示名）
- 1人に複数行あるもの（例：アパレルの関心度の「アウター」）は、件数ではなく最大値で属性にする
- イベントの条件は回数と期間だけで、値（返品されたか＝true など）では絞れない。返品で除外するなら、先に集計属性「過去1年の返品回数」を Genie で作る
- 編集画面の Genie は「条件を追加 → Genie に聞く」から開く。構成（内訳）は更新ボタンを押してから見る
- アパレルのデモの順と人数の目安は README の「デモの流れ（アパレル）」（4,226 → 2,582 → 2,322人）
