"""インシュアランス（損保・生保）の日本語版を作る。元はグローバルの cdp_insurance。

member_source_records は名寄せの練習用データ。元データの「ゆれ」の種類を見て、日本語で同じ種類のゆれを作る。
- 名が頭文字だけ → 名をカタカナ / 名が大文字 → ローマ字の大文字 / そのほかの違い（愛称など）→ ひらがな
- 姓が大文字 → ローマ字の大文字 / そのほかの違い（途中で切れているなど）→ カタカナ
- メールが別 → 別のフリーメール / 電話のハイフンなし → ハイフンなし / 住所の略記 → 「1丁目2番3号」表記
- 空欄はそのまま空欄
金額は円。
"""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from jp_common import person, to_jpy, remap, pick, rng_for, SURNAMES, PREFS

ROOT = Path(__file__).resolve().parent.parent
SRC, OUT = ROOT / "raw/cdp_insurance", ROOT / "data/insurance"
OUT.mkdir(parents=True, exist_ok=True)

LINE = {"Auto": "自動車保険", "Home": "火災保険", "Life": "生命保険", "Annuity": "個人年金保険", "Pet": "ペット保険", "Umbrella": "個人賠償責任保険"}
PSTATUS = {"Active": "有効", "Lapsed": "失効", "Cancelled": "解約"}
CSTATUS = {"Closed": "支払い完了", "Under Review": "審査中", "In Litigation": "係争中", "Open": "受付"}
CAMPAIGN = {"Umbrella Upsell": "個人賠償責任保険のご案内", "Annuity Retirement Push": "個人年金（老後の資金づくり）のご案内",
    "Multi-Policy Discount": "複数契約割引のご案内", "Home Bundle Offer": "火災保険セットプランのご案内",
    "Life Insurance Awareness": "生命保険の見直しのご案内", "Auto Renewal Reminder": "自動車保険の更新のお知らせ",
    "Win-Back Lapsed": "失効した契約の復活のご案内", "Pet Insurance Cross-sell": "ペット保険のご案内"}
CH = {"Email": "メール", "Direct Mail": "郵送DM", "Meta": "Meta広告", "Push": "プッシュ通知", "Phone": "電話", "Mobile App": "アプリ"}
EVENT = {"App Login": "アプリにログイン", "Web Visit": "Webサイトを訪問", "Bill Paid": "保険料を支払い", "Policy Document View": "契約書類を閲覧",
    "Quote Started": "見積もりを開始", "Quote Abandoned": "見積もりを途中でやめた", "Call Center Contact": "コールセンターに問い合わせ",
    "Life Event: New Home": "ライフイベント：住宅の購入", "Life Event: New Vehicle": "ライフイベント：車の購入",
    "Life Event: Marriage": "ライフイベント：結婚", "Life Event: New Child": "ライフイベント：子どもの誕生",
    "Life Event: Retirement Age": "ライフイベント：定年の年齢に到達"}
PTYPE = {"Independent Agent": "独立系代理店", "Wholesaler": "保険販売会社", "Farm Agent": "地域密着の代理店",
         "Broker-Dealer": "保険仲立人", "Financial Professional": "ファイナンシャルプランナー"}
DOMAINS = ["example.com", "example.co.jp", "example.ne.jp", "example.jp"]

def hira(s):
    return "".join(chr(ord(c) - 0x60) if "ァ" <= c <= "ヶ" else c for c in s)

def golden_people(ids):
    p = person(ids)
    dom = pd.Series(pick(ids, "dom", DOMAINS))
    p["email"] = p.first_name_romaji + "." + p.last_name_romaji + "@" + dom  # 氏名が同じ人はメールも重なる（名寄せを難しくするため、元データと同じ）
    p["street_kanji"] = [a.replace(c, "", 1) for a, c in zip(p.street_address, p.city)]  # 「1-2-3」の部分
    return p

def members_golden(G):
    d = pd.read_parquet(SRC / "members_golden.parquet")
    p = G.loc[d.member_id].reset_index(drop=True)
    return pd.DataFrame({"member_id": d.member_id, "first_name": p.first_name, "last_name": p.last_name, "email": p.email, "phone": p.phone,
        "street_address": p.street_address, "city": p.city, "prefecture": p.prefecture, "postal_code": p.postal_code, "age": d.age,
        "tenure_years": d.tenure_years, "is_mutual_member": d.is_mutual_member, "engagement_score": d.engagement_score,
        "preferred_channel": remap(d.preferred_channel, CH, "preferred_channel"), "email_opt_in": d.email_opt_in,
        "marketing_opt_out": d.marketing_opt_out, "do_not_contact": d.do_not_contact,
        "lifetime_value_jpy": to_jpy(d.lifetime_value_usd, 100), "member_since": d.member_since})

