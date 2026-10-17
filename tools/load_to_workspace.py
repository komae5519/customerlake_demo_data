"""日本語版のデータセットを、指定したワークスペースのカタログに作る。

使い方:
  .venv/bin/python tools/load_to_workspace.py --profile <CLIプロファイル> --catalog <カタログ> [--warehouse <ID>]
      [--schema-map apparel=<名前>,travel=<名前>,...] [--create-catalog [--managed-location <パス>]] [業種 ...]
  業種: apparel travel gaming insurance（省略で全部）
  --schema-map: スキーマ名を変えるとき（省略した業種は業種名のまま）
  --create-catalog: カタログがなければ作る（Default Storage の環境では SQL から作れないことがある。そのときは画面から作るよう案内して止まる）

やること（業種ごと）:
  1. <catalog>.<業種> スキーマと、ファイル置き場の Volume（_files）を作る
  2. data/<フォルダ>/*.parquet を Volume に上げる
  3. テーブルを作り直す。日付は「最新の日付が今日」になるようにずらす（期間の長さは変わらない。生年月日はずらさない）
  4. テーブルと列に日本語の説明を付ける
  5. イベントテーブルに使う表で日付しかないものに、日時の列（TIMESTAMP）と ID 列を足す（EXTRA）
"""
import argparse, json, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VERTICALS = {  # スキーマ名: (data の下のフォルダ, 元データの最新日＝今日に合わせる日)
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

def cli(profile, *args, data=None):
    r = subprocess.run(["databricks", *args, "--profile", profile, "-o", "json"], capture_output=True, text=True, input=data)
    if r.returncode: raise RuntimeError(f"{' '.join(args[:3])}: {r.stderr.strip()[:500]}")
    return json.loads(r.stdout) if r.stdout.strip() else {}

def sql(profile, wh, stmt):
    body = json.dumps({"warehouse_id": wh, "statement": stmt, "wait_timeout": "50s"})
    r = cli(profile, "api", "post", "/api/2.0/sql/statements", "--json", body)
    while r["status"]["state"] in ("PENDING", "RUNNING"):
        time.sleep(3); r = cli(profile, "api", "get", f"/api/2.0/sql/statements/{r['statement_id']}")
    if r["status"]["state"] != "SUCCEEDED": raise RuntimeError(f"{stmt[:200]}\n{r['status']}")
    return r.get("result", {}).get("data_array", [])

def q(s):
    return "'" + s.replace("\\", "\\\\").replace("'", "\\'") + "'"

def pick_warehouse(profile):
    whs = cli(profile, "warehouses", "list")
    whs = sorted(whs, key=lambda w: (w.get("state") != "RUNNING", not w.get("enable_serverless_compute", False)))
    if not whs: sys.exit("SQL ウェアハウスがありません。--warehouse で指定してください")
    return whs[0]["id"]

def load(profile, wh, catalog, schema, target=None):
    folder, as_of = VERTICALS[schema]
    target = target or schema
    meta = json.loads((ROOT / "data" / folder / "_schema.json").read_text())
    fq = f"`{catalog}`.`{target}`"
    sql(profile, wh, f"CREATE SCHEMA IF NOT EXISTS {fq} COMMENT {q(meta['_schema'])}")
    sql(profile, wh, f"CREATE VOLUME IF NOT EXISTS {fq}.`_files` COMMENT 'テーブルの元になる Parquet ファイルの置き場'")
    vol = f"/Volumes/{catalog}/{target}/_files"
    shift = sql(profile, wh, f"SELECT datediff(current_date(), DATE'{as_of}')")[0][0]
    print(f"[{schema} → {target}] 日付を {shift} 日ずらす（{as_of} → 今日）", flush=True)
    for table, tm in ((k, v) for k, v in meta.items() if not k.startswith("_")):
        f = ROOT / "data" / folder / f"{table}.parquet"
        subprocess.run(["databricks", "fs", "cp", "--overwrite", str(f), f"dbfs:{vol}/{table}.parquet", "--profile", profile],
                       check=True, capture_output=True)
        src = f"read_files('{vol}/{table}.parquet', format => 'parquet')"
        cols = sql(profile, wh, f"DESCRIBE QUERY SELECT * FROM {src}")
        sel = []
        for name, typ, *_ in cols:
            if name == "_rescued_data": continue
            if name in NO_SHIFT: sel.append(f"`{name}`")
            elif typ == "date": sel.append(f"date_add(`{name}`, {shift}) AS `{name}`")
            elif typ.startswith("timestamp"): sel.append(f"timestampadd(DAY, {shift}, `{name}`) AS `{name}`")
            else: sel.append(f"`{name}`")
        extra = EXTRA.get((schema, table), [])
        body = f"SELECT {', '.join(sel)} FROM {src}"
        if extra:
            body = f"SELECT *, {', '.join(f'{e} AS `{n}`' for n, e, _ in extra)} FROM ({body})"
        sql(profile, wh, f"CREATE OR REPLACE TABLE {fq}.`{table}` COMMENT {q(tm['comment'])} AS {body}")
        comments = {**tm["columns"], **{n: c for n, _, c in extra}}
        alters = ", ".join(f"`{n}` COMMENT {q(c)}" for n, c in comments.items())
        try:
            sql(profile, wh, f"ALTER TABLE {fq}.`{table}` ALTER COLUMN {alters}")
        except RuntimeError:  # 複数列を一度に変えられない環境では1列ずつ
            for n, c in comments.items():
                sql(profile, wh, f"ALTER TABLE {fq}.`{table}` ALTER COLUMN `{n}` COMMENT {q(c)}")
        n = sql(profile, wh, f"SELECT count(*) FROM {fq}.`{table}`")[0][0]
        print(f"  {target}.{table}\t{n} 行", flush=True)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", required=True); ap.add_argument("--catalog", required=True); ap.add_argument("--warehouse")
    ap.add_argument("--schema-map", default="", help="apparel=retail_jp,travel=airline_jp のように指定")
    ap.add_argument("--create-catalog", action="store_true"); ap.add_argument("--managed-location")
    ap.add_argument("schemas", nargs="*", default=list(VERTICALS))
    a = ap.parse_args()
    smap = dict(kv.split("=", 1) for kv in a.schema_map.split(",") if kv.strip())
    unknown = set(smap) - set(VERTICALS)
    if unknown: sys.exit(f"--schema-map の業種が不明です: {unknown}（使えるのは {list(VERTICALS)}）")
    wh = a.warehouse or pick_warehouse(a.profile)
    if a.create_catalog:
        loc = f" MANAGED LOCATION {q(a.managed_location)}" if a.managed_location else ""
        try:
            sql(a.profile, wh, f"CREATE CATALOG IF NOT EXISTS `{a.catalog}`{loc} COMMENT 'CustomerLake デモデータ（日本語版）'")
        except RuntimeError as e:
            sys.exit(f"カタログを SQL で作れませんでした。Catalog Explorer の「+」→「Create catalog」で、Default Storage を選んで作ってから、もう一度実行してください。\n{str(e)[:300]}")
    for s in a.schemas: load(a.profile, wh, a.catalog, s, smap.get(s))

if __name__ == "__main__":
    main()
