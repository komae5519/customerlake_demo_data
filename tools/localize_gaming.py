"""ゲームの日本語版を作る。元はグローバルの cdp_gaming（実在のゲームの名前を含む）。

ゲーム名・キャラクター名・アイテム名・列名に入っている実在の製品名は、架空のゲーム「ブリック」シリーズに置き換える。
プレイヤーは日本在住、金額は円。キャンペーン名は月を外して「第N弾」にする（日付を後でずらしても食い違わないように）。
"""
import json
from pathlib import Path
import pandas as pd
from jp_common import person, to_jpy, remap, pick, rng_for, USD_JPY

ROOT = Path(__file__).resolve().parent.parent
SRC, OUT = ROOT / "raw/cdp_gaming", ROOT / "data/gaming"
OUT.mkdir(parents=True, exist_ok=True)

GAME_KEY = {"lol": "arena", "tft": "tactics", "lor": "cards"}
GAME_NAME = {"League of Legends": "ブリックアリーナ", "Teamfight Tactics": "ブリックタクティクス", "Legends of Runeterra": "ブリックカード"}
HEROES = ["ヴァルド", "セイラ", "ルミナ", "ジェイク", "ミオ", "ゼクス", "ヴィオラ", "リヴィア", "トレス", "ボルト", "ハヤテ", "アカネ",
          "リーフ", "カグラ", "シオン", "レイジ", "ツクヨ", "ガロウ", "ミズキ", "ライガ", "ソラ", "ヒビキ", "クオン", "アスカ",
          "ノア", "エルザ", "ダイゴ", "ユキナ", "オウガ", "フウカ", "シキ", "マキナ", "ルカ", "ジン", "サヤ", "ロウ", "ネネ", "タイガ", "イオリ", "ハク"]
ITEM = {"champ_01": "アカネ 解放", "champ_02": "ハヤテ 解放", "champ_03": "ミオ 解放", "champ_04": "ルミナ 解放", "champ_05": "ゼクス 解放",
    "champ_06": "トレス 解放", "champ_07": "セイラ 解放", "champ_08": "ヴァルド 解放",
    "emote_01": "グッド", "emote_02": "ナイスゲーム", "emote_03": "ペンギンダンス", "emote_04": "鈴の音", "emote_05": "ミニペンギン",
    "emote_06": "ばっちり", "emote_07": "理解不能", "emote_08": "ドヤ顔",
    "skin_01": "花霊 アカネ", "skin_02": "サイバー ハヤテ", "skin_03": "星守 ミオ", "skin_04": "エレメンタル ルミナ", "skin_05": "銀河の剣士 ゼクス",
    "skin_06": "荒野の決闘 トレス", "skin_07": "アイドル セイラ", "skin_08": "ヘヴィメタル ヴァルド", "skin_09": "魔導学院 ヴィオラ",
    "skin_10": "魔導学院 ジェイク", "skin_11": "魔導学院 ミオ", "skin_12": "ゲームボス ボルト", "skin_13": "暗黒星 トレス",
    "skin_14": "夏祭り リーフ", "skin_15": "夜明け リヴィア", "skin_16": "宵闇 ハヤテ",
    "vc_rp10": "ジェム 1,500個", "vc_rp100": "ジェム 15,000個", "vc_rp25": "ジェム 3,750個", "vc_rp5": "ジェム 750個"}
ITEM_TYPE = {"Skin": "スキン", "Champion": "キャラクター", "Emote": "エモート", "Virtual Currency": "ゲーム内通貨"}
CTYPE = {"Season Launch": "シーズン開幕", "Promotional": "プロモーション", "Event": "イベント", "Battle Pass": "バトルパス",
         "Skin Sale": "スキンセール", "Champion Release": "新キャラクター登場"}