def member_source_records(G):
    s = pd.read_parquet(SRC / "member_source_records.parquet")
    g = pd.read_parquet(SRC / "members_golden.parquet").set_index("member_id")
    o = g.loc[s.true_member_id].reset_index(drop=True)          # 元の英語の正解レコード
    p = G.loc[s.true_member_id].reset_index(drop=True)          # 日本語の正解レコード
    fn, ln = s.first_name.reset_index(drop=True), s.last_name.reset_index(drop=True)
    first = np.select([fn.eq(o.first_name), fn.str.endswith("."), fn.eq(o.first_name.str.upper())],
                      [p.first_name, p.first_name_kana, p.first_name_romaji.str.upper()], p.first_name_kana.map(hira))
    last = np.select([ln.eq(o.last_name), ln.eq(o.last_name.str.upper())], [p.last_name, p.last_name_romaji.str.upper()], p.last_name_kana)
    em = s.email.reset_index(drop=True)
    alt = p.first_name_romaji + (rng_for(s.source_record_id, "m") * 90 + 10).astype(int).astype(str) + "@freemail.example.jp"
    email = np.select([em.isna(), em.eq(o.email)], [None, p.email], alt)
    ph = s.phone.reset_index(drop=True)
    phone = np.select([ph.isna(), ph.eq(o.phone)], [None, p.phone], p.phone.str.replace("-", ""))
    st = s.street_address.reset_index(drop=True)
    chome = p.street_kanji.str.split("-", expand=True)
    long_form = p.city + chome[0] + "丁目" + chome[1] + "番" + chome[2] + "号"
    street = np.where(st.eq(o.street_address), p.street_address, long_form)
    return pd.DataFrame({"source_record_id": s.source_record_id, "source_system": s.source_system, "true_member_id": s.true_member_id,
        "first_name": first, "last_name": last, "email": email, "phone": phone, "street_address": street,
        "prefecture": p.prefecture, "postal_code": p.postal_code, "record_created_date": s.record_created_date})

def policies():
    d = pd.read_parquet(SRC / "policies.parquet").rename(columns={"annual_premium_usd": "annual_premium_jpy"})
    d["policy_line"] = remap(d.policy_line, LINE, "line"); d["policy_status"] = remap(d.policy_status, PSTATUS, "status")
    d["annual_premium_jpy"] = to_jpy(d.annual_premium_jpy, 10); return d

def claims():
    d = pd.read_parquet(SRC / "claims.parquet").rename(columns={"claim_amount_usd": "claim_amount_jpy"})
    d["policy_line"] = remap(d.policy_line, LINE, "line"); d["claim_status"] = remap(d.claim_status, CSTATUS, "claim_status")
    d["claim_amount_jpy"] = to_jpy(d.claim_amount_jpy, 100); return d

def interactions():
    d = pd.read_parquet(SRC / "interactions.parquet")
    d["event_type"] = remap(d.event_type, EVENT, "event_type"); d["channel"] = remap(d.channel, CH, "channel"); return d

def campaign_activity():
    d = pd.read_parquet(SRC / "campaign_activity.parquet")
    d["campaign_name"] = remap(d.campaign_name, CAMPAIGN, "campaign"); d["channel"] = remap(d.channel, CH, "channel"); return d

def distribution_partners():
    d = pd.read_parquet(SRC / "distribution_partners.parquet")
    sur = pd.Series(pick(d.partner_id, "psur", SURNAMES)).map(lambda x: x[0])
    suffix = d.partner_type.map({"Independent Agent": "保険事務所", "Wholesaler": "保険販売", "Farm Agent": "総合保険",
                                 "Broker-Dealer": "保険ブローカー", "Financial Professional": "FP事務所"})
    pref = pd.Series(pick(d.partner_id, "ppref", PREFS, [p[1] for p in PREFS])).map(lambda x: x[0])
    return pd.DataFrame({"partner_id": d.partner_id, "partner_name": sur + suffix, "partner_type": remap(d.partner_type, PTYPE, "ptype"),
        "region_prefecture": pref, "appointed_year": d.appointed_year,
        "partner_status": remap(d.partner_status, {"Active": "有効", "Inactive": "無効"}, "pstatus")})

