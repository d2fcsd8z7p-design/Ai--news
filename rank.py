"""同じ話題の記事をまとめ、注目度スコアで並べる。"""
from __future__ import annotations

import math
import re
import urllib.parse
from datetime import datetime, timedelta, timezone

import config

STOP = set("""
a an the and or but of to in on for with at by from as is are was were be been being it its this that
these those new now how why what who will can could would should may might has have had after over into
about up out than more most just says said say report reports via you your we our they their his her
not no yes amp inc ltd co one two first top day week year today here there all also new
""".split())

AI_WORDS = set("""
ai a.i. artificial intelligence llm llms gpt chatgpt openai anthropic claude gemini deepmind google
meta llama mistral xai grok copilot microsoft nvidia gpu gpus chip chips model models agent agents
robot robotics humanoid apple siri samsung tsmc semiconductor datacenter data-center quantum
生成 人工知能 チャット モデル 半導体
""".split())

TRACKING = re.compile(r"^(utm_|fbclid|gclid|ref$|cmpid|mc_)")


def norm_url(u: str) -> str:
    try:
        p = urllib.parse.urlsplit(u)
    except ValueError:
        return u
    q = [(k, v) for k, v in urllib.parse.parse_qsl(p.query) if not TRACKING.match(k)]
    host = p.netloc.lower().removeprefix("www.")
    return f"{host}{p.path.rstrip('/')}" + (f"?{urllib.parse.urlencode(q)}" if q else "")


def tokens(title: str) -> set[str]:
    t = title.lower()
    words = {w for w in re.findall(r"[a-z0-9][a-z0-9.\-+]*[a-z0-9]|[a-z0-9]", t)
             if w not in STOP and (len(w) >= 3 or w.isdigit() or w == "ai")}
    # 日本語は2文字ずつ区切って比較
    for run in re.findall(r"[぀-ヿ一-鿿]+", t):
        words |= {run[i:i + 2] for i in range(len(run) - 1)}
    # 語尾の s をそろえる（models → model）
    return {w[:-1] if len(w) > 4 and w.endswith("s") else w for w in words}


def similar(a: set[str], b: set[str]) -> bool:
    if not a or not b:
        return False
    inter = len(a & b)
    return inter >= 2 and inter / min(len(a), len(b)) >= 0.5


def age_hours(item: dict, now: datetime) -> float | None:
    if not item.get("published"):
        return None
    try:
        d = datetime.fromisoformat(item["published"])
    except ValueError:
        return None
    return (now - d).total_seconds() / 3600


def cluster(items: list[dict]) -> list[list[dict]]:
    clusters: list[dict] = []  # {"items": [...], "tok": [set,...], "urls": set}
    # 反応の大きいものから順に代表にする
    items = sorted(items, key=lambda x: -(x.get("hn_points", 0) + x.get("reddit_ups", 0) / 5))
    for it in items:
        tk = tokens(it["title"])
        nu = norm_url(it["url"])
        target = None
        for c in clusters:
            if nu in c["urls"] or any(similar(tk, t) for t in c["tok"]):
                target = c
                break
        if target is None:
            target = {"items": [], "tok": [], "urls": set()}
            clusters.append(target)
        target["items"].append(it)
        target["tok"].append(tk)
        target["urls"].add(nu)
    return [c["items"] for c in clusters]


def score(c: list[dict], now: datetime) -> dict:
    outlets = {i["source"] for i in c if i["kind"] != "community"}
    hn_pts = max([i.get("hn_points", 0) for i in c] + [0])
    hn_cmt = max([i.get("hn_comments", 0) for i in c] + [0])
    rd_ups = sum(i.get("reddit_ups", 0) for i in c)
    techmeme = any(i["via"] == "Techmeme" for i in c)
    ages = [a for a in (age_hours(i, now) for i in c) if a is not None]
    newest = min(ages) if ages else 12.0

    s = (2.5 * len(outlets)
         + 1.2 * math.log1p(hn_pts)
         + 0.6 * math.log1p(hn_cmt)
         + 0.8 * math.log1p(rd_ups)
         + (2.0 if techmeme else 0.0))
    s *= max(0.3, 1 - newest / 48)  # 新しいほど高く
    words = set().union(*(tokens(i["title"]) for i in c))
    is_ai = bool(words & AI_WORDS)
    if is_ai:
        s *= 1.3
    if not outlets:  # 報道されていない（掲示板だけの話題）は控えめに
        s *= 0.6
    return {"score": round(s, 2), "outlets": sorted(outlets), "hn_points": hn_pts,
            "hn_comments": hn_cmt, "reddit_ups": rd_ups, "techmeme": techmeme,
            "age_h": round(newest, 1), "is_ai": is_ai}


def seen_before(c: list[dict], history: list[dict]) -> bool:
    urls = {norm_url(i["url"]) for i in c}
    toks = [tokens(i["title"]) for i in c]
    for h in history:
        if urls & set(h.get("urls", [])):
            return True
        ht = tokens(h.get("title_en", ""))
        if any(similar(ht, t) for t in toks):
            return True
    return False


def rank(items: list[dict], history: list[dict], top_n: int = 25) -> list[dict]:
    now = datetime.now(timezone.utc)
    fresh = [i for i in items
             if (a := age_hours(i, now)) is None or a <= config.MAX_AGE_HOURS]
    out = []
    for c in cluster(fresh):
        if seen_before(c, history):
            continue
        m = score(c, now)
        # 代表記事：コミュニティ投稿より報道機関の記事を優先
        rep = next((i for i in c if i["kind"] == "outlet"), None) or \
            next((i for i in c if i["kind"] != "community"), c[0])
        out.append({
            "title": rep["title"],
            "titles": list(dict.fromkeys(i["title"] for i in c))[:6],
            "urls": list({norm_url(i["url"]): i["url"] for i in c
                          if "news.google.com" not in i["url"]}.values())[:8],
            "summary": next((i["summary"] for i in c if i["summary"]), ""),
            "sources": sorted({i["source"] for i in c}),
            **m,
        })
    out.sort(key=lambda x: -x["score"])
    for n, c in enumerate(out[:top_n]):
        c["id"] = n
    return out[:top_n]


def prune_history(history: list[dict]) -> list[dict]:
    limit = datetime.now(timezone.utc) - timedelta(days=config.HISTORY_DAYS)
    return [h for h in history if datetime.fromisoformat(h["posted_at"]) > limit]