CH = {"In-Game": "ゲーム内", "Social Media": "SNS", "SMS": "SMS", "Email": "メール", "Push Notification": "プッシュ通知"}
EVT = {"View": "表示", "Open": "開封", "Click": "クリック", "Purchase": "購入", "Share": "シェア", "Unsubscribe": "配信停止"}
DEVICE = {"tablet": "タブレット", "desktop": "PC", "console": "家庭用ゲーム機", "mobile": "スマートフォン"}
STATUS = {"Active": "有効", "Inactive": "休眠", "Suspended": "一時停止", "Banned": "利用停止"}
GTYPE = {"standard": "通常", "pairs": "ペア", "pve": "PvE", "tutorial": "チュートリアル"}
SEASON = {"TFTSet17": "シーズン17", "TFTSet15": "シーズン15", "TFTSetTutorial": "チュートリアル"}

def campaign_names():
    """元のキャンペーン名（種類 - チャネル - 月）→「種類（チャネル）第N弾」。同じ種類×チャネルの中で月の順に番号を振る。"""
    names = pd.concat([pd.read_parquet(SRC / "marketing_events.parquet", columns=["campaign_name"]).campaign_name,
                       pd.read_parquet(SRC / "transactions.parquet", columns=["campaign_name"]).campaign_name,
                       pd.read_parquet(SRC / "users.parquet", columns=["install_campaign_name"]).install_campaign_name]).dropna().unique()
    p = pd.DataFrame({"name": names})
    parts = p.name.str.split(" - ", expand=True)
    p["type"], p["ch"], p["month"] = parts[0], parts[1], pd.to_datetime(parts[2], format="%B %Y")
    p = p.sort_values("month")
    p["n"] = p.groupby(["type", "ch"]).cumcount() + 1
    return {r.name: f"{CTYPE[r.type]}（{CH[r.ch]}）第{r.n}弾" for r in p.itertuples()}

CAMP = campaign_names()

def users():
    d = pd.read_parquet(SRC / "users.parquet")
    p = person(d.user_id)
    handle = (p.first_name_romaji.str.capitalize() + (rng_for(d.user_id, "h") * 9000 + 1000).astype(int).astype(str))
    tag = pd.Series(pick(d.user_id, "tag", ["JP1", "JP1", "JP1", "JP1", "777", "000", "GG"]))
    hero = pd.Series(pick(d.lol_top_champion.fillna(""), "hero", HEROES)).where(d.lol_top_champion.notna())
    out = pd.DataFrame({"user_id": d.user_id, "account_id": d.account_id, "first_party_id": d.first_party_id,
        "email": p.email, "username": d.username, "player_name": handle, "tag_line": tag, "player_tag": handle + "#" + tag,
        "first_name": p.first_name, "last_name": p.last_name, "full_name": p.full_name, "date_of_birth": d.date_of_birth,
        "phone": p.phone, "street_address": p.street_address, "city": p.city, "postal_code": p.postal_code,
        "country": "日本", "prefecture": p.prefecture, "preferred_language": "ja-JP",
        "is_email_unique": d.is_email_unique, "is_mailable": d.is_mailable, "account_status": remap(d.account_status, STATUS, "status"),
        "is_fraudster_account": d.is_fraudster_account, "tracking_opt_out": d.tracking_opt_out,
        "registration_date": d.registration_date, "last_login_at": d.last_login_at, "install_date": d.install_date,
        "install_platform": d.install_platform, "install_campaign_name": remap(d.install_campaign_name, CAMP, "install_campaign"),
        "install_channel": remap(d.install_channel, CH, "install_channel"),
        "arena_lifetime_games": d.lol_lifetime_games, "arena_first_seen_date": d.lol_first_seen_date, "arena_last_seen_date": d.lol_last_seen_date,
        "arena_games_90d": d.lol_games_90d, "arena_wins_90d": d.lol_wins_90d, "arena_win_rate_90d": d.lol_win_rate_90d,
        "arena_afk_recent": d.lol_afk_recent, "arena_afk_game_count": d.lol_afk_game_count, "arena_top_hero": hero,
        "lifetime_spend_jpy": to_jpy(d.lifetime_spend_usd.astype(float)), "lifetime_transaction_count": d.lifetime_transaction_count,
        "first_purchase_date": d.first_purchase_date, "last_purchase_date": d.last_purchase_date, "is_payer": d.is_payer})
    return out

def game_sessions():
    d = pd.read_parquet(SRC / "game_sessions.parquet")
    d["game_key"] = remap(d.game_key, GAME_KEY, "game_key"); d["game_name"] = remap(d.game_name, GAME_NAME, "game_name")
    return d

