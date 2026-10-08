"""
4. Meme Generator
Places text with Impact-style font, outline, auto-sizing, exports HD PNG.
Mix: 50% classic on-image + 50% white margin bars.
"""
import os
import json
import textwrap
import random as _random
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter
from config import TEMPLATES_DIR, GENERATED_DIR, FONT_PATHS


def _load_font(size: int):
    for fp in FONT_PATHS:
        if os.path.exists(fp):
            try:
                return ImageFont.truetype(fp, size)
            except Exception:
                continue
    return ImageFont.load_default()


def _draw_text_with_outline(draw, xy, text, font, fill=(255, 255, 255), outline=(0, 0, 0), outline_width=3):
    x, y = xy
    for dx in range(-outline_width, outline_width + 1):
        for dy in range(-outline_width, outline_width + 1):
            if dx != 0 or dy != 0:
                draw.text((x + dx, y + dy), text, font=font, fill=outline)
    draw.text((x, y), text, font=font, fill=fill)


def _region_brightness(img, x, y, w, h):
    try:
        x0 = max(0, int(x))
        y0 = max(0, int(y))
        x1 = min(img.width, int(x + w))
        y1 = min(img.height, int(y + h))
        if x1 <= x0 or y1 <= y0:
            return 128
        crop = img.crop((x0, y0, x1, y1)).convert("L")
        crop = crop.resize((24, 24))
        pixels = list(crop.getdata())
        return sum(pixels) / max(len(pixels), 1)
    except Exception:
        return 128


def _fit_text(text: str, max_width: int, max_height: int, max_font=48, min_font=14):
    text = text.strip() or " "
    max_width = max(40, int(max_width * 0.92))
    practical_max = min(max_font, max(min_font + 2, int(max_height * 0.40)))
    practical_max = min(practical_max, int(max_width * 0.12) + 14)
    for size in range(practical_max, min_font - 1, -1):
        font = _load_font(size)
        tmp = Image.new("RGB", (10, 10))
        d = ImageDraw.Draw(tmp)
        sample = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz "
        avg_char = d.textlength(sample, font=font) / len(sample)
        chars_per_line = max(10, int((max_width - 16) / max(avg_char, 1)))
        lines = textwrap.wrap(text, width=chars_per_line) or [text]
        if len(lines) > 3:
            continue
        line_height = int(size * 1.18)
        total_h = len(lines) * line_height
        if total_h > max_height - 10:
            continue
        max_line_w = max(d.textlength(line, font=font) for line in lines)
        if max_line_w <= max_width - 12:
            return font, lines, line_height, size
    font = _load_font(min_font)
    lines = textwrap.wrap(text, width=22) or [text]
    return font, lines, int(min_font * 1.18), min_font


def _wrap_margin_text(text: str, font, max_width: int, draw) -> list:
    words = (text or "").split()
    if not words:
        return [""]
    lines, cur = [], ""
    for w in words:
        test = (cur + " " + w).strip()
        if draw.textlength(test, font=font) <= max_width:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines[:5]


