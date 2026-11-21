"""Claude API で「どれを投稿するか」を選び、日本語のスライド原稿を書く。"""
from __future__ import annotations

import json
import re
import time

import requests

import config

API_URL = "https://api.anthropic.com/v1/messages"


def ask(system: str, user: str, max_tokens: int = 3000) -> str:
    if not config.ANTHROPIC_API_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY が設定されていません")
    body = {"model": config.ANTHROPIC_MODEL, "max_tokens": max_tokens,
            "system": system, "messages": [{"role": "user", "content": user}]}
    headers = {"x-api-key": config.ANTHROPIC_API_KEY,
               "anthropic-version": "2023-06-01", "content-type": "application/json"}
    for attempt in range(4):
        r = requests.post(API_URL, json=body, headers=headers, timeout=180)
        if r.status_code in (429, 500, 502, 503, 529) and attempt < 3:
            time.sleep(10 * (attempt + 1))
            continue
        r.raise_for_status()
        return "".join(b.get("text", "") for b in r.json()["content"] if b["type"] == "text")
    raise RuntimeError("Claude API に接続できませんでした")


def parse_json(text: str) -> dict:
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise ValueError(f"JSON が返ってきませんでした: {text[:300]}")
    return json.loads(m.group(0))


SELECT_SYSTEM = """あなたは日本のTikTok向けAI・ITニュースアカウントの編集長です。
候補の中から、いま日本の視聴者に届けるべきニュースを1本だけ選びます。
基準（重要な順）:
1. AI・IT分野であること（AIを最優先。半導体・ビッグテック・セキュリティなども可）
2. 注目度（報道した媒体数、Hacker News/Redditの反応、score）
3. 一般の人にも影響や驚きがあること
4. 最近投稿した話題と重ならないこと
避けるもの: 噂だけの話、単なる製品セール情報、政治的に一方に偏った論評、事故・事件の扇情的な扱い。
JSONだけで答えてください。"""


def select(cands: list[dict], recent_titles: list[str]) -> dict:
    lines = []
    for c in cands:
        lines.append(json.dumps({
            "id": c["id"], "title": c["title"], "other_titles": c["titles"][1:4],
            "sources": c["sources"][:8], "score": c["score"], "hn_points": c["hn_points"],
            "reddit_ups": c["reddit_ups"], "age_h": c["age_h"], "summary": c["summary"][:300],
        }, ensure_ascii=False))
    user = ("## 候補\n" + "\n".join(lines) +
            "\n\n## 最近投稿した話題\n" + ("\n".join(f"- {t}" for t in recent_titles) or "なし") +
            '\n\n次の形式で答えてください: {"id": 数字, "reason": "選んだ理由（日本語・1文）"}')
    res = parse_json(ask(SELECT_SYSTEM, user, 400))
    res["id"] = int(res["id"])
    return res


WRITE_SYSTEM = """あなたは日本のTikTokで人気のAI・ITニュース解説者です。
渡された記事本文だけを根拠に、スマホで読む縦長スライドの原稿を書きます。

厳守:
- 記事に書かれていない事実・数字・発言を作らない。推測は「〜とみられる」「〜の可能性」と明記
- 数字、社名、製品名は正確に。英語の固有名詞は一般的な表記（例: OpenAI, NVIDIA）
- 専門用語には短い言い換えを添える
- 煽りすぎない。でも1枚目は思わず次を見たくなる書き方に
- 文字数制限を必ず守る（スマホで読める量）

JSONだけで答えてください。"""

WRITE_FORMAT = """次の形式で答えてください:
{
  "title_en": "元ニュースの英語見出し（重複チェック用）",
  "cover": {"kicker": "2〜6文字のラベル（例: 速報 / 新モデル / 規制 / 半導体）",
            "title": "1枚目の大見出し（28文字以内）",
            "subtitle": "補足の一言（36文字以内）"},
  "slides": [
    {"heading": "見出し（14文字以内）", "body": "本文（100文字以内）"}
  ],
  "why": {"heading": "なぜ重要？", "body": "私たちへの影響や今後（110文字以内）"},
  "post_title": "TikTokのタイトル（30文字以内）",
  "caption": "投稿の説明文（150文字以内。最後に問いかけを1つ）",
  "hashtags": ["#AI", "#テックニュース", "…合計5〜7個"],
  "sources": ["出典の媒体名", "…"]
}
slides は 3〜4枚。"""


def write(cand: dict, articles: list[dict]) -> dict:
    parts = [f"## 見出し\n{cand['title']}\n\n## 他の媒体の見出し\n" +
             "\n".join(f"- {t}" for t in cand["titles"][1:6]),
             f"## RSSの要約\n{cand['summary']}"]
    for a in articles:
        parts.append(f"## 記事本文（{a['source']}）\n{a['text']}")
    user = "\n\n".join(parts) + "\n\n" + WRITE_FORMAT
    data = parse_json(ask(WRITE_SYSTEM, user, 3000))
    return validate(data)


def _cut(s: str, n: int) -> str:
    s = (s or "").strip()
    return s if len(s) <= n else s[: n - 1] + "…"


def validate(d: dict) -> dict:
    d["cover"]["kicker"] = _cut(d["cover"].get("kicker", "NEWS"), 8)
    d["cover"]["title"] = _cut(d["cover"]["title"], 34)
    d["cover"]["subtitle"] = _cut(d["cover"].get("subtitle", ""), 44)
    d["slides"] = [{"heading": _cut(s["heading"], 18), "body": _cut(s["body"], 120)}
                   for s in d["slides"][:4]]
    d["why"] = {"heading": _cut(d["why"].get("heading", "なぜ重要？"), 18),
                "body": _cut(d["why"]["body"], 130)}
    d["post_title"] = _cut(d.get("post_title") or d["cover"]["title"], 40)
    tags = [t if t.startswith("#") else f"#{t}" for t in d.get("hashtags", [])][:7]
    d["hashtags"] = tags or ["#AI", "#テックニュース"]
    d["caption"] = _cut(d.get("caption", ""), 300)
    d["sources"] = [s for s in d.get("sources", []) if s][:4]
    return d
