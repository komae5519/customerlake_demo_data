"""日本語化の共通部品。氏名・都道府県・郵便番号・電話番号・メールを、ID から決まった値で作る（何度実行しても同じ結果）。"""
import numpy as np
import pandas as pd

USD_JPY = 150  # 金額の換算レート（デモ用の固定値）

SURNAMES = [("佐藤","sato","サトウ"),("鈴木","suzuki","スズキ"),("高橋","takahashi","タカハシ"),("田中","tanaka","タナカ"),("伊藤","ito","イトウ"),("渡辺","watanabe","ワタナベ"),
    ("山本","yamamoto","ヤマモト"),("中村","nakamura","ナカムラ"),("小林","kobayashi","コバヤシ"),("加藤","kato","カトウ"),("吉田","yoshida","ヨシダ"),("山田","yamada","ヤマダ"),
    ("佐々木","sasaki","ササキ"),("山口","yamaguchi","ヤマグチ"),("松本","matsumoto","マツモト"),("井上","inoue","イノウエ"),("木村","kimura","キムラ"),("林","hayashi","ハヤシ"),
    ("斎藤","saito","サイトウ"),("清水","shimizu","シミズ"),("山崎","yamazaki","ヤマザキ"),("森","mori","モリ"),("池田","ikeda","イケダ"),("橋本","hashimoto","ハシモト"),
    ("阿部","abe","アベ"),("石川","ishikawa","イシカワ"),("山下","yamashita","ヤマシタ"),("中島","nakajima","ナカジマ"),("石井","ishii","イシイ"),("小川","ogawa","オガワ"),
    ("前田","maeda","マエダ"),("岡田","okada","オカダ"),("長谷川","hasegawa","ハセガワ"),("藤田","fujita","フジタ"),("後藤","goto","ゴトウ"),("近藤","kondo","コンドウ"),
    ("村上","murakami","ムラカミ"),("遠藤","endo","エンドウ"),("青木","aoki","アオキ"),("坂本","sakamoto","サカモト"),("斉藤","saito","サイトウ"),("福田","fukuda","フクダ"),
    ("太田","ota","オオタ"),("西村","nishimura","ニシムラ"),("藤井","fujii","フジイ"),("金子","kaneko","カネコ"),("岡本","okamoto","オカモト"),("藤原","fujiwara","フジワラ"),
    ("中野","nakano","ナカノ"),("三浦","miura","ミウラ"),("原田","harada","ハラダ"),("中川","nakagawa","ナカガワ"),("松田","matsuda","マツダ"),("竹内","takeuchi","タケウチ"),
    ("小野","ono","オノ"),("田村","tamura","タムラ"),("中山","nakayama","ナカヤマ"),("和田","wada","ワダ"),("石田","ishida","イシダ"),("森田","morita","モリタ")]
GIVEN = [("翔太","shota","ショウタ"),("蓮","ren","レン"),("大翔","hiroto","ヒロト"),("悠真","yuma","ユウマ"),("湊","minato","ミナト"),("陽翔","haruto","ハルト"),("樹","itsuki","イツキ"),
    ("大輔","daisuke","ダイスケ"),("健太","kenta","ケンタ"),("拓也","takuya","タクヤ"),("翼","tsubasa","ツバサ"),("颯太","sota","ソウタ"),("直樹","naoki","ナオキ"),("誠","makoto","マコト"),
    ("浩二","koji","コウジ"),("隆","takashi","タカシ"),("修","osamu","オサム"),("和也","kazuya","カズヤ"),("亮","ryo","リョウ"),("智也","tomoya","トモヤ"),("優斗","yuto","ユウト"),
    ("海斗","kaito","カイト"),("陸","riku","リク"),("慎吾","shingo","シンゴ"),("康介","kosuke","コウスケ"),("達也","tatsuya","タツヤ"),("圭","kei","ケイ"),("哲也","tetsuya","テツヤ"),
    ("剛","tsuyoshi","ツヨシ"),("聡","satoshi","サトシ"),("陽菜","hina","ヒナ"),("結衣","yui","ユイ"),("美咲","misaki","ミサキ"),("さくら","sakura","サクラ"),("葵","aoi","アオイ"),
    ("凛","rin","リン"),("結菜","yuna","ユナ"),("芽依","mei","メイ"),("莉子","riko","リコ"),("美羽","miu","ミウ"),("彩","aya","アヤ"),("愛","ai","アイ"),("恵","megumi","メグミ"),
    ("由美","yumi","ユミ"),("真由美","mayumi","マユミ"),("明美","akemi","アケミ"),("裕子","yuko","ユウコ"),("直美","naomi","ナオミ"),("久美子","kumiko","クミコ"),
    ("智子","tomoko","トモコ"),("香織","kaori","カオリ"),("麻衣","mai","マイ"),("優花","yuka","ユカ"),("七海","nanami","ナナミ"),("花","hana","ハナ"),("舞","mai","マイ"),
    ("千尋","chihiro","チヒロ"),("早紀","saki","サキ"),("瞳","hitomi","ヒトミ"),("奈々","nana","ナナ")]
