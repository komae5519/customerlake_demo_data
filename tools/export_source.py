"""グローバルのデモ環境（fevm-customer の customer_catalog）から、テーブルを読むだけで Parquet に書き出す。

使い方: .venv/bin/python tools/export_source.py <schema> [table ...]
出力:   raw/<schema>/<table>.parquet（zstd）
元の環境には書き込まない（SELECT だけ）。
"""
import json, subprocess, sys, time
from pathlib import Path
import pyarrow as pa, pyarrow.ipc as ipc, pyarrow.parquet as pq, requests

PROFILE, HOST, WH = "fevm-customer", "https://fevm-customer.cloud.databricks.com", "202506b8ec4f8053"
ROOT = Path(__file__).resolve().parent.parent

def token():
    out = subprocess.run(["databricks", "auth", "token", "--profile", PROFILE], capture_output=True, text=True, check=True).stdout
    return json.loads(out)["access_token"]

def run(sql, tok):
    h = {"Authorization": f"Bearer {tok}"}
    r = requests.post(f"{HOST}/api/2.0/sql/statements", headers=h, json={
        "warehouse_id": WH, "statement": sql, "wait_timeout": "50s",
        "disposition": "EXTERNAL_LINKS", "format": "ARROW_STREAM"}).json()
    sid = r["statement_id"]
    while r["status"]["state"] in ("PENDING", "RUNNING"):
        time.sleep(3); r = requests.get(f"{HOST}/api/2.0/sql/statements/{sid}", headers=h).json()
    if r["status"]["state"] != "SUCCEEDED": raise RuntimeError(r["status"])
    tables, chunk = [], r["result"]
    while True:
        for link in chunk.get("external_links", []):
            data = requests.get(link["external_link"]).content
            tables.append(ipc.open_stream(pa.BufferReader(data)).read_all())
        nxt = chunk.get("next_chunk_internal_link") or (chunk.get("external_links") or [{}])[-1].get("next_chunk_internal_link")
        if not nxt: break
        chunk = requests.get(f"{HOST}{nxt}", headers=h).json()
    return pa.concat_tables(tables) if tables else None

def main():
    schema, names = sys.argv[1], sys.argv[2:]
    tok = token()
    if not names:
        meta = json.loads(subprocess.run(["databricks", "tables", "list", "customer_catalog", schema, "--profile", PROFILE, "-o", "json"],
                                         capture_output=True, text=True, check=True).stdout)
        names = [t["name"] for t in meta if t.get("table_type") == "MANAGED"]
    out = ROOT / "raw" / schema; out.mkdir(parents=True, exist_ok=True)
    for n in names:
        t = run(f"SELECT * FROM customer_catalog.{schema}.{n}", tok)
        pq.write_table(t, out / f"{n}.parquet", compression="zstd")
        print(f"{schema}.{n}\t{t.num_rows}\t{(out / f'{n}.parquet').stat().st_size/1e6:.1f}MB", flush=True)

if __name__ == "__main__":
    main()