def marketing_events():
    d = pd.read_parquet(SRC / "marketing_events.parquet")
    d["event_type"] = remap(d.event_type, EVT, "event_type"); d["channel"] = remap(d.channel, CH, "channel")
    d["device_type"] = remap(d.device_type, DEVICE, "device"); d["conversion_value"] = to_jpy(d.conversion_value.astype(float))
    d["campaign_name"] = remap(d.campaign_name, CAMP, "campaign"); d["campaign_type"] = remap(d.campaign_type, CTYPE, "ctype")
    d["campaign_channel"] = remap(d.campaign_channel, CH, "cch")
    return d

def tactics_matches():
    d = pd.read_parquet(SRC / "tft_matches.parquet")
    d["match_id"] = "JP1_" + d.match_id.str.split("_").str[1]
    d = d.rename(columns={"tft_set_number": "season_number", "tft_set_core_name": "season_name", "tft_game_type": "game_type"})
    d["season_name"] = remap(d.season_name, SEASON, "season"); d["game_type"] = remap(d.game_type, GTYPE, "game_type")
    return d

def transactions():
    d = pd.read_parquet(SRC / "transactions.parquet")
    d = d.rename(columns={"amount_usd": "amount_jpy", "item_list_price_usd": "item_list_price_jpy"})
    d["amount_jpy"] = (d.amount_jpy.astype(float) * USD_JPY).round(); d["item_list_price_jpy"] = (d.item_list_price_jpy.astype(float) * USD_JPY).round()
    d["item_name"] = remap(d.item_id, ITEM, "item"); d["item_type"] = remap(d.item_type, ITEM_TYPE, "item_type")
    d["campaign_name"] = d.campaign_name.map(lambda x: CAMP.get(x) if isinstance(x, str) else None)
    d["campaign_channel"] = d.campaign_channel.map(lambda x: CH.get(x) if isinstance(x, str) else None)
    return d