def _to_reel_safe_frame(img, target_w=1080, target_h=1920, margin=0.06):
    img = img.convert("RGB")
    canvas = Image.new("RGB", (target_w, target_h), (20, 20, 20))
    bg = img.copy()
    bg_ratio = max(target_w / bg.width, target_h / bg.height)
    bg = bg.resize(
        (max(1, int(bg.width * bg_ratio)), max(1, int(bg.height * bg_ratio))),
        Image.LANCZOS,
    )
    left = (bg.width - target_w) // 2
    top = (bg.height - target_h) // 2
    bg = bg.crop((left, top, left + target_w, top + target_h))
    bg = bg.filter(ImageFilter.GaussianBlur(radius=28))
    bg = ImageEnhance.Brightness(bg).enhance(0.85)
    canvas.paste(bg, (0, 0))
    safe_w = int(target_w * (1 - 2 * margin))
    safe_h = int(target_h * (1 - 2 * margin))
    ratio = min(safe_w / img.width, safe_h / img.height)
    fw = max(1, int(img.width * ratio))
    fh = max(1, int(img.height * ratio))
    fg = img.resize((fw, fh), Image.LANCZOS)
    canvas.paste(fg, ((target_w - fw) // 2, (target_h - fh) // 2))
    return canvas


def _generate_classic_on_image(template_path: Path, texts: list, output_name: str) -> Path:
    """Normal meme: text ON the picture (top / bottom)."""
    img = Image.open(template_path).convert("RGB")
    img = ImageEnhance.Contrast(img).enhance(1.15)
    img = ImageEnhance.Color(img).enhance(1.12)
    img = ImageEnhance.Sharpness(img).enhance(1.08)

    w, h = img.size
    margin = max(12, int(min(w, h) * 0.04))
    draw = ImageDraw.Draw(img)

    top_text = (texts[0] if len(texts) > 0 else "").strip()
    bottom_text = (texts[1] if len(texts) > 1 else "").strip()

    boxes = []
    if top_text:
        boxes.append({
            "text": top_text,
            "x": margin,
            "y": margin,
            "w": w - 2 * margin,
            "h": max(70, int(h * 0.22)),
        })
    if bottom_text:
        bot_h = max(70, int(h * 0.22))
        boxes.append({
            "text": bottom_text,
            "x": margin,
            "y": h - bot_h - margin,
            "w": w - 2 * margin,
            "h": bot_h,
        })

    for box in boxes:
        text = box["text"]
        x, y, bw, bh = box["x"], box["y"], box["w"], box["h"]
        font, lines, line_h, size = _fit_text(text, bw - 12, bh - 12, max_font=48, min_font=16)
        brightness = _region_brightness(img, x, y, bw, bh)
        if brightness > 155:
            fill, outline = (0, 0, 0), (255, 255, 255)
        else:
            fill, outline = (255, 255, 255), (0, 0, 0)
        outline_w = 2 if size < 28 else 3
        total_text_h = len(lines) * line_h
        start_y = y + max(0, (bh - total_text_h) // 2)
        for j, line in enumerate(lines):
            line_w = draw.textlength(line, font=font)
            lx = x + (bw - line_w) // 2
            ly = start_y + j * line_h
            _draw_text_with_outline(
                draw, (lx, ly), line, font,
                fill=fill, outline=outline, outline_width=outline_w,
            )

    img = _to_reel_safe_frame(img, margin=0.04)
    out_path = GENERATED_DIR / output_name
    img.save(out_path, "PNG", quality=95)
    return out_path


def _generate_margin_bars(template_path: Path, texts: list, output_name: str) -> Path:
    """White bars above/below — clean photo in the middle."""
    photo = Image.open(template_path).convert("RGB")
    photo = ImageEnhance.Contrast(photo).enhance(1.15)
    photo = ImageEnhance.Color(photo).enhance(1.12)
    photo = ImageEnhance.Sharpness(photo).enhance(1.08)

    top_text = (texts[0] if len(texts) > 0 else "").strip()
    bottom_text = (texts[1] if len(texts) > 1 else "").strip()

    layout = _random.choices(
        ["both", "top_only", "bottom_only"],
        weights=[45, 35, 20],
        k=1,
    )[0]

    if layout == "top_only":
        if top_text and bottom_text:
            top_text = f"{top_text}  {bottom_text}"
        elif bottom_text and not top_text:
            top_text = bottom_text
        bottom_text = ""
    elif layout == "bottom_only":
        if top_text and bottom_text:
            bottom_text = f"{top_text}  {bottom_text}"
        elif top_text and not bottom_text:
            bottom_text = top_text
        top_text = ""

    content_w = 1080
    pad_x = 36
    text_max_w = content_w - pad_x * 2

    def _sans(size):
        for fp in [
            "C:/Windows/Fonts/arialbd.ttf",
            "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/segoeui.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ] + list(FONT_PATHS):
            if os.path.exists(fp):
                try:
                    return ImageFont.truetype(fp, size)
                except Exception:
                    continue
        return ImageFont.load_default()

    probe = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    top_font = _sans(36)
    bot_font = _sans(36)

    top_lines = _wrap_margin_text(top_text, top_font, text_max_w, probe) if top_text else []
    bot_lines = _wrap_margin_text(bottom_text, bot_font, text_max_w, probe) if bottom_text else []

    line_h_top = 46
    line_h_bot = 46
    bar_pad_y = 22
    top_bar_h = (bar_pad_y * 2 + len(top_lines) * line_h_top) if top_lines else 0
    bot_bar_h = (bar_pad_y * 2 + len(bot_lines) * line_h_bot) if bot_lines else 0

    ratio = content_w / photo.width
    ph = max(1, int(photo.height * ratio))
    photo = photo.resize((content_w, ph), Image.LANCZOS)

    total_h = top_bar_h + ph + bot_bar_h
    canvas = Image.new("RGB", (content_w, total_h), (255, 255, 255))
    draw = ImageDraw.Draw(canvas)

    if top_lines:
        y = bar_pad_y
        for line in top_lines:
            lw = draw.textlength(line, font=top_font)
            draw.text(((content_w - lw) / 2, y), line, font=top_font, fill=(0, 0, 0))
            y += line_h_top

    canvas.paste(photo, (0, top_bar_h))

    if bot_lines:
        y = top_bar_h + ph + bar_pad_y
        for line in bot_lines:
            lw = draw.textlength(line, font=bot_font)
            draw.text(((content_w - lw) / 2, y), line, font=bot_font, fill=(0, 0, 0))
            y += line_h_bot

    canvas = _to_reel_safe_frame(canvas, margin=0.04)
    out_path = GENERATED_DIR / output_name
    canvas.save(out_path, "PNG", quality=95)
    return out_path


def generate_meme(
    template_path: Path,
    text_boxes: list,
    texts: list,
    output_name: str,
    style_name: str = "classic",
) -> Path:
    """50% classic on-image + 50% white margin bars."""
    mode = _random.choices(
        ["classic", "margin"],
        weights=[50, 50],
        k=1,
    )[0]
    if mode == "classic":
        return _generate_classic_on_image(template_path, texts, output_name)
    return _generate_margin_bars(template_path, texts, output_name)


def create_meme_from_template(template_obj, caption_dict: dict, meme_id: int) -> Path:
    template_path = TEMPLATES_DIR / template_obj.filename
    try:
        from template_collector import _guess_text_boxes
        with Image.open(template_path) as im:
            w, h = im.size
        old_boxes = json.loads(template_obj.text_boxes or "[]")
        n = max(2, len(old_boxes)) if old_boxes else 2
        boxes = _guess_text_boxes(w, h, n, name=template_obj.name or "")
    except Exception:
        boxes = json.loads(template_obj.text_boxes or "[]")

    texts = []
    if len(boxes) >= 2:
        texts = [caption_dict.get("top_text", ""), caption_dict.get("bottom_text", "")]
        texts.extend(caption_dict.get("extra_texts", []))
    elif len(boxes) == 1:
        texts = [caption_dict.get("top_text", "") or caption_dict.get("bottom_text", "")]
    else:
        texts = [caption_dict.get("top_text", "")]
        texts.extend(caption_dict.get("extra_texts", []))

    while len(texts) < len(boxes):
        texts.append("")
    texts = texts[: max(2, len(boxes))]

    out_name = f"meme_{meme_id:05d}_{template_obj.category}_{caption_dict.get('style', 'gen')}.png"
    return generate_meme(template_path, boxes, texts, out_name)