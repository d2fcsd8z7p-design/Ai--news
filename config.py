"""設定。秘密情報は GitHub の Secrets、それ以外は Variables / 環境変数で上書きできます。"""
import os

# ---- ニュースの取得元（AI・IT分野） -------------------------------------
# (表示名, RSS/AtomのURL, 種類)
FEEDS = [
    ("Techmeme", "https://www.techmeme.com/feed.xml", "aggregator"),
    ("TechCrunch", "https://techcrunch.com/feed/", "outlet"),
    ("TechCrunch AI", "https://techcrunch.com/category/artificial-intelligence/feed/", "outlet"),
    ("The Verge", "https://www.theverge.com/rss/index.xml", "outlet"),
    ("Ars Technica", "https://feeds.arstechnica.com/arstechnica/index", "outlet"),
    ("MIT Technology Review", "https://www.technologyreview.com/feed/", "outlet"),
    ("Wired", "https://www.wired.com/feed/tag/ai/latest/rss", "outlet"),
    ("VentureBeat", "https://venturebeat.com/category/ai/feed/", "outlet"),
    ("Engadget", "https://www.engadget.com/rss.xml", "outlet"),
    ("The Register", "https://www.theregister.com/headlines.atom", "outlet"),
    ("Google News AI", "https://news.google.com/rss/search?q=artificial+intelligence+when:1d&hl=en-US&gl=US&ceid=US:en", "aggregator"),
    ("ITmedia AI+", "https://rss.itmedia.co.jp/rss/2.0/aiplus.xml", "outlet"),
    ("Publickey", "https://www.publickey1.jp/atom.xml", "outlet"),
]

# 反応の大きさを測る場所
HN_MIN_POINTS = 60
REDDIT_SUBS = ["artificial", "technology", "singularity", "OpenAI"]

# 何時間前までのニュースを対象にするか
MAX_AGE_HOURS = 30

# 同じ話題を何日間は再投稿しないか
HISTORY_DAYS = 14
# 公開用画像を何日で削除するか（TikTokは投稿時に取り込むので短くてOK）
KEEP_IMAGES_DAYS = 7

# ---- AI（Claude API） -----------------------------------------------
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL") or "claude-sonnet-5-5"

# ---- 画像の公開先（GitHub Pages） --------------------------------------
# 例: https://yourname.github.io/tiktok-ai-news
SITE_BASE_URL = (os.getenv("SITE_BASE_URL") or "").rstrip("/")

# ---- TikTok --------------------------------------------------------
TIKTOK_CLIENT_KEY = os.getenv("TIKTOK_CLIENT_KEY", "")
TIKTOK_CLIENT_SECRET = os.getenv("TIKTOK_CLIENT_SECRET", "")
TIKTOK_REFRESH_TOKEN = os.getenv("TIKTOK_REFRESH_TOKEN", "")
# MEDIA_UPLOAD = 下書き（受信箱）に送る / DIRECT_POST = そのまま公開（TikTokの監査通過後）
POST_MODE = os.getenv("POST_MODE") or "MEDIA_UPLOAD"
# DIRECT_POST のときの公開範囲
PRIVACY_LEVEL = os.getenv("PRIVACY_LEVEL") or "PUBLIC_TO_EVERYONE"
# 「AI生成」ラベルを付けるか
IS_AIGC = (os.getenv("IS_AIGC") or "true").lower() == "true"

# ---- スライドの見た目 -------------------------------------------------
ACCOUNT_HANDLE = os.getenv("ACCOUNT_HANDLE") or "@your_account"
BRAND_NAME = os.getenv("BRAND_NAME") or "AI NEWS"

USER_AGENT = "Mozilla/5.0 (compatible; ai-news-slides/1.0; +https://github.com)"
