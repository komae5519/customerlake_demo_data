"""作ったテーブルの設計書と CustomerLake の設定を、Markdown のノートブックにする。

使い方:
  .venv/bin/python tools/make_design_notebook.py --catalog <カタログ> [--schema-map apparel=<名前>,...] [業種 ...]
      [--out <ローカルのファイル>] [--profile <CLIプロファイル> --workspace-path <ワークスペースのパス>] [--counts]
  --workspace-path: 指定するとワークスペースにノートブックとして入れる（例 /Users/you@databricks.com/customerlake/設計書）
  --counts: テーブルの行数を実際に数えて載せる（--profile が必要）

元にするもの:
  meta/customerlake_design.json  業種・テーブルの用途、想定する施策、CustomerLake の設定
  data/<業種>/_schema.json       テーブルと列の説明（列の論理名はここから作る）
  data/<業種>/*.parquet          列の型
"""
import argparse, datetime, json, re, subprocess, sys
from pathlib import Path

import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import load_to_workspace as L  # EXTRA（イベントテーブル用に足す列）と SQL の実行を使い回す

DESIGN = json.loads((ROOT / "meta" / "customerlake_design.json").read_text())["verticals"]
NAMES = {"apparel": "アパレル小売", "travel": "航空会社 レイクエア", "gaming": "ゲーム ブリック", "insurance": "保険"}


def sql_type(t):
    s = str(t)
    if s.startswith("timestamp"): return "TIMESTAMP"
    if s.startswith("date"): return "DATE"
    return {"int64": "BIGINT", "int32": "INT", "int16": "SMALLINT", "double": "DOUBLE", "float": "FLOAT", "bool": "BOOLEAN",
            "string": "STRING", "large_string": "STRING"}.get(s, s.upper())


def logical(comment, override=None):
    """説明の最初の区切り（「（」「。」）までを論理名にする。"""
    if override: return override
    head = re.split(r"[（(。]", comment, 1)[0].strip()
    return head or comment


def cell(lines):
    return "# MAGIC %md\n" + "\n".join("# MAGIC " + x if x else "# MAGIC" for x in lines)


def esc(s):
    return str(s).replace("|", "／").replace("\n", " ")


