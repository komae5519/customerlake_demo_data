"""リテール（アパレル）の日本語版を作る。元はグローバルの cdp_retail（ペット用品店）。

テーブル構成・件数・日付はそのまま。ペット用品の値をアパレルに、米国の個人情報を日本の形式に、ドルを円に置き換える。
出力: data/retail/<table>.parquet と data/retail/_schema.json（テーブルと列の日本語説明）
"""
import json
from pathlib import Path
import pandas as pd
from jp_common import person, to_jpy, remap

ROOT = Path(__file__).resolve().parent.parent
SRC, OUT = ROOT / "raw/cdp_retail", ROOT / "data/retail"
OUT.mkdir(parents=True, exist_ok=True)

CATEGORY = {"CAT-001": "トップス", "CAT-002": "ボトムス", "CAT-003": "アウター", "CAT-004": "ワンピース", "CAT-005": "ニット",
    "CAT-006": "シャツ・ブラウス", "CAT-007": "インナー", "CAT-008": "ソックス・レッグウェア", "CAT-009": "シューズ",
    "CAT-010": "バッグ", "CAT-011": "アクセサリー", "CAT-012": "キッズ", "CAT-013": "スポーツウェア",
    "CAT-014": "ルームウェア", "CAT-015": "帽子・ベルト"}
SUB_SKU = {  # 元の定期購入SKU → (新しいSKU, 商品名)
    "AUTO-DOG-DRY-30LB": ("SUB-RENTAL-STD", "洋服レンタル スタンダード"), "AUTO-DOG-WET-12CT": ("SUB-RENTAL-PRM", "洋服レンタル プレミアム"),
    "AUTO-DOG-DENTAL-CHEWS": ("SUB-STYLING-BOX", "スタイリング提案ボックス"), "AUTO-CAT-DRY-15LB": ("SUB-BASIC-TEE", "ベーシックTシャツ定期便"),
    "AUTO-CAT-WET-24CT": ("SUB-INNER", "インナー定期便"), "AUTO-CAT-LITTER-20LB": ("SUB-SOCKS", "ソックス定期便"),
    "AUTO-CAT-TREATS": ("SUB-LEGWEAR", "ストッキング・タイツ定期便"), "AUTO-FLEA-TICK-DOG": ("SUB-KIDS", "キッズ服定期便"),
    "AUTO-FLEA-TICK-CAT": ("SUB-LOUNGE", "ルームウェア定期便"), "AUTO-BIRD-SEED-5LB": ("SUB-SPORTS", "スポーツウェア定期便"),
    "AUTO-FISH-FLAKES-12OZ": ("SUB-CARE", "衣類ケア用品定期便"), "AUTO-SMALL-PET-PELLETS-10LB": ("SUB-SHOECARE", "シューケア用品定期便")}
CANCEL = {"Too expensive": "価格が高い", "Bad experience": "サービスに不満があった", "Found cheaper alternative": "より安い代わりを見つけた",
    "Switching brands": "他のブランドに乗り換えた", "Pet passed away": "サイズや好みが合わなくなった",
    "Moving / relocating": "引っ越し", "No longer needed": "必要なくなった"}
REG = {"web": "Webサイト", "app": "アプリ", "store": "店舗"}
ORDER_CH = {"in_store": "店舗", "online": "オンライン", "buy_online_pickup_in_store": "ネット注文・店舗受け取り"}
FULFILL = {"in_store_pickup": "店舗受け取り", "ship_to_home": "自宅配送", "same_day_delivery": "当日配送"}
TIER = {"Basic": "レギュラー", "Silver": "シルバー", "Gold": "ゴールド", "Platinum": "プラチナ"}
SUB_STATUS = {"active": "利用中", "paused": "一時停止", "cancelled": "解約"}

def users():
    d = pd.read_parquet(SRC / "users.parquet")
    p = person(d.user_id)
    out = pd.DataFrame({"user_id": d.user_id, "email": p.email, "last_name": p.last_name, "first_name": p.first_name,
        "phone": p.phone, "postal_code": p.postal_code, "prefecture": p.prefecture,
        "registration_channel": remap(d.registration_channel, REG, "registration_channel"),
        "has_style_profile": d.has_pet_profile, "created_at": d.created_at, "updated_at": d.updated_at, "is_active": d.is_active})
    return out

def transactions():
    d = pd.read_parquet(SRC / "transactions.parquet")
    d["net_sales"] = to_jpy(d.net_sales); d["discount_amount"] = to_jpy(d.discount_amount)
    d["order_channel"] = remap(d.order_channel, ORDER_CH, "order_channel")
    d["fulfillment_method"] = remap(d.fulfillment_method, FULFILL, "fulfillment_method")
    return d

def loyalty_accounts():
    d = pd.read_parquet(SRC / "loyalty_accounts.parquet")
    d["tier"] = remap(d.tier, TIER, "tier"); return d

