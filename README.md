# customerlake_demo_data
CustomerLake｜業種別CDPデータサンプル（日本語版）

CustomerLake（Campaign Agents / Profile Agents）のデモを、日本語のデータで触れるようにするためのデータセットです。
グローバルの CustomerLake デモ環境のデータ（`customer_catalog`）を元に、日本向けに作り直しました。

- すべて合成データです。実在の人・会社・製品ではありません
- 氏名・住所・電話は日本の形式、金額は円です
- 件数と期間は元のデータのままです（期間を使った分析ができるように、間引いていません）
- 日付は、テーブルを作るときに「最新の日付が今日」になるようにずらします

## 業種とテーブル

| スキーマ | 業種 | テーブル（行数） | 顧客のテーブルと結合キー |
|---|---|---|---|
| `apparel` | アパレル小売 | users 16万 / transactions 294万 / loyalty_accounts 11万 / subscriptions 4万 / user_product_affinity 71万 | `users` / `user_id` |
| `travel` | 航空会社「レイクエア」 | users 6万 / bookings 49万 / flight_segments 226万 / ancillary_purchases 12万 / loyalty_activity 34万 / users_attended_event 20 | `users` / `user_id` |
| `gaming` | ゲーム「ブリック」シリーズ | users 2万 / game_sessions 58万 / tactics_matches 4万 / transactions 5千 / marketing_events 2万 | `users` / `user_id` |
| `insurance` | 保険 | members_golden 5万 / member_source_records 8万（名寄せ前）/ policies 9万 / claims 3万 / interactions 48万 / campaign_activity 7万 / distribution_partners 3千 | `members_golden` / `member_id` |

テーブルと列には、すべて日本語の説明が付きます（CustomerLake の Genie が属性やオーディエンスを作るときの手がかりになります）。

`insurance.member_source_records` は名寄せの練習用です。同じ契約者が複数のシステムに、表記がゆれた形で登録されています（名がカナやローマ字、電話番号のハイフンなし、住所の「丁目・番・号」表記、メールの空欄など）。`true_member_id` が正解です。

## 自分の環境に作る

### A. コーディングエージェントに頼む（おすすめ）
Claude Code や Codex でこのリポジトリを開き、「CustomerLake のデモデータを用意して」と頼みます。エージェントが次の順に聞いてから作ります（手順は `.claude/skills/customerlake-jp-demo-data/SKILL.md`）。

1. どのワークスペースに作るか
2. カタログ（既存のものを使うか、新しく作るか）
3. スキーマ名（既定は `apparel` `travel` `gaming` `insurance`。変えたい名前や、不要な業種があれば伝える）
4. 設計書のノートブックの保存先

最後に、作ったテーブルの設計（ビジネスドメイン・用途・想定する施策・カラムの物理名と論理名）と、CustomerLake の設定（エンティティ・関係・イベントテーブル・プロファイル属性・集計する属性・デモで作るオーディエンス）をまとめたノートブックが、ワークスペースに入ります。

### B. ノートブックで（ワークスペースの中だけで完結）
1. このリポジトリをワークスペースの Git フォルダとして追加する
2. `setup_demo_data` を開き、先頭の `CATALOG`（と、スキーマ名を変えるなら `SCHEMA_MAP`）を変える
3. すべてのセルを実行する（サーバーレスで動きます。所要時間は数分〜十数分）

### C. ローカルから自分で実行する
```bash
uv venv .venv && uv pip install --python .venv/bin/python pyarrow pandas
# データを入れる（--schema-map でスキーマ名を変えられる。--create-catalog でカタログがなければ作る）
.venv/bin/python -I tools/load_to_workspace.py --profile <CLIプロファイル> --catalog <カタログ> [--schema-map apparel=retail_jp] [apparel travel gaming insurance]
# 設計書のノートブックを出す
.venv/bin/python -I tools/make_design_notebook.py --catalog <カタログ> [--schema-map ...] --profile <CLIプロファイル> --counts --workspace-path "/Users/<メール>/customerlake-jp-demo/CustomerLake_設計書"
```
`databricks auth login` 済みのプロファイルと、`CREATE SCHEMA` できるカタログが必要です。SQL ウェアハウスは自動で選びます（`--warehouse` で指定も可）。

カタログを新しく作るとき、Default Storage の環境では SQL から作れないことがあります。そのときは Catalog Explorer の「+」→「Create catalog」で Default Storage を選んで作ってください。FEVM でカタログを作る権限がない場合は、go/fevm の Template Catalog →「Standalone Catalog」で作れます。

### イベントテーブル用に足してある列
CustomerLake のイベントテーブルは、日時の列が TIMESTAMP 型で、1行を一意に表す ID の列が必要です。元のデータに日付（DATE）しかない表や、ID が一意でない表には、作るときに次の列を足します。

| テーブル | 足す列 |
|---|---|
| apparel.transactions | `order_ts`（注文日の0時） |
| gaming.game_sessions | `session_id`、`activity_ts` |
| gaming.tactics_matches | `match_event_id`（user_id と match_id をつないだもの） |
| travel.ancillary_purchases | `purchase_ts` |
| travel.loyalty_activity | `activity_ts` |
| insurance.campaign_activity | `send_ts` |

## フォルダの中身

| パス | 内容 |
|---|---|
| `data/<業種>/*.parquet` | 日本語版のデータ（zstd 圧縮） |
| `data/<業種>/_schema.json` | テーブルと列の日本語の説明 |
| `setup_demo_data.py` | 準備用のノートブック |
| `tools/load_to_workspace.py` | 準備用のスクリプト（ローカル実行） |
| `tools/make_design_notebook.py` | 設計書のノートブックを作るスクリプト |
| `meta/customerlake_design.json` | 業種・テーブルの用途、想定する施策、CustomerLake の設定（設計書の元） |
| `.claude/skills/customerlake-jp-demo-data/` | エージェント用の手順（スキル） |
| `AGENTS.md` / `CLAUDE.md` | エージェントへの案内 |
| `tools/localize_*.py`, `tools/jp_common.py` | 元データから日本語版を作るスクリプト（作り直すとき用） |
| `tools/export_source.py` | 元データの書き出し（グローバルのデモ環境を読むだけ。書き込みはしない） |

## 元データからの主な変更

- アパレル：元はペット用品店のデータ。カテゴリ（トップス、ボトムス、アウターなど15種）、定期便（洋服レンタル、インナー定期便など12種）、解約理由をアパレル向けに置き換え
- トラベル：実在の航空会社・提携ブランドを架空の名前に、空港を日本発着中心の14空港に置き換え。会員の約7割を日本在住に
- ゲーム：実在のゲーム・キャラクター・アイテムの名前を架空のものに置き換え。キャンペーン名は月を外して「第N弾」に
- 保険：保険の種類を日本の商品名（自動車保険、火災保険、生命保険など）に、代理店名を架空の日本の名前に置き換え