SCHEMA = {
  "_schema": "保険会社（架空）の契約者データ（CustomerLake デモ用の合成データ）。名寄せ済みの契約者マスタ、名寄せ前のシステム別レコード、契約、保険金請求、行動ログ、キャンペーン、代理店。金額は円。",
  "members_golden": {"comment": "契約者マスタ（名寄せ済みの正しいレコード）。1行が1人の契約者。",
    "columns": {"member_id": "契約者ID（主キー）", "first_name": "名", "last_name": "姓", "email": "メールアドレス（架空）", "phone": "携帯電話番号（架空）",
      "street_address": "住所（市区町村以下）", "city": "市区町村", "prefecture": "都道府県", "postal_code": "郵便番号", "age": "年齢",
      "tenure_years": "契約年数", "is_mutual_member": "相互会社の社員（有配当の契約者）か", "engagement_score": "エンゲージメントスコア（0〜100）",
      "preferred_channel": "希望する連絡方法", "email_opt_in": "メールの受け取りに同意しているか", "marketing_opt_out": "営業の連絡を断っているか",
      "do_not_contact": "連絡禁止か", "lifetime_value_jpy": "顧客生涯価値（円）", "member_since": "最初の契約日"}},
  "member_source_records": {"comment": "名寄せ前のシステム別レコード。1人の契約者が複数のシステムに、表記がゆれた形で登録されている（カナ、ローマ字、ハイフンなし、丁目表記など）。true_member_id が正解。",
    "columns": {"source_record_id": "レコードID（主キー）", "source_system": "登録元のシステム（LEGACY_POLICY_ADMIN＝旧契約管理、AGENT_PORTAL＝代理店ポータル、DIGITAL_SIGNUP＝Web申し込み）",
      "true_member_id": "正解の契約者ID（members_golden.member_id）。名寄せの答え合わせ用", "first_name": "名（表記ゆれあり）", "last_name": "姓（表記ゆれあり）",
      "email": "メールアドレス（空欄や別アドレスあり）", "phone": "電話番号（空欄やハイフンなしあり）", "street_address": "住所（表記ゆれあり）",
      "prefecture": "都道府県", "postal_code": "郵便番号", "record_created_date": "レコードの登録日"}},
  "policies": {"comment": "保険契約。1行が1契約。",
    "columns": {"policy_id": "契約ID（主キー）", "member_id": "契約者ID（members_golden.member_id）", "policy_line": "保険の種類",
      "annual_premium_jpy": "年間保険料（円）", "policy_status": "契約の状態（有効／失効／解約）", "effective_date": "契約開始日", "renewal_date": "次の更新日",
      "partner_id": "担当代理店ID（distribution_partners.partner_id）"}},
  "claims": {"comment": "保険金の請求。1行が1件の請求。",
    "columns": {"claim_id": "請求ID（主キー）", "member_id": "契約者ID", "policy_id": "契約ID（policies.policy_id）", "policy_line": "保険の種類",
      "claim_amount_jpy": "請求額（円）", "claim_status": "請求の状態（受付／審査中／支払い完了／係争中）", "filed_date": "請求日"}},
  "interactions": {"comment": "契約者の行動ログ（アプリ、Web、支払い、問い合わせ、ライフイベント）。1行が1件。",
    "columns": {"interaction_id": "ログID（主キー）", "member_id": "契約者ID", "event_type": "行動の種類", "channel": "チャネル", "event_ts": "日時"}},
  "campaign_activity": {"comment": "キャンペーンの配信と反応。1行が1人への1回の配信。",
    "columns": {"send_id": "配信ID（主キー）", "member_id": "契約者ID", "campaign_name": "キャンペーン名", "channel": "チャネル",
      "send_date": "配信日", "opened": "開封したか", "converted": "申し込みにつながったか"}},
  "distribution_partners": {"comment": "代理店マスタ（架空）。",
    "columns": {"partner_id": "代理店ID（主キー）", "partner_name": "代理店名（架空）", "partner_type": "代理店の種類", "region_prefecture": "担当地域（都道府県）",
      "appointed_year": "委託を始めた年", "partner_status": "状態（有効／無効）"}},
}

if __name__ == "__main__":
    ids = pd.read_parquet(SRC / "members_golden.parquet", columns=["member_id"]).member_id
    G = golden_people(ids).set_index(ids)
    jobs = {"members_golden": lambda: members_golden(G), "member_source_records": lambda: member_source_records(G), "policies": policies,
            "claims": claims, "interactions": interactions, "campaign_activity": campaign_activity, "distribution_partners": distribution_partners}
    for name, fn in jobs.items():
        df = fn()
        assert set(df.columns) == set(SCHEMA[name]["columns"]), (name, set(df.columns) ^ set(SCHEMA[name]["columns"]))
        df.to_parquet(OUT / f"{name}.parquet", compression="zstd", index=False)
        print(f"{name}\t{len(df)}\t{(OUT / f'{name}.parquet').stat().st_size / 1e6:.1f}MB", flush=True)
    (OUT / "_schema.json").write_text(json.dumps(SCHEMA, ensure_ascii=False, indent=2))