def subscriptions():
    d = pd.read_parquet(SRC / "subscriptions.parquet")
    m = remap(d.product_sku, SUB_SKU, "product_sku")
    d.insert(d.columns.get_loc("product_sku") + 1, "product_name", m.map(lambda x: x[1]))
    d["product_sku"] = m.map(lambda x: x[0])
    d["monthly_revenue"] = to_jpy(d.monthly_revenue)
    d["status"] = remap(d.status, SUB_STATUS, "status")
    d["cancellation_reason"] = remap(d.cancellation_reason, CANCEL, "cancellation_reason")
    return d

def user_product_affinity():
    d = pd.read_parquet(SRC / "user_product_affinity.parquet")
    d["category_name"] = remap(d.category_id, CATEGORY, "category_id"); return d

SCHEMA = {
  "_schema": "アパレル小売の顧客データ（CustomerLake デモ用の合成データ。実在の顧客ではありません）。会員、注文、ポイント会員、定期便、カテゴリ別の関心度の5テーブル。金額は円。",
  "users": {"comment": "会員マスタ。1行が1人の会員。ほかのテーブルとは user_id でつながる。",
    "columns": {"user_id": "会員ID（主キー）", "email": "メールアドレス（架空。example.com）", "last_name": "姓", "first_name": "名",
      "phone": "携帯電話番号（架空）", "postal_code": "郵便番号", "prefecture": "都道府県",
      "registration_channel": "会員登録した経路（Webサイト／アプリ／店舗）", "has_style_profile": "スタイル診断（好みや体型の登録）を済ませているか",
      "created_at": "会員登録日時", "updated_at": "会員情報の最終更新日時", "is_active": "有効な会員か（退会していない）"}},
  "transactions": {"comment": "注文明細。1行が1注文の1商品。店舗とオンラインの両方を含む。",
    "columns": {"order_id": "注文ID（主キー）", "user_id": "会員ID（users.user_id）", "sku_id": "商品SKU", "quantity": "数量",
      "net_sales": "売上金額（円、値引き後）", "order_channel": "注文した経路（店舗／オンライン／ネット注文・店舗受け取り）",
      "store_id": "店舗ID（オンライン注文は空）", "order_date": "注文日", "fulfillment_method": "受け取り方法（店舗受け取り／自宅配送／当日配送）",
      "discount_amount": "値引き額（円）", "is_returned": "返品されたか"}},
  "loyalty_accounts": {"comment": "ポイント会員。ポイントプログラムに入っている会員だけが載る。",
    "columns": {"loyalty_account_id": "ポイント会員ID（主キー）", "user_id": "会員ID（users.user_id）",
      "tier": "会員ランク（レギュラー／シルバー／ゴールド／プラチナ）", "points_balance": "現在のポイント残高",
      "lifetime_points_earned": "これまでに貯めたポイントの合計", "enrolled_at": "ポイント会員になった日時",
      "tier_expiry_date": "今の会員ランクの有効期限", "is_enrolled": "ポイント会員として有効か"}},
  "subscriptions": {"comment": "定期便・レンタルの契約。1行が1契約。",
    "columns": {"subscription_id": "契約ID（主キー）", "user_id": "会員ID（users.user_id）", "product_sku": "定期便の商品SKU",
      "product_name": "定期便の商品名", "frequency_days": "お届けの間隔（日）", "monthly_revenue": "月あたりの売上（円）",
      "status": "契約の状態（利用中／一時停止／解約）", "started_at": "契約開始日時", "next_delivery_date": "次回お届け予定日",
      "cancellation_reason": "解約理由（解約した契約のみ）"}},
  "user_product_affinity": {"comment": "会員ごと・商品カテゴリごとの関心度。1行が1人×1カテゴリ。",
    "columns": {"user_id": "会員ID（users.user_id）", "category_id": "商品カテゴリID", "category_name": "商品カテゴリ名",
      "affinity_score": "関心度スコア（0〜1。高いほど関心が強い）", "purchase_count_12m": "直近12か月の購入回数",
      "browse_count_30d": "直近30日の閲覧回数", "last_purchase_date": "最後に購入した日", "computed_at": "スコアを計算した日時"}},
}

if __name__ == "__main__":
    for name in ["users", "transactions", "loyalty_accounts", "subscriptions", "user_product_affinity"]:
        df = globals()[name]()
        assert set(df.columns) == set(SCHEMA[name]["columns"]), (name, set(df.columns) ^ set(SCHEMA[name]["columns"]))
        df.to_parquet(OUT / f"{name}.parquet", compression="zstd", index=False)
        print(f"{name}\t{len(df)}\t{(OUT / f'{name}.parquet').stat().st_size / 1e6:.1f}MB", flush=True)
    (OUT / "_schema.json").write_text(json.dumps(SCHEMA, ensure_ascii=False, indent=2))
