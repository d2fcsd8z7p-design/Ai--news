"""TikTok Content Posting API（画像投稿）"""
from __future__ import annotations

import time

import requests

API = "https://open.tiktokapis.com/v2"


class TikTokError(RuntimeError):
    pass


def _check(r: requests.Response) -> dict:
    try:
        j = r.json()
    except ValueError:
        raise TikTokError(f"HTTP {r.status_code}: {r.text[:300]}")
    err = j.get("error")
    if isinstance(err, dict) and err.get("code") not in (None, "ok"):
        raise TikTokError(f"{err.get('code')}: {err.get('message')}")
    if r.status_code >= 400:
        raise TikTokError(f"HTTP {r.status_code}: {j}")
    return j


def exchange_code(client_key, client_secret, code, redirect_uri) -> dict:
    """初回だけ：認可コード → アクセストークン/リフレッシュトークン"""
    r = requests.post(f"{API}/oauth/token/", timeout=30, data={
        "client_key": client_key, "client_secret": client_secret, "code": code,
        "grant_type": "authorization_code", "redirect_uri": redirect_uri})
    j = r.json()
    if "access_token" not in j:
        raise TikTokError(f"トークン取得に失敗: {j.get('error')} {j.get('error_description')}")
    return j


def refresh(client_key, client_secret, refresh_token) -> dict:
    r = requests.post(f"{API}/oauth/token/", timeout=30, data={
        "client_key": client_key, "client_secret": client_secret,
        "grant_type": "refresh_token", "refresh_token": refresh_token})
    j = r.json()
    if "access_token" not in j:
        raise TikTokError(f"トークン更新に失敗: {j.get('error')} {j.get('error_description')}")
    return j


def _headers(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=UTF-8"}


def creator_info(token) -> dict:
    r = requests.post(f"{API}/post/publish/creator_info/query/", headers=_headers(token), timeout=30)
    return _check(r)["data"]


def post_photos(token, image_urls, title, description, mode="MEDIA_UPLOAD",
                privacy_level="PUBLIC_TO_EVERYONE", is_aigc=True) -> str:
    post_info = {"title": title[:90], "description": description[:4000]}
    if mode == "DIRECT_POST":
        info = creator_info(token)
        options = info.get("privacy_level_options", [])
        if privacy_level not in options:
            raise TikTokError(f"公開範囲 {privacy_level} は使えません（選べるもの: {options}）")
        post_info |= {"privacy_level": privacy_level, "disable_comment": False,
                      "auto_add_music": True}
    body = {
        "media_type": "PHOTO",
        "post_mode": mode,
        "post_info": post_info,
        "source_info": {"source": "PULL_FROM_URL", "photo_images": image_urls,
                        "photo_cover_index": 0},
        "is_aigc": is_aigc,
    }
    r = requests.post(f"{API}/post/publish/content/init/", headers=_headers(token),
                      json=body, timeout=60)
    return _check(r)["data"]["publish_id"]


def wait_status(token, publish_id, timeout_s=300) -> str:
    end = time.time() + timeout_s
    status = "UNKNOWN"
    while time.time() < end:
        r = requests.post(f"{API}/post/publish/status/fetch/", headers=_headers(token),
                          json={"publish_id": publish_id}, timeout=30)
        data = _check(r).get("data", {})
        status = data.get("status", "UNKNOWN")
        print(f"[info] TikTok status: {status}")
        if status in ("SEND_TO_USER_INBOX", "PUBLISH_COMPLETE"):
            return status
        if status == "FAILED":
            raise TikTokError(f"投稿に失敗: {data.get('fail_reason')}")
        time.sleep(10)
    return status