def build(catalog, smap, verticals, counts):
    today = datetime.date.today().isoformat()
    cells = []
    head = [f"# CustomerLake デモデータ 設計書（カタログ `{catalog}`）", "",
            f"作成日：{today}　／　作り方：`tools/load_to_workspace.py`（または `setup_demo_data`）でテーブルを作り、このノートブックは `tools/make_design_notebook.py` で生成",
            "", "すべて合成データです（実在の人・会社・製品ではありません）。金額は円。日付は、テーブルを作った日が最新になるようにずらしてあります。", "",
            "| スキーマ | 業種 | 何に使うか | エンティティ（中心のテーブル・主キー） |", "|---|---|---|---|"]
    for v in verticals:
        d = DESIGN[v]; e = d["customerlake"]["entity"]
        head.append(f"| `{smap.get(v, v)}` | {NAMES[v]} | {esc(d['purpose'])} | {e['name']}（`{e['table']}`・`{e['primary_key']}`） |")
    head += ["", "**CustomerLake の設定の流れ**（業種ごとに同じ）",
             "1. エンティティを作る：中心のテーブルと主キーを選ぶ",
             "2. 関係を追加する：ほかのテーブルを主キーでつなぎ、カーディナリティ（1:1 / 1:many など）を選ぶ",
             "3. プロファイル属性を作る：中心のテーブルと 1:1 のテーブルの列から選び、表示名を日本語にする（1:many のテーブルはここでは選ばない）",
             "4. イベントテーブルを設定する：エンティティの「テーブル」タブで対象のテーブルの「︙」→ イベントテーブルを設定（ID の列と TIMESTAMP 型の日時の列を選ぶ）",
             "5. 集計する属性を作る：属性タブの「＋新しい属性」で Genie に普段の言葉で頼む",
             "6. オーディエンスを作る：Genie に文章で頼み、内訳を見て、追加で頼んで絞る"]
    cells.append(cell(head))

    for v in verticals:
        d = DESIGN[v]; cl = d["customerlake"]; schema = smap.get(v, v)
        meta = json.loads((ROOT / "data" / d["folder"] / "_schema.json").read_text())
        lines = [f"## {NAMES[v]}（スキーマ `{catalog}.{schema}`）", "", f"**ビジネスドメイン**：{d['domain']}", "",
                 f"**用途**：{d['purpose']}", "", "**想定するマーケティング施策**"] + [f"- {u}" for u in d["use_cases"]]
        lines += ["", "### テーブル一覧", "",
                  "| テーブル | 役割 | 用途 | 説明 |" + (" 行数 |" if counts else ""), "|---|---|---|---|" + ("---|" if counts else "")]
        for t, tm in d["tables"].items():
            row = f"| `{t}` | {tm['role']} | {esc(tm['purpose'])} | {esc(meta[t]['comment'])} |"
            if counts:
                n = counts.get((schema, t))
                row += f" {int(n):,} |" if n is not None else " — |"
            lines.append(row)
        cells.append(cell(lines))

        for t in d["tables"]:
            arrow = pq.read_schema(ROOT / "data" / d["folder"] / f"{t}.parquet")
            types = {f.name: sql_type(f.type) for f in arrow}
            extra = {n: ("TIMESTAMP" if "TIMESTAMP" in e else "STRING", c) for n, e, c in L.EXTRA.get((v, t), [])}
            lines = [f"#### `{catalog}.{schema}.{t}`", "", esc(meta[t]["comment"]), "",
                     "| カラム物理名 | カラム論理名 | 型 | 説明 |", "|---|---|---|---|"]
            for n, c in meta[t]["columns"].items():
                lines.append(f"| `{n}` | {esc(logical(c, d['logical_names'].get(n)))} | {types.get(n, '')} | {esc(c)} |")
            for n, (ty, c) in extra.items():
                lines.append(f"| `{n}` | {esc(logical(c))} | {ty} | {esc(c)} |")
            cells.append(cell(lines))

        e = cl["entity"]
        lines = [f"### CustomerLake の設定（{NAMES[v]}）", "", "**エンティティ**", "", "| 項目 | 値 |", "|---|---|",
                 f"| 名前 | {e['name']} |", f"| 説明 | {esc(e['description'])} |", f"| テーブル | `{catalog}.{schema}.{e['table']}` |",
                 f"| 主キー | `{e['primary_key']}` |", "", "**関係（つなぐテーブル）**", "", "| テーブル | カーディナリティ | 結合条件 |", "|---|---|---|"]
        lines += [f"| `{r['table']}` | {r['cardinality']} | `{r['join']}` |" for r in cl["relationships"]]
        lines += ["", "**イベントテーブル**（「テーブル」タブ → 対象のテーブルの「︙」→ イベントテーブルを設定）", "",
                  "| テーブル | 名前 | イベント ID の列 | 日時の列 | 説明 |", "|---|---|---|---|---|"]
        lines += [f"| `{x['table']}` | {x['name']} | `{x['event_id']}` | `{x['timestamp']}` | {esc(x['description'])} |" for x in cl["event_tables"]]
        lines += ["", "**プロファイル属性**（エンティティ作成の「属性を定義する」で選ぶ列と表示名）", "", "| テーブル | 列 | 表示名 |", "|---|---|---|"]
        for t, attrs in cl["profile_attributes"].items():
            lines += [f"| `{t}` | `{c}` | {n} |" for c, n in attrs.items()]
        if cl["aggregate_attributes"]:
            lines += ["", "**集計する属性**（属性タブの「＋新しい属性」で Genie に頼む）", "", "| 表示名 | 元のテーブル | 作り方 | Genie に頼む文章 |", "|---|---|---|---|"]
            lines += [f"| {x['name']} | `{x['source']}` | {esc(x['how'])} | {esc(x['genie_prompt'])} |" for x in cl["aggregate_attributes"]]
        lines += ["", "**デモで作るオーディエンス**", "", "| オーディエンス | Genie に入力する文章 | 見る内訳 | 続けて入力する文章 |", "|---|---|---|---|"]
        lines += [f"| {x['name']} | {esc(x['prompt'])} | {x['breakdown']} | {esc(x['refine'])} |" for x in cl["audiences"]]
        cells.append(cell(lines))

    cells.append(cell(["## テーブルがそろっているか確かめる", "", "下のセルを実行すると、各テーブルの行数が出ます。"]))
    fq = [f"{catalog}.{smap.get(v, v)}.{t}" for v in verticals for t in DESIGN[v]["tables"]]
    cells.append("tables = " + json.dumps(fq, ensure_ascii=False, indent=1) + "\n" +
                 "display(spark.createDataFrame([(t, spark.table(t).count()) for t in tables], 'テーブル string, 行数 long'))")
    return "# Databricks notebook source\n" + "\n\n# COMMAND ----------\n\n".join(cells) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalog", required=True); ap.add_argument("--schema-map", default="")
    ap.add_argument("--out", default=str(ROOT / "build" / "customerlake_design.py"))
    ap.add_argument("--profile"); ap.add_argument("--workspace-path"); ap.add_argument("--warehouse"); ap.add_argument("--counts", action="store_true")
    ap.add_argument("verticals", nargs="*", default=list(DESIGN))
    a = ap.parse_args()
    smap = dict(kv.split("=", 1) for kv in a.schema_map.split(",") if kv.strip())
    counts = {}
    if a.counts:
        if not a.profile: sys.exit("--counts には --profile が必要です")
        wh = a.warehouse or L.pick_warehouse(a.profile)
        for v in a.verticals:
            s = smap.get(v, v)
            for t in DESIGN[v]["tables"]:
                counts[(s, t)] = L.sql(a.profile, wh, f"SELECT count(*) FROM `{a.catalog}`.`{s}`.`{t}`")[0][0]
    out = Path(a.out); out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(build(a.catalog, smap, a.verticals, counts), encoding="utf-8")
    print(f"ノートブックを書き出した: {out}")
    if a.workspace_path:
        if not a.profile: sys.exit("--workspace-path には --profile が必要です")
        parent = a.workspace_path.rsplit("/", 1)[0]
        subprocess.run(["databricks", "workspace", "mkdirs", parent, "--profile", a.profile], check=True)
        subprocess.run(["databricks", "workspace", "import", a.workspace_path, "--file", str(out), "--language", "PYTHON",
                        "--format", "SOURCE", "--overwrite", "--profile", a.profile], check=True)
        print(f"ワークスペースに入れた: {a.workspace_path}")


if __name__ == "__main__":
    main()
