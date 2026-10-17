"""トラベル（航空会社）の日本語版を作る。元はグローバルの cdp_travel。

実在の航空会社・提携ブランドは架空の名前に置き換える。空港は日本発着中心の14空港に1対1で置き換え、国際線かどうかは置き換え後の空港で付け直す。
会員の国籍は日本中心にする（日本以外の会員は元の英語名のまま）。金額は円。
"""
import json
from pathlib import Path
import pandas as pd
from jp_common import person, to_jpy, remap, pick

ROOT = Path(__file__).resolve().parent.parent
SRC, OUT = ROOT / "raw/cdp_travel", ROOT / "data/travel"
OUT.mkdir(parents=True, exist_ok=True)

AIRPORT = {"ORD": "HND", "DFW": "ITM", "DEN": "CTS", "NRT": "NRT", "YYZ": "ICN", "SEA": "FUK", "ATL": "KIX",
           "LHR": "LHR", "SYD": "SYD", "LAX": "OKA", "JFK": "HNL", "SFO": "NGO", "BOS": "TPE", "CDG": "CDG"}
JP_AIRPORTS = {"HND", "ITM", "CTS", "NRT", "FUK", "KIX", "OKA", "NGO"}
COUNTRY = {"US": "US", "IN": "KR", "ES": "TW", "SG": "SG"}  # それ以外は JP
LANG = {"JP": "ja", "US": "en", "KR": "ko", "TW": "zh", "SG": "en"}
TIER = {"Member": "一般", "Silver": "シルバー", "Gold": "ゴールド", "Platinum": "プラチナ", "Diamond": "ダイヤモンド"}
PTYPE = {"bag": "手荷物", "seat": "座席指定", "lounge": "ラウンジ", "upgrade": "アップグレード", "wifi": "機内Wi-Fi"}
PRODUCT = {"First Bag": "受託手荷物（1個目）", "Second Bag": "受託手荷物（2個目）", "Overweight Bag": "重量超過手荷物",
    "Economy Plus": "エコノミープラス席", "Aisle Premium": "通路側の前方座席", "Window Premium": "窓側の前方座席", "Exit Row": "非常口座席",
    "Single Visit": "ラウンジ（1回利用）", "Annual Member": "ラウンジ年会員", "Day Pass": "ラウンジ1日パス",
    "MileagePlus Upgrade": "マイルでアップグレード", "Cabin Upgrade": "上位クラスへのアップグレード",
    "Full Flight WiFi": "機内Wi-Fi（全区間）", "Hourly WiFi": "機内Wi-Fi（1時間）"}
CABIN = {"economy": "エコノミー", "premium_economy": "プレミアムエコノミー", "business": "ビジネス", "first": "ファースト"}
BCH = {"app": "アプリ", "web": "Webサイト", "agent": "旅行代理店", "partner": "提携サイト"}
STATUS = {"completed": "搭乗済み", "cancelled": "欠航", "diverted": "目的地変更", "no_show": "搭乗せず"}
ACT = {"flight_earn": "搭乗で獲得", "partner_earn": "提携先で獲得", "redemption": "特典に交換", "expiry": "失効"}
PARTNER = {"AvisRental": "サクラレンタカー", "AmexTravel": "ミライカード トラベル", "Marriott": "ベイサイドホテルズ",
    "Hilton": "グランドレイクホテル", "Lyft": "スマート配車", "UnitedHotels": "レイクエア ホテルズ", "ChaseCard": "レイクエア カード"}

def route(s):
    a = s.str.split("-", expand=True)
    return remap(a[0], AIRPORT, "route") + "-" + remap(a[1], AIRPORT, "route")

def users(name="users"):
    d = pd.read_parquet(SRC / f"{name}.parquet")
    cc = d.country_code.map(lambda c: COUNTRY.get(c, "JP"))
    p = person(d.user_id); jp = cc.eq("JP")
    out = pd.DataFrame({"user_id": d.user_id,
        "email": p.email.where(jp, d.email), "last_name": p.last_name.where(jp, d.last_name),
        "first_name": p.first_name.where(jp, d.first_name), "phone": p.phone.where(jp, d.phone),
        "date_of_birth": d.date_of_birth, "country_code": cc, "preferred_language": cc.map(LANG),
        "loyalty_id": "LK" + d.loyalty_id.str[2:], "created_at": d.created_at, "updated_at": d.updated_at, "is_active": d.is_active})
    return out

def bookings():
    d = pd.read_parquet(SRC / "bookings.parquet")
    d["route"] = route(d.route)
    ends = d.route.str.split("-", expand=True)
    d["is_international"] = ~(ends[0].isin(JP_AIRPORTS) & ends[1].isin(JP_AIRPORTS))
    d["cabin"] = remap(d.cabin, CABIN, "cabin"); d["booking_channel"] = remap(d.booking_channel, BCH, "booking_channel")
    d["total_fare"] = to_jpy(d.total_fare, 100); d["currency_code"] = "JPY"
    return d

def flight_segments():
    d = pd.read_parquet(SRC / "flight_segments.parquet")
    d["flight_number"] = "LK" + d.flight_number.str[2:]
    d["origin_airport"] = remap(d.origin_airport, AIRPORT, "origin"); d["destination_airport"] = remap(d.destination_airport, AIRPORT, "dest")
    d["status"] = remap(d.status, STATUS, "status")
    return d

