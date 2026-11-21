"""1080x1920 の縦長スライド画像（JPEG）を作る。"""
from __future__ import annotations

import glob
import hashlib
import random
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

import config

W, H = 1080, 1920
MARGIN = 84
TEXT_W = W - MARGIN * 2

BG_TOP = (9, 12, 28)
BG_BOTTOM = (22, 26, 58)
WHITE = (245, 247, 255)
MUTED = (160, 168, 200)
ACCENTS = [(34, 211, 238), (167, 139, 250), (163, 230, 53), (251, 191, 36), (244, 114, 182)]

NO_LINE_START = set("、。，．・：；？！）」』】〕〉》ー～…‥ゝゞぁぃぅぇぉっゃゅょゎァィゥェォッャュョヮヵヶ,.!?:;)]}%")
NO_LINE_END = set("（「『【〔〈《([{")


# ---------- フォント ----------
_font_cache: dict = {}


def _find_font_file(weight: str) -> list[str]:
    pats = {"bold": ["*NotoSansCJK*-Bold.ttc", "*NotoSansCJK*-Black.ttc", "*NotoSansJP*Bold*"],
            "regular": ["*NotoSansCJK*-Regular.ttc", "*NotoSansCJK*-Medium.ttc", "*NotoSansJP*Regular*"]}
    files = []
    for p in pats[weight]:
        files += glob.glob(f"/usr/share/fonts/**/{p}", recursive=True)
        files += glob.glob(str(Path(__file__).parent / "fonts" / p))
    return files


def font(size: int, weight: str = "regular") -> ImageFont.FreeTypeFont:
    key = (size, weight)
    if key in _font_cache:
        return _font_cache[key]
    for f in _find_font_file(weight) + _find_font_file("regular"):
        if f.endswith(".ttc"):  # ttc の中から日本語(JP)を選ぶ
            for idx in range(10):
                try:
                    ft = ImageFont.truetype(f, size, index=idx)
                except OSError:
                    break
                if "JP" in " ".join(ft.getname()):
                    _font_cache[key] = ft
                    return ft
        else:
            _font_cache[key] = ImageFont.truetype(f, size)
            return _font_cache[key]
    raise RuntimeError("日本語フォントが見つかりません（fonts-noto-cjk を入れてください）")


# ---------- 文字の折り返し（日本語対応） ----------
def _units(text: str) -> list[str]:
    """英単語・数字はひとかたまり、日本語は1文字ずつ"""
    out, buf = [], ""
    for ch in text:
        if ch.isascii() and not ch.isspace():
            buf += ch
            continue
        if buf:
            out.append(buf)
            buf = ""
        out.append(ch)
    if buf:
        out.append(buf)
    return out


def wrap(text: str, ft, max_w: int) -> list[str]:
    lines: list[str] = []
    for para in text.split("\n"):
        line = ""
        for u in _units(para):
            if ft.getlength(line + u) <= max_w or not line.strip():
                line += u
                continue
            # 行頭禁則：句読点などは前の行にぶら下げる
            if u[0] in NO_LINE_START:
                lines.append(line + u)
                line = ""
                continue
            # 行末禁則：開きカッコは次の行へ
            if line and line[-1] in NO_LINE_END:
                lines.append(line[:-1])
                line = line[-1] + u.lstrip()
                continue
            lines.append(line.rstrip())
            line = u.lstrip()
        if line.strip():
            lines.append(line.rstrip())
    return lines


def fit_text(text, max_w, max_lines, sizes, weight):
    """収まる最大のフォントサイズを探す"""
    for s in sizes:
        ft = font(s, weight)
        lines = wrap(text, ft, max_w)
        if len(lines) <= max_lines:
            return ft, lines
    ft = font(sizes[-1], weight)
    lines = wrap(text, ft, max_w)[:max_lines]
    lines[-1] = lines[-1][:-1] + "…"
    return ft, lines


def draw_lines(d, xy, lines, ft, fill, spacing=1.45) -> int:
    x, y = xy
    lh = int(ft.size * spacing)
    for ln in lines:
        d.text((x, y), ln, font=ft, fill=fill)
        y += lh
    return y