# 都道府県, 人口（万人）, 郵便番号の上3桁の範囲
PREFS = [("北海道",514,40,99),("青森県",120,30,39),("岩手県",118,20,29),("宮城県",228,980,989),("秋田県",93,10,19),
    ("山形県",104,990,999),("福島県",179,960,979),("茨城県",284,300,319),("栃木県",192,320,329),("群馬県",191,370,379),
    ("埼玉県",734,330,369),("千葉県",627,260,299),("東京都",1404,100,208),("神奈川県",923,210,259),("新潟県",214,940,959),
    ("富山県",102,930,939),("石川県",112,920,929),("福井県",75,910,919),("山梨県",80,400,409),("長野県",202,380,399),
    ("岐阜県",194,500,509),("静岡県",355,410,439),("愛知県",748,440,499),("三重県",172,510,519),("滋賀県",141,520,529),
    ("京都府",255,600,629),("大阪府",878,530,599),("兵庫県",537,650,679),("奈良県",131,630,639),("和歌山県",90,640,649),
    ("鳥取県",54,680,689),("島根県",65,690,699),("岡山県",186,700,719),("広島県",275,720,739),("山口県",131,740,759),
    ("徳島県",70,770,779),("香川県",93,760,769),("愛媛県",131,790,799),("高知県",67,780,789),("福岡県",510,800,839),
    ("佐賀県",80,840,849),("長崎県",128,850,859),("熊本県",172,860,869),("大分県",111,870,879),("宮崎県",105,880,889),
    ("鹿児島県",156,890,899),("沖縄県",147,900,909)]
# 主な市区町村（住所を作るときに使う。都道府県ごとに1つ以上）
CITIES = {"東京都":["新宿区","渋谷区","世田谷区","港区","練馬区","品川区","八王子市"],"神奈川県":["横浜市","川崎市","相模原市","藤沢市"],
    "大阪府":["大阪市","堺市","豊中市","吹田市"],"愛知県":["名古屋市","豊田市","岡崎市"],"埼玉県":["さいたま市","川口市","川越市"],
    "千葉県":["千葉市","船橋市","松戸市","柏市"],"兵庫県":["神戸市","姫路市","西宮市"],"北海道":["札幌市","旭川市","函館市"],
    "福岡県":["福岡市","北九州市","久留米市"],"京都府":["京都市","宇治市"],"宮城県":["仙台市","石巻市"],"広島県":["広島市","福山市"]}

