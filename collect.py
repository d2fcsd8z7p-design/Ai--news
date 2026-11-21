"""世界中のテックニュースと、その反応（HNのポイント・Redditの高評価）を集める。"""
from __future__ import annotations

import html
import json
import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import config


def http_get(url: str, timeout: int = 20) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": config.USER_AGENT,
                                               "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def strip_html(s: str) -> str:
    s = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", s or "", flags=re.S | re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", html.unescape(s)).strip()


def parse_date(s: str | None) -> datetime | None:
    if not s:
        return None
    s = s.strip()
    try:
        d = parsedate_to_datetime(s)
    except (TypeError, ValueError):
        try:
            d = datetime.fromisoformat(s.replace("Z", "+00:00"))
        except ValueError:
            return None
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    return d.astimezone(timezone.utc)


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()


def _child(el, name):
    for c in el:
        if _local(c.tag) == name:
            return c
    return None


def _text(el, *names) -> str:
    for n in names:
        c = _child(el, n)
        if c is not None and (c.text or "").strip():
            return c.text.strip()
    return ""


def parse_feed(data: bytes, source: str, kind: str) -> list[dict]:
    root = ET.fromstring(data)
    items = []
    for el in root.iter():
        tag = _local(el.tag)
        if tag not in ("item", "entry"):
            continue
        title = strip_html(_text(el, "title"))
        link = _text(el, "link")
        if not link:  # Atom
            for c in el:
                if _local(c.tag) == "link" and c.get("rel", "alternate") == "alternate":
                    link = c.get("href", "")
                    break
        summary = strip_html(_text(el, "description", "summary", "content", "encoded"))
        published = parse_date(_text(el, "pubdate", "published", "updated", "date"))
        outlet = source
        # Google News は「タイトル - 媒体名」形式。媒体名を取り出す
        src_el = _child(el, "source")
        if kind == "aggregator" and src_el is not None and (src_el.text or "").strip():
            outlet = src_el.text.strip()
            title = re.sub(r"\s+-\s+[^-]+$", "", title)
        if not title or not link:
            continue
        items.append({
            "title": title,
            "url": link,
            "summary": summary[:600],
            "published": published.isoformat() if published else None,
            "source": outlet,
            "via": source,
            "kind": kind,
        })
    return items


def fetch_feeds() -> list[dict]:
    out = []
    for name, url, kind in config.FEEDS:
        try:
            out += parse_feed(http_get(url), name, kind)
        except Exception as e:  # 1つ失敗しても続ける
            print(f"[warn] feed {name}: {e}")
    return out


def fetch_hn() -> list[dict]:
    since = int(time.time()) - config.MAX_AGE_HOURS * 3600
    q = urllib.parse.urlencode({
        "tags": "story",
        "numericFilters": f"created_at_i>{since},points>{config.HN_MIN_POINTS}",
        "hitsPerPage": 100,
    })
    try:
        data = json.loads(http_get(f"https://hn.algolia.com/api/v1/search?{q}"))
    except Exception as e:
        print(f"[warn] hacker news: {e}")
        return []
    out = []
    for h in data.get("hits", []):
        if not h.get("title"):
            continue
        out.append({
            "title": h["title"],
            "url": h.get("url") or f"https://news.ycombinator.com/item?id={h['objectID']}",
            "summary": "",
            "published": datetime.fromtimestamp(h["created_at_i"], timezone.utc).isoformat(),
            "source": "Hacker News",
            "via": "Hacker News",
            "kind": "community",
            "hn_points": h.get("points") or 0,
            "hn_comments": h.get("num_comments") or 0,
        })
    return out


def fetch_reddit() -> list[dict]:
    out = []
    for sub in config.REDDIT_SUBS:
        try:
            data = json.loads(http_get(f"https://www.reddit.com/r/{sub}/top.json?t=day&limit=25"))
        except Exception as e:  # クラウドからは拒否されることがある
            print(f"[warn] reddit r/{sub}: {e}")
            continue
        for c in data.get("data", {}).get("children", []):
            d = c.get("data", {})
            if d.get("stickied") or not d.get("title"):
                continue
            out.append({
                "title": d["title"],
                "url": d.get("url_overridden_by_dest") or d.get("url") or "",
                "summary": (d.get("selftext") or "")[:400],
                "published": datetime.fromtimestamp(d.get("created_utc", 0), timezone.utc).isoformat(),
                "source": f"Reddit r/{sub}",
                "via": "Reddit",
                "kind": "community",
                "reddit_ups": d.get("ups") or 0,
                "reddit_comments": d.get("num_comments") or 0,
            })
    return out


def collect_all() -> list[dict]:
    items = fetch_feeds() + fetch_hn() + fetch_reddit()
    print(f"[info] collected {len(items)} items")
    return items
