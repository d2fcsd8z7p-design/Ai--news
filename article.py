"""選ばれたニュースの記事本文を取得する（取れない場合はRSSの要約で代用）。"""
from __future__ import annotations

import re
import urllib.parse
from html.parser import HTMLParser

from collect import http_get

SKIP_HOSTS = ("news.ycombinator.com", "reddit.com", "x.com", "twitter.com", "youtube.com")


class _P(HTMLParser):
    def __init__(self):
        super().__init__()
        self.depth_skip = 0
        self.in_p = False
        self.buf: list[str] = []
        self.paras: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "nav", "footer", "aside", "form"):
            self.depth_skip += 1
        elif tag == "p":
            self.in_p, self.buf = True, []

    def handle_endtag(self, tag):
        if tag in ("script", "style", "nav", "footer", "aside", "form"):
            self.depth_skip = max(0, self.depth_skip - 1)
        elif tag == "p" and self.in_p:
            self.in_p = False
            t = re.sub(r"\s+", " ", "".join(self.buf)).strip()
            if len(t) >= 60:
                self.paras.append(t)

    def handle_data(self, data):
        if self.in_p and not self.depth_skip:
            self.buf.append(data)


def extract_text(html_bytes: bytes, limit: int = 7000) -> str:
    p = _P()
    p.feed(html_bytes.decode("utf-8", errors="ignore"))
    return "\n".join(p.paras)[:limit]


def fetch_articles(urls: list[str], max_articles: int = 3) -> list[dict]:
    out = []
    for u in urls:
        host = urllib.parse.urlsplit(u).netloc.lower()
        if any(h in host for h in SKIP_HOSTS):
            continue
        try:
            text = extract_text(http_get(u, timeout=20))
        except Exception as e:
            print(f"[warn] article {u}: {e}")
            continue
        if len(text) > 400:
            out.append({"url": u, "source": host.removeprefix("www."), "text": text})
        if len(out) >= max_articles:
            break
    return out