CAPITAL = {"青森県":"青森市","岩手県":"盛岡市","秋田県":"秋田市","山形県":"山形市","福島県":"郡山市","茨城県":"水戸市","栃木県":"宇都宮市",
    "群馬県":"前橋市","新潟県":"新潟市","富山県":"富山市","石川県":"金沢市","福井県":"福井市","山梨県":"甲府市","長野県":"長野市",
    "岐阜県":"岐阜市","静岡県":"静岡市","三重県":"津市","滋賀県":"大津市","奈良県":"奈良市","和歌山県":"和歌山市","鳥取県":"鳥取市",
    "島根県":"松江市","岡山県":"岡山市","山口県":"下関市","徳島県":"徳島市","香川県":"高松市","愛媛県":"松山市","高知県":"高知市",
    "佐賀県":"佐賀市","長崎県":"長崎市","熊本県":"熊本市","大分県":"大分市","宮崎県":"宮崎市","鹿児島県":"鹿児島市","沖縄県":"那覇市"}

def rng_for(ids, salt):
    """ID ごとに決まった乱数（0〜1）を返す。"""
    ids = pd.Series(ids).astype(str)
    h = pd.util.hash_pandas_object(ids + "|" + salt, index=False).to_numpy()
    return (h % 10_000_000) / 10_000_000

def pick(ids, salt, choices, weights=None):
    u = rng_for(ids, salt)
    if weights is None:
        idx = (u * len(choices)).astype(int)
    else:
        cw = np.cumsum(weights) / np.sum(weights)
        idx = np.searchsorted(cw, u, side="right")
    idx = np.minimum(idx, len(choices) - 1)
    return [choices[i] for i in idx]

def person(ids):
    """氏名・ローマ字・都道府県・郵便番号・電話・メールの DataFrame（入力の順番どおり）。"""
    ids = pd.Series(ids).reset_index(drop=True)
    sur = pick(ids, "sur", SURNAMES); giv = pick(ids, "giv", GIVEN)
    pref = pick(ids, "pref", PREFS, [p[1] for p in PREFS])
    u1, u2, u3 = rng_for(ids, "zip"), rng_for(ids, "zip4"), rng_for(ids, "tel")
    zips = [f"{p[2] + int(a * (p[3] - p[2] + 1)):03d}-{int(b * 10000):04d}" for p, a, b in zip(pref, u1, u2)]
    u4 = rng_for(ids, "tel2")
    tel = [f"0{['90', '80', '70'][int(c * 3)]}-{int(c * 1e7) % 10000:04d}-{int(d * 1e7) % 10000:04d}" for c, d in zip(u3, u4)]
    cl = [CITIES[p[0]] if p[0] in CITIES else [CAPITAL[p[0]]] for p in pref]
    city = [c[min(int(u * len(c)), len(c) - 1)] for c, u in zip(cl, rng_for(ids, "city"))]
    chome = [f"{1 + int(a * 5)}-{1 + int(b * 30)}-{1 + int(c * 20)}" for a, b, c in zip(rng_for(ids, "c1"), rng_for(ids, "c2"), rng_for(ids, "c3"))]
    return pd.DataFrame({
        "last_name": [s[0] for s in sur], "first_name": [g[0] for g in giv],
        "last_name_kana": [s[2] for s in sur], "first_name_kana": [g[2] for g in giv],
        "last_name_romaji": [s[1] for s in sur], "first_name_romaji": [g[1] for g in giv],
        "full_name": [s[0] + " " + g[0] for s, g in zip(sur, giv)],
        "email": [f"{g[1]}.{s[1]}{i if str(i).isdigit() else int(u * 1e6)}@example.com" for s, g, i, u in zip(sur, giv, ids, rng_for(ids, "mail"))],
        "phone": tel, "prefecture": [p[0] for p in pref], "postal_code": zips,
        "city": city, "street_address": [f"{c}{a}" for c, a in zip(city, chome)]})

def to_jpy(s, step=10):
    return (np.round(pd.to_numeric(s) * USD_JPY / step) * step).astype("float64")

def remap(s, mapping, name):
    """値の置き換え。対応表にない値が出たら止める（訳し漏れを防ぐ）。"""
    missing = set(pd.Series(s).dropna().unique()) - set(mapping)
    if missing: raise ValueError(f"{name}: 対応表にない値 {sorted(missing)[:10]}")
    return pd.Series(s).map(mapping)