def ancillary_purchases():
    d = pd.read_parquet(SRC / "ancillary_purchases.parquet")
    d["purchase_type"] = remap(d.purchase_type, PTYPE, "purchase_type"); d["product_name"] = remap(d.product_name, PRODUCT, "product_name")
    d["revenue"] = to_jpy(d.revenue); d["route"] = route(d.route); d["loyalty_tier"] = remap(d.loyalty_tier, TIER, "tier")
    return d

def loyalty_activity():
    d = pd.read_parquet(SRC / "loyalty_activity.parquet")
    d["loyalty_tier"] = remap(d.loyalty_tier, TIER, "tier"); d["activity_type"] = remap(d.activity_type, ACT, "activity_type")
    d["partner_name"] = remap(d.partner_name, PARTNER, "partner_name")
    return d

USER_COLS = {"user_id": "会員ID（主キー）", "email": "メールアドレス（架空）", "last_name": "姓（日本以外の会員は英語表記）",
    "first_name": "名（日本以外の会員は英語表記）", "phone": "電話番号（架空）", "date_of_birth": "生年月日",
    "country_code": "居住国（JP／US／KR／TW／SG）", "preferred_language": "希望言語（ja／en／ko／zh）",
    "loyalty_id": "マイレージ会員番号", "created_at": "会員登録日時", "updated_at": "会員情報の最終更新日時", "is_active": "有効な会員か"}
SCHEMA = {
  "_schema": "航空会社「レイクエア」（架空）の顧客データ（CustomerLake デモ用の合成データ）。会員、予約、搭乗区間、付帯サービスの購入、マイルの履歴。金額は円。",
  "users": {"comment": "マイレージ会員マスタ。1行が1人の会員。", "columns": USER_COLS},
  "users_attended_event": {"comment": "イベントに参加した会員（20人）。列は users と同じ。", "columns": USER_COLS},
  "bookings": {"comment": "航空券の予約。1行が1予約（往復を含む）。",
    "columns": {"booking_id": "予約ID（主キー）", "user_id": "会員ID（users.user_id）", "route": "路線（出発空港-到着空港のコード）",
      "fare_class": "運賃クラス（予約クラスの記号）", "cabin": "客室クラス（エコノミー／プレミアムエコノミー／ビジネス／ファースト）",
      "departure_date": "出発日", "return_date": "帰りの便の日付", "total_fare": "運賃の合計（円）", "currency_code": "通貨（JPY）",
      "booking_channel": "予約した経路（アプリ／Webサイト／旅行代理店／提携サイト）", "is_international": "国際線か", "booked_at": "予約した日時"}},
  "flight_segments": {"comment": "搭乗区間。1行が1区間（1回のフライト）。遅延や欠航もここでわかる。",
    "columns": {"segment_id": "区間ID（主キー）", "user_id": "会員ID（users.user_id）", "flight_number": "便名（LK はレイクエア）",
      "origin_airport": "出発空港コード", "destination_airport": "到着空港コード", "scheduled_departure": "出発予定日時",
      "actual_departure": "実際の出発日時", "delay_minutes": "遅延（分）", "status": "区間の状態（搭乗済み／欠航／目的地変更／搭乗せず）",
      "miles_flown": "飛行マイル"}},
  "ancillary_purchases": {"comment": "付帯サービスの購入（手荷物、座席指定、ラウンジ、アップグレード、機内Wi-Fi）。",
    "columns": {"purchase_id": "購入ID（主キー）", "user_id": "会員ID（users.user_id）", "booking_id": "予約ID（bookings.booking_id）",
      "purchase_type": "サービスの種類", "product_name": "サービス名", "quantity": "数量", "revenue": "売上（円）",
      "purchase_date": "購入日", "route": "路線", "loyalty_tier": "購入時の会員ランク"}},
  "loyalty_activity": {"comment": "マイルの獲得・利用の履歴。1行が1回の動き。",
    "columns": {"activity_id": "履歴ID（主キー）", "user_id": "会員ID（users.user_id）",
      "loyalty_tier": "会員ランク（一般／シルバー／ゴールド／プラチナ／ダイヤモンド）", "points_earned": "獲得マイル",
      "points_redeemed": "利用マイル", "points_balance": "マイル残高", "activity_type": "動きの種類（搭乗で獲得／提携先で獲得／特典に交換／失効）",
      "partner_name": "提携先の名前（架空）", "activity_date": "日付"}},
}

if __name__ == "__main__":
    jobs = {"users": users, "users_attended_event": lambda: users("users_attended_event"), "bookings": bookings,
            "flight_segments": flight_segments, "ancillary_purchases": ancillary_purchases, "loyalty_activity": loyalty_activity}
    for name, fn in jobs.items():
        df = fn()
        assert set(df.columns) == set(SCHEMA[name]["columns"]), (name, set(df.columns) ^ set(SCHEMA[name]["columns"]))
        df.to_parquet(OUT / f"{name}.parquet", compression="zstd", index=False)
        print(f"{name}\t{len(df)}\t{(OUT / f'{name}.parquet').stat().st_size / 1e6:.1f}MB", flush=True)
    (OUT / "_schema.json").write_text(json.dumps(SCHEMA, ensure_ascii=False, indent=2))
