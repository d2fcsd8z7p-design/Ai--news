"""AI・ITニュースを選んでスライド化し、TikTokに送る。

  python main.py            本番（TikTokの下書きに送る）
  python main.py --preview  画像を作って公開するだけ（TikTokには送らない）
  python main.py --local    画像をこの場で作るだけ（git操作もしない／テスト用）
  --sample FILE             ニュース収集とAIを使わず、JSONの原稿で画像を作る
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

import article
import collect
import config
import llm
import rank
import slides
import tiktok

ROOT = Path(__file__).parent
HISTORY = ROOT / "history.json"
POSTS = ROOT / "posts"
JST = timezone(timedelta(hours=9))


def load_history() -> list[dict]:
    if HISTORY.exists():
        return json.loads(HISTORY.read_text(encoding="utf-8"))
    return []


def save_history(h: list[dict]):
    HISTORY.write_text(json.dumps(h, ensure_ascii=False, indent=1), encoding="utf-8")


def git(*args):
    subprocess.run(["git", *args], cwd=ROOT, check=True)


def git_push(message: str):
    git("add", "-A", "posts", "history.json") if HISTORY.exists() else git("add", "-A", "posts")
    if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT).returncode == 0:
        return
    git("commit", "-q", "-m", message)
    for _ in range(3):
        try:
            git("pull", "-q", "--rebase")
            git("push", "-q")
            return
        except subprocess.CalledProcessError:
            time.sleep(5)
    raise RuntimeError("git push に失敗しました")


def cleanup_old_posts(now: datetime):
    limit = (now - timedelta(days=config.KEEP_IMAGES_DAYS)).strftime("%Y%m%d")
    if not POSTS.exists():
        return
    for d in POSTS.iterdir():
        if d.is_dir() and d.name[:8] < limit:
            shutil.rmtree(d)


def wait_public(urls: list[str], timeout_s=900):
    """GitHub Pages に画像が出るまで待つ"""
    end = time.time() + timeout_s
    pending = list(urls)
    while pending and time.time() < end:
        pending = [u for u in pending
                   if requests.head(u, timeout=20, allow_redirects=False).status_code != 200]
        if pending:
            time.sleep(15)
    if pending:
        raise RuntimeError(f"画像が公開されませんでした（GitHub Pages の設定を確認）: {pending[0]}")


def summary(md: str):
    """GitHub の実行結果ページに表示する"""
    p = os.getenv("GITHUB_STEP_SUMMARY")
    if p:
        with open(p, "a", encoding="utf-8") as f:
            f.write(md + "\n")
    print(md)


def build_caption(data: dict) -> str:
    src = " / ".join(data["sources"]) if data["sources"] else "各社報道"
    return f"{data['caption']}\n\n出典: {src}\n※AIで要約しています\n\n" + " ".join(data["hashtags"])


def choose_and_write(history: list[dict]) -> tuple[dict, dict]:
    items = collect.collect_all()
    cands = rank.rank(items, history)
    if not cands:
        raise RuntimeError("候補のニュースが見つかりませんでした")
    print("[info] 注目度ランキング上位:")
    for c in cands[:10]:
        print(f"  {c['score']:6.2f}  [{len(c['outlets'])}媒体 HN{c['hn_points']}] {c['title']}")
    sel = llm.select(cands, [h["title_ja"] for h in history[-20:]])
    cand = next((c for c in cands if c["id"] == sel["id"]), cands[0])
    print(f"[info] 選んだニュース: {cand['title']}  理由: {sel.get('reason')}")
    arts = article.fetch_articles(cand["urls"])
    print(f"[info] 本文を取得できた記事: {len(arts)}本")
    data = llm.write(cand, arts)
    if not data["sources"]:
        data["sources"] = [s for s in cand["sources"]
                           if not s.startswith(("Reddit", "Hacker"))][:3]
    return cand, data


def require(*names):
    missing = [n for n in names if not getattr(config, n)]
    if missing:
        sys.exit(f"設定が足りません: {', '.join(missing)}（GitHub の Secrets / Variables を確認）")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--preview", action="store_true")
    ap.add_argument("--local", action="store_true")
    ap.add_argument("--sample")
    args = ap.parse_args()

    now = datetime.now(JST)
    history = rank.prune_history(load_history())

    if args.sample:
        data = llm.validate(json.loads(Path(args.sample).read_text(encoding="utf-8")))
        cand = {"title": data.get("title_en", ""), "urls": []}
    else:
        require("ANTHROPIC_API_KEY")
        cand, data = choose_and_write(history)

    slug = now.strftime("%Y%m%d-%H%M")
    out_dir = POSTS / slug
    paths = slides.render(data, out_dir, now)
    caption = build_caption(data)
    (out_dir / "post.json").write_text(json.dumps(
        {"data": data, "caption": caption, "article_urls": cand["urls"]},
        ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[info] スライド {len(paths)}枚 → {out_dir}")
    if args.local:
        return

    require("SITE_BASE_URL")
    cleanup_old_posts(now)
    git_push(f"slides {slug}")
    urls = [f"{config.SITE_BASE_URL}/posts/{slug}/{p.name}" for p in paths]
    wait_public(urls)

    md = [f"## {data['cover']['title']}", "", "```", caption, "```", ""]
    md += [f'<img src="{u}" width="180">' for u in urls]
    summary("\n".join(md))
    if args.preview:
        return

    require("TIKTOK_CLIENT_KEY", "TIKTOK_CLIENT_SECRET", "TIKTOK_REFRESH_TOKEN")
    tok = tiktok.refresh(config.TIKTOK_CLIENT_KEY, config.TIKTOK_CLIENT_SECRET,
                         config.TIKTOK_REFRESH_TOKEN)
    new_rt = tok.get("refresh_token")
    if new_rt and new_rt != config.TIKTOK_REFRESH_TOKEN:
        print(f"::add-mask::{new_rt}")
        Path(os.getenv("RUNNER_TEMP", "/tmp"), "new_refresh_token").write_text(new_rt)

    publish_id = tiktok.post_photos(
        tok["access_token"], urls, data["post_title"], caption,
        mode=config.POST_MODE, privacy_level=config.PRIVACY_LEVEL, is_aigc=config.IS_AIGC)
    status = tiktok.wait_status(tok["access_token"], publish_id)
    summary(f"\n**TikTok:** {status}（{config.POST_MODE}）")

    history.append({"posted_at": datetime.now(timezone.utc).isoformat(),
                    "title_ja": data["cover"]["title"], "title_en": data.get("title_en", cand["title"]),
                    "urls": [rank.norm_url(u) for u in cand["urls"]], "slug": slug})
    save_history(history)
    git_push(f"history {slug}")


if __name__ == "__main__":
    main()
