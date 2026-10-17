# このリポジトリでのエージェントの動き方

CustomerLake のデモ用の日本語データセット（アパレル・航空会社・ゲーム・保険）と、それを Databricks のワークスペースに作る道具一式です。

使う人から「CustomerLake のデモデータを用意して」「自分の環境にデータを入れて」のように頼まれたら、
`.claude/skills/customerlake-jp-demo-data/SKILL.md` の手順どおりに進めてください（Claude Code ではスキルとして自動で読み込まれます。Codex などはこのファイルを読んでから始めてください）。

- 最初に会話で決めること：ワークスペース → カタログ（既存か新規か）→ スキーマ名 → 設計書のノートブックの保存先
- 実行するもの：`tools/load_to_workspace.py`（データを入れる）→ `tools/make_design_notebook.py`（設計書を出す）
- グローバルのデモ環境（fevm-customer）には書き込まないこと。`tools/export_source.py` は読むだけです