# ---------- 背景・共通パーツ ----------
def background(accent, seed: int) -> Image.Image:
    img = Image.new("RGB", (W, H))
    px = ImageDraw.Draw(img)
    for y in range(H):
        t = y / H
        px.line([(0, y), (W, y)], fill=tuple(int(BG_TOP[i] + (BG_BOTTOM[i] - BG_TOP[i]) * t) for i in range(3)))
    rnd = random.Random(seed)
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    g = ImageDraw.Draw(glow)
    for _ in range(3):
        r = rnd.randint(260, 460)
        cx, cy = rnd.randint(-100, W + 100), rnd.randint(-100, H + 100)
        g.ellipse([cx - r, cy - r, cx + r, cy + r], fill=accent + (rnd.randint(40, 70),))
    glow = glow.filter(ImageFilter.GaussianBlur(140))
    img = Image.alpha_composite(img.convert("RGBA"), glow)
    # うっすらとしたグリッド
    grid = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(grid)
    for x in range(0, W, 90):
        gd.line([(x, 0), (x, H)], fill=(255, 255, 255, 10))
    for y in range(0, H, 90):
        gd.line([(0, y), (W, y)], fill=(255, 255, 255, 10))
    return Image.alpha_composite(img, grid)


def pill(d, xy, text, ft, bg, fg, pad=(26, 12)):
    x, y = xy
    tw = ft.getlength(text)
    box = [x, y, x + tw + pad[0] * 2, y + ft.size + pad[1] * 2 + 6]
    d.rounded_rectangle(box, radius=(box[3] - box[1]) // 2, fill=bg)
    d.text((x + pad[0], y + pad[1]), text, font=ft, fill=fg)
    return box


def header(d, accent, edition: str):
    pill(d, (MARGIN, 120), config.BRAND_NAME, font(34, "bold"), accent, BG_TOP)
    ft = font(32)
    d.text((W - MARGIN - ft.getlength(edition), 132), edition, font=ft, fill=MUTED)


def footer(d, accent, page: int, total: int):
    y = H - 210
    ft = font(32)
    d.text((MARGIN, y), config.ACCOUNT_HANDLE, font=ft, fill=MUTED)
    label = f"{page}/{total}"
    d.text((W - MARGIN - ft.getlength(label), y), label, font=ft, fill=MUTED)
    # 進捗バー
    bar_y = y + 64
    seg = (TEXT_W - (total - 1) * 10) / total
    for i in range(total):
        x0 = MARGIN + i * (seg + 10)
        d.rounded_rectangle([x0, bar_y, x0 + seg, bar_y + 8], radius=4,
                            fill=accent if i < page else (60, 66, 100))


# ---------- 各スライド ----------
def cover(data, accent, seed, edition, total):
    img = background(accent, seed)
    d = ImageDraw.Draw(img)
    header(d, accent, edition)
    c = data["cover"]
    y = 560
    box = pill(d, (MARGIN, y), c["kicker"], font(44, "bold"), WHITE, BG_TOP, pad=(30, 14))
    y = box[3] + 60
    ft, lines = fit_text(c["title"], TEXT_W, 5, [104, 96, 88, 80, 72], "bold")
    y = draw_lines(d, (MARGIN, y), lines, ft, WHITE, 1.32)
    d.rectangle([MARGIN, y + 30, MARGIN + 140, y + 40], fill=accent)
    if c.get("subtitle"):
        ft2, l2 = fit_text(c["subtitle"], TEXT_W, 3, [50, 46, 42], "regular")
        draw_lines(d, (MARGIN, y + 90), l2, ft2, (210, 216, 240), 1.5)
    ft3 = font(40, "bold")
    hint = "スワイプして読む  →"
    d.text((W - MARGIN - ft3.getlength(hint), H - 330), hint, font=ft3, fill=accent)
    footer(d, accent, 1, total)
    return img


def content(slide, num, accent, seed, edition, page, total):
    img = background(accent, seed + page)
    d = ImageDraw.Draw(img)
    header(d, accent, edition)
    y = 380
    d.text((MARGIN, y), f"{num:02d}", font=font(150, "bold"), fill=accent)
    y += 230
    ft, lines = fit_text(slide["heading"], TEXT_W, 2, [76, 70, 64], "bold")
    y = draw_lines(d, (MARGIN, y), lines, ft, WHITE, 1.3)
    d.rectangle([MARGIN, y + 24, W - MARGIN, y + 27], fill=(80, 88, 130))
    y += 80
    ft2, l2 = fit_text(slide["body"], TEXT_W, 9, [54, 50, 46, 42], "regular")
    draw_lines(d, (MARGIN, y), l2, ft2, (225, 230, 248), 1.62)
    footer(d, accent, page, total)
    return img


def why(data, accent, seed, edition, page, total):
    img = background(accent, seed + page)
    d = ImageDraw.Draw(img)
    header(d, accent, edition)
    w = data["why"]
    ft, lines = fit_text(w["body"], TEXT_W - 60, 9, [54, 50, 46, 42], "regular")
    body_h = int(ft.size * 1.62) * len(lines)
    # カード（本文の量に合わせて高さを決め、縦方向の中央に置く）
    card_h = 70 + 150 + body_h + 60
    top = max(380, (H - card_h) // 2 - 80)
    card = [MARGIN - 20, top, W - MARGIN + 20, top + card_h]
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(overlay).rounded_rectangle(card, radius=40, fill=(255, 255, 255, 18),
                                              outline=accent + (200,), width=4)
    img = Image.alpha_composite(img, overlay)
    d = ImageDraw.Draw(img)
    y = card[1] + 70
    d.text((MARGIN + 30, y), w["heading"], font=font(76, "bold"), fill=accent)
    y += 150
    draw_lines(d, (MARGIN + 30, y), lines, ft, WHITE, 1.62)
    footer(d, accent, page, total)
    return img


def outro(data, accent, seed, edition, page, total):
    img = background(accent, seed + page)
    d = ImageDraw.Draw(img)
    header(d, accent, edition)
    y = 600
    ft, lines = fit_text("フォローで毎日\n朝7時・夕6時に\nAIニュースが届く", TEXT_W, 4, [88, 80], "bold")
    y = draw_lines(d, (MARGIN, y), lines, ft, WHITE, 1.35)
    y += 80
    d.text((MARGIN, y), "出典", font=font(40, "bold"), fill=accent)
    y += 70
    src = " / ".join(data.get("sources") or ["各社報道"])
    ft2, l2 = fit_text(src, TEXT_W, 3, [44, 40, 36], "regular")
    y = draw_lines(d, (MARGIN, y), l2, ft2, (215, 220, 240), 1.5)
    y += 50
    ft3, l3 = fit_text("※この投稿は報道をもとにAIで要約しています。詳しくは出典元の記事をご確認ください。",
                       TEXT_W, 3, [34], "regular")
    draw_lines(d, (MARGIN, y), l3, ft3, MUTED, 1.5)
    footer(d, accent, page, total)
    return img


def edition_label(now: datetime) -> str:
    return now.strftime("%Y.%m.%d ") + ("朝" if now.hour < 12 else "夕")


def render(data: dict, out_dir: Path, now: datetime) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    seed = int(hashlib.md5(data["cover"]["title"].encode()).hexdigest()[:8], 16)
    accent = ACCENTS[seed % len(ACCENTS)]
    ed = edition_label(now)
    total = 1 + len(data["slides"]) + 2
    imgs = [cover(data, accent, seed, ed, total)]
    for i, s in enumerate(data["slides"], 1):
        imgs.append(content(s, i, accent, seed, ed, i + 1, total))
    imgs.append(why(data, accent, seed, ed, total - 1, total))
    imgs.append(outro(data, accent, seed, ed, total, total))
    paths = []
    for n, im in enumerate(imgs, 1):
        p = out_dir / f"{n:02d}.jpg"
        im.convert("RGB").save(p, "JPEG", quality=90, optimize=True)
        paths.append(p)
    return paths
