# customerlake_demo_data
CustomerLake｜業種別CDPデータサンプル（日本語版）

CustomerLake（Campaign Agents / Profile Agents）のデモを、日本語のデータで触れるようにするためのデータセットです。

- すべて合成データです。実在の人・会社・製品ではありません
- 氏名・住所・電話は日本の形式、金額は円です
- 業種ごとに2万〜16万人の顧客と、その行動の履歴があります（「直近30日」のような期間の条件で絞れる量です）
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
CustomerLake のイベントテーブルは、日時の列が TIMESTAMP 型で、1行を一意に表す ID の列が必要です。日付（DATE）の列しかない表や、ID が一意でない表には、作るときに次の列を足します。

| テーブル | 足す列 |
|---|---|
| apparel.transactions | `order_ts`（注文日の0時） |
| gaming.game_sessions | `session_id`、`activity_ts` |
| gaming.tactics_matches | `match_event_id`（user_id と match_id をつないだもの） |
| travel.ancillary_purchases | `purchase_ts` |
| travel.loyalty_activity | `activity_ts` |
| insurance.campaign_activity | `send_ts` |

## デモの流れ（アパレル）
紹介動画「マーケターの仕事は、こう変わる（アパレル編）」と同じ順で見せられるように、設計書のノートブックに値を入れてあります。

| 段階 | 画面での操作 | 人数の目安 |
|---|---|---|
| 1 わたしの施策 | 4つの条件を決める（過去1年に5回以上買った・この30日は買っていない・アウターに関心が高い・返品が多い人は除く） | |
| 2 材料をそろえる | 属性の「＋新しい属性」で Genie に「会員ごとに、過去1年間に返品された注文の数を数えて」 → 過去1年の返品回数 | |
| 3 対象を出す | 新規オーディエンス → Genie に施策の条件を文章で入力 | 4,226人 |
| 4 中身を見て直す | 会員ランクの内訳で (null) 36% → 条件を追加 → Genie に「ポイント会員の人だけに絞って」 | 2,582人 |
| | 続けて「返品回数が2回以上の人は除いて」 | 2,322人 |
| 5 確かめる | View full SQL と Unity Catalog のビュー | |

- 人数は実測値です。Genie の組み立ては毎回少し変わるので、大きくずれたら条件を見直してください
- イベントの条件は回数と期間しか指定できず、「返品された注文」のような値では絞れません。返品で除くために、段階2で集計属性を先に作ります
- 見せたいのは、配信する人数がその場で分かり、条件を変えてもすぐ分かり、それをマーケターが自分でできること

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