SCHEMA = {
  "_schema": "ゲーム会社（架空）のプレイヤーデータ（CustomerLake デモ用の合成データ）。対戦ゲーム「ブリックアリーナ」、オートバトラー「ブリックタクティクス」、カードゲーム「ブリックカード」のプレイ・課金・マーケティング施策への反応。金額は円。",
  "users": {"comment": "プレイヤーマスタ。1行が1人のプレイヤー。arena_* はブリックアリーナでの成績。",
    "columns": {"user_id": "プレイヤーID（主キー）", "account_id": "アカウントID", "first_party_id": "自社の会員ID", "email": "メールアドレス（架空）",
      "username": "ログインユーザー名", "player_name": "ゲーム内の表示名", "tag_line": "表示名に付くタグ", "player_tag": "表示名#タグ（ゲーム内で一意）",
      "first_name": "名", "last_name": "姓", "full_name": "氏名", "date_of_birth": "生年月日", "phone": "携帯電話番号（架空）",
      "street_address": "住所（市区町村以下）", "city": "市区町村", "postal_code": "郵便番号", "country": "国", "prefecture": "都道府県",
      "preferred_language": "表示言語", "is_email_unique": "メールアドレスがほかのプレイヤーと重複していないか", "is_mailable": "メールを送ってよいか",
      "account_status": "アカウントの状態（有効／休眠／一時停止／利用停止）", "is_fraudster_account": "不正アカウントと判定されたか",
      "tracking_opt_out": "トラッキングを拒否しているか", "registration_date": "アカウント登録日", "last_login_at": "最終ログイン日時",
      "install_date": "インストール日", "install_platform": "インストールのきっかけになった広告媒体",
      "install_campaign_name": "インストールのきっかけになったキャンペーン", "install_channel": "インストールのきっかけになったチャネル",
      "arena_lifetime_games": "ブリックアリーナの通算プレイ数", "arena_first_seen_date": "ブリックアリーナを最初に遊んだ日",
      "arena_last_seen_date": "ブリックアリーナを最後に遊んだ日", "arena_games_90d": "直近90日のプレイ数", "arena_wins_90d": "直近90日の勝利数",
      "arena_win_rate_90d": "直近90日の勝率", "arena_afk_recent": "最近、試合を途中で放置したか", "arena_afk_game_count": "途中で放置した試合数",
      "arena_top_hero": "一番よく使うキャラクター", "lifetime_spend_jpy": "累計課金額（円）", "lifetime_transaction_count": "累計課金回数",
      "first_purchase_date": "初めて課金した日", "last_purchase_date": "最後に課金した日", "is_payer": "課金したことがあるか"}},
  "game_sessions": {"comment": "プレイ実績。1行が1人×1ゲーム×1日。",
    "columns": {"user_id": "プレイヤーID（users.user_id）", "game_key": "ゲームのコード（arena／tactics／cards）", "game_name": "ゲーム名",
      "activity_date": "プレイした日", "games_played": "その日のプレイ数", "games_won": "その日の勝利数", "minutes_played": "その日のプレイ時間（分）",
      "afk_games": "途中で放置した試合数"}},
  "tactics_matches": {"comment": "ブリックタクティクスの対戦結果。1行が1人×1試合。",
    "columns": {"user_id": "プレイヤーID（users.user_id）", "match_id": "試合ID", "game_date": "試合日", "game_ts": "試合日時",
      "source_game_ts": "元システムでの記録日時", "placement": "順位（1〜8位）", "is_top4": "4位以内か", "is_win": "1位か",
      "final_level": "最終レベル", "gold_left": "残りゴールド", "last_round": "最後のラウンド", "players_eliminated": "倒したプレイヤー数",
      "time_eliminated_s": "脱落までの時間（秒）", "total_damage_to_players": "ほかのプレイヤーに与えたダメージの合計", "game_length_s": "試合時間（秒）",
      "season_number": "シーズン番号", "season_name": "シーズン名", "game_type": "モード（通常／ペア／PvE／チュートリアル）", "queue_id": "マッチングの種類のID"}},
  "transactions": {"comment": "課金（アイテム購入）。1行が1回の購入。",
    "columns": {"transaction_id": "購入ID（主キー）", "user_id": "プレイヤーID（users.user_id）", "transaction_date": "購入日", "transaction_ts": "購入日時",
      "source_transaction_ts": "元システムでの記録日時", "amount_jpy": "支払額（円）", "is_refunded": "返金されたか", "item_id": "アイテムID",
      "item_name": "アイテム名", "item_type": "アイテムの種類（スキン／キャラクター／エモート／ゲーム内通貨）", "item_list_price_jpy": "定価（円）",
      "campaign_id": "購入につながったキャンペーンのID", "campaign_name": "購入につながったキャンペーン名", "campaign_channel": "そのキャンペーンのチャネル",
      "session_id": "購入したセッションのID"}},
  "marketing_events": {"comment": "マーケティング施策への反応。1行が1回の反応（表示、開封、クリック、購入など）。",
    "columns": {"event_id": "反応ID（主キー）", "user_id": "プレイヤーID（users.user_id）", "account_id": "アカウントID", "event_date": "日付",
      "event_timestamp": "日時", "source_event_timestamp": "元システムでの記録日時", "event_type": "反応の種類（表示／開封／クリック／購入／シェア／配信停止）",
      "channel": "チャネル", "device_type": "端末（スマートフォン／PC／タブレット／家庭用ゲーム機）", "conversion_value": "購入につながった金額（円）",
      "campaign_id": "キャンペーンID", "campaign_name": "キャンペーン名", "campaign_type": "キャンペーンの種類", "campaign_channel": "キャンペーンのチャネル",
      "ad_platform": "広告媒体"}},
}

if __name__ == "__main__":
    for name in ["users", "game_sessions", "tactics_matches", "transactions", "marketing_events"]:
        df = globals()[name]()
        assert set(df.columns) == set(SCHEMA[name]["columns"]), (name, set(df.columns) ^ set(SCHEMA[name]["columns"]))
        df.to_parquet(OUT / f"{name}.parquet", compression="zstd", index=False)
        print(f"{name}\t{len(df)}\t{(OUT / f'{name}.parquet').stat().st_size / 1e6:.1f}MB", flush=True)
    (OUT / "_schema.json").write_text(json.dumps(SCHEMA, ensure_ascii=False, indent=2))
