"""初回だけ：連携ページに表示されたコードを TikTok のリフレッシュトークンに交換し、
GitHub の Secret（TIKTOK_REFRESH_TOKEN）に保存できる形で書き出す。"""
import os
import sys
from pathlib import Path

import config
import tiktok

code = (os.getenv("CODE") or "").strip()
if not code:
    sys.exit("code が空です。連携ページに表示されたコードを入力して実行してください")
if not (config.TIKTOK_CLIENT_KEY and config.TIKTOK_CLIENT_SECRET and config.SITE_BASE_URL):
    sys.exit("TIKTOK_CLIENT_KEY / TIKTOK_CLIENT_SECRET / SITE_BASE_URL を先に設定してください")

tok = tiktok.exchange_code(config.TIKTOK_CLIENT_KEY, config.TIKTOK_CLIENT_SECRET, code,
                           f"{config.SITE_BASE_URL}/callback.html")
rt = tok["refresh_token"]
print(f"::add-mask::{rt}")
Path(os.getenv("RUNNER_TEMP", "/tmp"), "new_refresh_token").write_text(rt)
print(f"連携できました。scope: {tok.get('scope')}")
