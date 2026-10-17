# Databricks notebook source
# MAGIC %md
# MAGIC # CustomerLake デモデータ（日本語版）の準備
# MAGIC
# MAGIC このノートブックと同じフォルダの `data/` にある Parquet から、指定したカタログに業種ごとのスキーマとテーブルを作ります。
# MAGIC
# MAGIC | スキーマ | 業種 | 主なテーブル |
# MAGIC |---|---|---|
# MAGIC | `apparel` | アパレル小売 | users（会員）, transactions（注文）, loyalty_accounts, subscriptions, user_product_affinity |
# MAGIC | `travel` | 航空会社 | users, bookings, flight_segments, ancillary_purchases, loyalty_activity |
# MAGIC | `gaming` | ゲーム | users（プレイヤー）, game_sessions, tactics_matches, transactions, marketing_events |
# MAGIC | `insurance` | 保険 | members_golden, member_source_records（名寄せ前）, policies, claims, interactions, campaign_activity, distribution_partners |
# MAGIC
# MAGIC - データはすべて合成データです（実在の人・会社ではありません）。金額は円です
# MAGIC - 日付は「最新の日付が今日」になるようにずらして作ります（期間の長さは変わりません）
# MAGIC - 同じスキーマにもう一度実行すると、テーブルを作り直します
# MAGIC
# MAGIC **使い方**：下の `CATALOG` を自分のカタログ名に変えて、すべてのセルを実行します（サーバーレスで動きます）。

# COMMAND ----------

CATALOG = "jp_customerlake_demo"                      # テーブルを作るカタログ（CREATE SCHEMA の権限が必要）
SCHEMAS = ["apparel", "travel", "gaming", "insurance"]  # 作る業種。不要なものは消す
SCHEMA_MAP = {}                                         # スキーマ名を変えるとき。例 {"apparel": "retail_jp"}（書かない業種は業種名のまま）

# COMMAND ----------

import json, os, shutil

VERTICALS = {  # スキーマ名: (data の下のフォルダ, 元データの最新日)
    "apparel": ("retail", "2026-04-29"), "travel": ("travel", "2026-04-29"),
    "gaming": ("gaming", "2025-12-27"), "insurance": ("insurance", "2026-08-11")}
NO_SHIFT = {"date_of_birth"}
# イベントテーブルの日時の列は TIMESTAMP 型が必須で、イベントの ID 列も要る（CustomerLake の「Set event table」）。
# 元データが DATE しかない表に、日時の列（その日の0時）と ID 列を足す。（業種, 表）: [(列名, 式, 説明)]
EXTRA = {
    ("apparel", "transactions"): [("order_ts", "CAST(order_date AS TIMESTAMP)", "注文日時（イベントテーブル用。order_date の0時）")],
    ("gaming", "game_sessions"): [
        ("session_id", "concat_ws('-', cast(user_id AS string), game_key, cast(activity_date AS string))", "プレイ実績のID（user_id・game_key・activity_date をつないだもの。イベントテーブル用）"),
        ("activity_ts", "CAST(activity_date AS TIMESTAMP)", "プレイした日時（イベントテーブル用。activity_date の0時）")],
    ("gaming", "tactics_matches"): [("match_event_id", "concat_ws('-', cast(user_id AS string), match_id)", "対戦結果のID（user_id・match_id をつないだもの。1試合に複数のプレイヤーがいるため。イベントテーブル用）")],
    ("travel", "ancillary_purchases"): [("purchase_ts", "CAST(purchase_date AS TIMESTAMP)", "購入日時（イベントテーブル用。purchase_date の0時）")],
    ("travel", "loyalty_activity"): [("activity_ts", "CAST(activity_date AS TIMESTAMP)", "マイルが動いた日時（イベントテーブル用。activity_date の0時）")],
    ("insurance", "campaign_activity"): [("send_ts", "CAST(send_date AS TIMESTAMP)", "配信日時（イベントテーブル用。send_date の0時）")],
}

nb_path = dbutils.notebook.entry_point.getDbutils().notebook().getContext().notebookPath().get()
DATA = os.path.join("/Workspace" + os.path.dirname(nb_path), "data")
assert os.path.isdir(DATA), f"data フォルダが見つかりません: {DATA}"

def q(s):
    return "'" + s.replace("\\", "\\\\").replace("'", "\\'") + "'"

def load(schema):
    folder, as_of = VERTICALS[schema]
    target = SCHEMA_MAP.get(schema, schema)
    meta = json.load(open(f"{DATA}/{folder}/_schema.json"))
    fq = f"`{CATALOG}`.`{target}`"
    spark.sql(f"CREATE SCHEMA IF NOT EXISTS {fq} COMMENT {q(meta['_schema'])}")
    spark.sql(f"CREATE VOLUME IF NOT EXISTS {fq}.`_files` COMMENT 'テーブルの元になる Parquet ファイルの置き場'")
    vol = f"/Volumes/{CATALOG}/{target}/_files"
    shift = spark.sql(f"SELECT datediff(current_date(), DATE'{as_of}')").first()[0]
    print(f"[{schema}] 日付を {shift} 日ずらします（{as_of} → 今日）")
    for table, tm in ((k, v) for k, v in meta.items() if not k.startswith("_")):
        shutil.copy(f"{DATA}/{folder}/{table}.parquet", f"{vol}/{table}.parquet")
        df = spark.read.parquet(f"{vol}/{table}.parquet")
        sel = []
        for f in df.schema.fields:
            t = f.dataType.simpleString()
            if f.name in NO_SHIFT: sel.append(f"`{f.name}`")
            elif t == "date": sel.append(f"date_add(`{f.name}`, {shift}) AS `{f.name}`")
            elif t.startswith("timestamp"): sel.append(f"timestampadd(DAY, {shift}, `{f.name}`) AS `{f.name}`")
            else: sel.append(f"`{f.name}`")
        extra = EXTRA.get((schema, table), [])
        body = f"SELECT {', '.join(sel)} FROM parquet.`{vol}/{table}.parquet`"
        if extra:
            body = f"SELECT *, {', '.join(f'{e} AS `{n}`' for n, e, _ in extra)} FROM ({body})"
        spark.sql(f"CREATE OR REPLACE TABLE {fq}.`{table}` COMMENT {q(tm['comment'])} AS {body}")
        for n, c in {**tm["columns"], **{n: c for n, _, c in extra}}.items():
            spark.sql(f"ALTER TABLE {fq}.`{table}` ALTER COLUMN `{n}` COMMENT {q(c)}")
        print(f"  {target}.{table}: {spark.table(f'{fq}.`{table}`').count():,} 行")

for s in SCHEMAS:
    load(s)
print("✅ 完了")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 次にやること
# MAGIC 1. ワークスペースの右上のメニュー（プレビュー）で CustomerLake を有効にする
# MAGIC 2. CustomerLake でエンティティを作る。まずは各スキーマの `users`（保険は `members_golden`）を顧客のエンティティにし、ほかのテーブルを `user_id`（保険は `member_id`）でつなぐ
# MAGIC 3. 属性とオーディエンスを作る（例：「直近90日に2回以上買ったゴールド会員」「国際線のビジネスクラスに乗った会員」）
