"""
2. Meme Template Collector

- Downloads real popular templates from Imgflip (free API)
- Falls back to procedurally generated classic blanks
- Stores everything in the local templates/ folder + DB
"""

import json
import os
import re
import requests
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from config import TEMPLATES_DIR, FONT_PATHS
from database import get_session, Template, init_db
from trend_discovery import get_popular_imgflip_templates


def _get_font(size=40):
    for fp in FONT_PATHS:
        if os.path.exists(fp):
            return ImageFont.truetype(fp, size)
    return ImageFont.load_default()


def create_blank_template(name: str, width: int, height: int, text_boxes: list, bg_color=(25, 25, 30)):
    """Create a clean blank canvas (no ugly guide rectangles) for classic text-on-dark memes."""
    img = Image.new("RGB", (width, height), bg_color)
    # Subtle gradient-ish top bar so it doesn't look pure black / empty
    draw = ImageDraw.Draw(img)
    for y in range(0, min(80, height // 5)):
        shade = 25 + int(y * 0.4)
        draw.line([(0, y), (width, y)], fill=(shade, shade, shade + 5))
    # Tiny label only in corner (will be covered by text usually)
    font = _get_font(14)
    draw.text((8, height - 20), name[:30], fill=(90, 90, 95), font=font)
    filename = f"{name.lower().replace(' ', '_').replace('/', '_')[:60]}.png"
    path = TEMPLATES_DIR / filename
    img.save(path, "PNG")
    return filename, text_boxes


def _guess_text_boxes(width: int, height: int, box_count: int, name: str = "") -> list:
    """
    Smarter text placement based on known meme layouts.
    Avoids empty white halves and bad overlays.
    """
    name_l = (name or "").lower()
    margin = max(10, int(width * 0.025))

    # --- Drake / Hotline Bling style (right side only) ---
    if "drake" in name_l:
        # Text only on the right half
        right_x = width // 2 + margin
        right_w = width // 2 - 2 * margin
        return [
            {"x": right_x, "y": margin, "w": right_w, "h": height // 2 - 2 * margin, "align": "center"},
            {"x": right_x, "y": height // 2 + margin, "w": right_w, "h": height // 2 - 2 * margin, "align": "center"},
        ]

    # --- Two Buttons / left-right panels ---
    if "two buttons" in name_l or "buttons" in name_l:
        half_w = width // 2 - 2 * margin
        return [
            {"x": margin, "y": margin, "w": half_w, "h": int(height * 0.35), "align": "center"},
            {"x": width // 2 + margin, "y": margin, "w": half_w, "h": int(height * 0.35), "align": "center"},
        ]

    # --- Trade Offer (left / right with center figure) ---
    if "trade offer" in name_l:
        return [
            {"x": margin, "y": int(height * 0.55), "w": width // 2 - 2 * margin, "h": int(height * 0.35), "align": "center"},
            {"x": width // 2 + margin, "y": int(height * 0.55), "w": width // 2 - 2 * margin, "h": int(height * 0.35), "align": "center"},
        ]

    # --- Expanding Brain / vertical stack on left ---
    if "brain" in name_l or "expanding" in name_l or "galaxy" in name_l:
        left_w = width // 2 - 2 * margin
        h_each = (height - 2 * margin) // max(box_count, 4) - 6
        boxes = []
        for i in range(max(box_count, 4)):
            boxes.append({
                "x": margin,
                "y": margin + i * (h_each + 6),
                "w": left_w,
                "h": h_each,
                "align": "center",
            })
        return boxes

       # --- Default: classic top / bottom (thin bands = smaller text) ---
    if box_count <= 1:
        return [{
            "x": margin, "y": margin,
            "w": width - 2 * margin,
            "h": max(55, int(height * 0.14)),
            "align": "center"
        }]
    elif box_count == 2:
        top_h = max(55, int(height * 0.13))
        bot_h = max(55, int(height * 0.13))
        return [
            {"x": margin, "y": margin, "w": width - 2 * margin, "h": top_h, "align": "center"},
            {"x": margin, "y": height - bot_h - margin, "w": width - 2 * margin, "h": bot_h, "align": "center"},
        ]
    elif box_count == 3:
        band_h = max(50, int(height * 0.12))
        return [
            {"x": margin, "y": margin, "w": width - 2 * margin, "h": band_h, "align": "center"},
            {"x": margin, "y": (height - band_h) // 2, "w": width - 2 * margin, "h": band_h, "align": "center"},
            {"x": margin, "y": height - band_h - margin, "w": width - 2 * margin, "h": band_h, "align": "center"},
        ]
    else:
        usable = height - 2 * margin
        h_each = max(45, usable // box_count - 6)
        boxes = []
        for i in range(box_count):
            boxes.append({
                "x": margin,
                "y": margin + i * (h_each + 4),
                "w": width - 2 * margin,
                "h": h_each,
                "align": "center",
            })
        return boxes

def download_imgflip_templates(max_count: int = 100) -> int:
    """Download as many real Imgflip templates as possible."""
    print("   ⬇️  Downloading real templates from Imgflip (max pool)…")
    templates = get_popular_imgflip_templates(limit=max_count)
    if not templates:
        print("   ⚠️ Could not reach Imgflip – skipping real download")
        return 0

    session = get_session()
    added = 0
    for t in templates:
        name = t["value"]
        existing = session.query(Template).filter(Template.name == name).first()
        if existing:
            continue

        url = t["template_url"]
        try:
            content = _download_bytes(url, timeout=15, retries=3)
            safe = re.sub(r"[^a-zA-Z0-9_-]", "_", name.lower())[:40]
            filename = f"imgflip_{t['template_id']}_{safe}.png"
            path = TEMPLATES_DIR / filename
            with open(path, "wb") as f:
                f.write(content)

            with Image.open(path) as img:
                w, h = img.size

            boxes = _guess_text_boxes(w, h, t.get("box_count", 2), name=name)

            record = Template(
                name=name,
                filename=filename,
                category="imgflip",
                text_boxes=json.dumps(boxes),
            )
            session.add(record)
            added += 1
            print(f"      + {name}")
        except Exception as e:
            print(f"      ⚠️ Failed {name}: {e}")

    session.commit()
    session.close()
    return added

def download_memegen_templates(max_count: int = 150) -> int:
    """
    Download blank templates from memegen.link (extra source beyond Imgflip).
    API: https://api.memegen.link/templates/
    """
    print("   ⬇️  Downloading templates from memegen.link…")
    try:
        resp = requests.get("https://api.memegen.link/templates/", timeout=20)
        if resp.status_code != 200:
            print(f"   ⚠️ memegen.link failed: {resp.status_code}")
            return 0
        data = resp.json()
    except Exception as e:
        print(f"   ⚠️ memegen.link unreachable: {e}")
        return 0

    session = get_session()
    added = 0
    for t in data[:max_count]:
        name = t.get("name") or t.get("id") or "unknown"
        tid = t.get("id", "x")
        blank_url = t.get("blank")
        if not blank_url:
            continue
        # Skip if name already exists
        existing = session.query(Template).filter(Template.name == name).first()
        if existing:
            continue
        try:
            img_resp = requests.get(blank_url, timeout=15)
            if img_resp.status_code != 200:
                continue
            safe = re.sub(r"[^a-zA-Z0-9_-]", "_", name.lower())[:40]
            filename = f"memegen_{tid}_{safe}.png"
            path = TEMPLATES_DIR / filename
            with open(path, "wb") as f:
                f.write(img_resp.content)

            with Image.open(path) as img:
                w, h = img.size

            lines = int(t.get("lines") or 2)
            boxes = _guess_text_boxes(w, h, lines, name=name)

            record = Template(
                name=name,
                filename=filename,
                category="memegen",
                text_boxes=json.dumps(boxes),
            )
            session.add(record)
            added += 1
            print(f"      + {name} (memegen)")
        except Exception as e:
            print(f"      ⚠️ Failed {name}: {e}")

    session.commit()
    session.close()
    return added


def download_trending_templates() -> int:
    """
    Fetch CURRENT trending templates (changes over weeks/months).
    Run regularly so long-term 30/day automation keeps getting new formats.
    """
    print("   🔥 Downloading CURRENT trending templates…")
    session = get_session()
    added = 0
    try:
        resp = requests.get("https://justmeme.wtf/api/v1/trending", timeout=15)
        if resp.status_code == 200:
            items = resp.json().get("trending") or []
            for t in items:
                name = t.get("name") or t.get("slug") or "trending"
                url = t.get("url")
                if not url:
                    continue
                if session.query(Template).filter(Template.name == name).first():
                    continue
                try:
                    img_resp = requests.get(url, timeout=15)
                    if img_resp.status_code != 200:
                        continue
                    tid = t.get("slug") or t.get("id") or "trend"
                    safe = re.sub(r"[^a-zA-Z0-9_-]", "_", str(name).lower())[:40]
                    filename = f"justmeme_{tid}_{safe}.png"
                    path = TEMPLATES_DIR / filename
                    with open(path, "wb") as f:
                        f.write(img_resp.content)
                    with Image.open(path) as img:
                        w, h = img.size
                    boxes = _guess_text_boxes(w, h, 2, name=name)
                    session.add(Template(
                        name=name,
                        filename=filename,
                        category="justmeme",
                        text_boxes=json.dumps(boxes),
                    ))
                    added += 1
                    print(f"      + TRENDING {name}")
                except Exception as e:
                    print(f"      ⚠️ Trending fail {name}: {e}")
    except Exception as e:
        print(f"   ⚠️ justmeme trending failed: {e}")
    session.commit()
    session.close()
    # Imgflip top-100 also rotates with trends
    try:
        added += download_imgflip_templates(max_count=100)
    except Exception:
        pass
    return added


def download_justmeme_templates(max_count: int = 300) -> int:
    """
    Download templates from justmeme.wtf (2300+ catalog).
    API: https://justmeme.wtf/api/v1/templates
    """
    print("   ⬇️  Downloading templates from justmeme.wtf…")
    session = get_session()
    added = 0
    page = 1
    per_page = 50

    while added < max_count:
        try:
            resp = requests.get(
                f"https://justmeme.wtf/api/v1/templates?limit={per_page}&page={page}",
                timeout=20,
            )
            if resp.status_code != 200:
                break
            payload = resp.json()
            batch = payload.get("templates") or []
            if not batch:
                break
        except Exception as e:
            print(f"   ⚠️ justmeme.wtf page {page} failed: {e}")
            break

        for t in batch:
            if added >= max_count:
                break
            name = t.get("name") or t.get("slug") or t.get("id") or "unknown"
            tid = t.get("slug") or t.get("id") or f"p{page}"
            url = t.get("url")
            if not url:
                continue
            existing = session.query(Template).filter(Template.name == name).first()
            if existing:
                continue
            try:
                img_resp = requests.get(url, timeout=15)
                if img_resp.status_code != 200:
                    continue
                safe = re.sub(r"[^a-zA-Z0-9_-]", "_", str(name).lower())[:40]
                filename = f"justmeme_{tid}_{safe}.png"
                path = TEMPLATES_DIR / filename
                with open(path, "wb") as f:
                    f.write(img_resp.content)

                with Image.open(path) as img:
                    w, h = img.size
                    # skip tiny/broken images
                    if w < 100 or h < 100:
                        continue

                boxes = _guess_text_boxes(w, h, 2, name=name)
                record = Template(
                    name=name,
                    filename=filename,
                    category="justmeme",
                    text_boxes=json.dumps(boxes),
                )
                session.add(record)
                added += 1
                if added % 25 == 0:
                    session.commit()
                    print(f"      … {added} justmeme templates")
            except Exception as e:
                print(f"      ⚠️ Failed {name}: {e}")

        total = payload.get("total") or 0
        if page * per_page >= total:
            break
        page += 1

    session.commit()
    session.close()
    return added


def seed_local_blanks():
    """Create / update classic blank templates (always ensure they exist with good box sizes)."""
    session = get_session()
    # Always re-create the blank image files + ensure DB records (update boxes if needed)
    specs = [
        {
            "name": "Classic Top Bottom",
            "category": "classic",
            "size": (800, 600),
            "boxes": [
                {"x": 30, "y": 15, "w": 740, "h": 160, "align": "center"},
                {"x": 30, "y": 430, "w": 740, "h": 150, "align": "center"},
            ],
            "bg": (28, 28, 32),
        },
        {
            "name": "Drake Hotline",
            "category": "drake",
            "size": (700, 700),
            "boxes": [
                {"x": 340, "y": 30, "w": 340, "h": 300, "align": "center"},
                {"x": 340, "y": 370, "w": 340, "h": 300, "align": "center"},
            ],
            "bg": (22, 22, 40),
        },
        {
            "name": "Expanding Brain",
            "category": "expanding_brain",
            "size": (700, 900),
            "boxes": [
                {"x": 15, "y": 15, "w": 340, "h": 200, "align": "center"},
                {"x": 15, "y": 230, "w": 340, "h": 200, "align": "center"},
                {"x": 15, "y": 450, "w": 340, "h": 200, "align": "center"},
                {"x": 15, "y": 670, "w": 340, "h": 200, "align": "center"},
            ],
            "bg": (12, 12, 30),
        },
        {
            "name": "Two Panels",
            "category": "two_panels",
            "size": (800, 500),
            "boxes": [
                {"x": 15, "y": 15, "w": 370, "h": 470, "align": "center"},
                {"x": 415, "y": 15, "w": 370, "h": 470, "align": "center"},
            ],
            "bg": (32, 32, 36),
        },
        {
            "name": "Change My Mind",
            "category": "change_my_mind",
            "size": (800, 600),
            "boxes": [
                {"x": 160, "y": 250, "w": 480, "h": 140, "align": "center"},
            ],
            "bg": (50, 32, 22),
        },
        {
            "name": "Success Kid",
            "category": "success",
            "size": (600, 600),
            "boxes": [
                {"x": 20, "y": 15, "w": 560, "h": 130, "align": "center"},
                {"x": 20, "y": 460, "w": 560, "h": 120, "align": "center"},
            ],
            "bg": (20, 50, 80),
        },
        {
            "name": "This Is Fine",
            "category": "this_is_fine",
            "size": (700, 500),
            "boxes": [
                {"x": 30, "y": 15, "w": 640, "h": 130, "align": "center"},
                {"x": 30, "y": 360, "w": 640, "h": 120, "align": "center"},
            ],
            "bg": (65, 30, 12),
        },
        {
            "name": "Distracted Boyfriend",
            "category": "distracted",
            "size": (800, 550),
            "boxes": [
                {"x": 15, "y": 15, "w": 250, "h": 100, "align": "center"},
                {"x": 275, "y": 15, "w": 250, "h": 100, "align": "center"},
                {"x": 535, "y": 15, "w": 250, "h": 100, "align": "center"},
            ],
            "bg": (30, 50, 30),
        },
    ]

    for spec in specs:
        filename, boxes = create_blank_template(
            spec["name"], *spec["size"], spec["boxes"], spec["bg"]
        )
        existing = session.query(Template).filter(Template.name == spec["name"]).first()
        if existing:
            existing.filename = filename
            existing.category = spec["category"]
            existing.text_boxes = json.dumps(boxes)
        else:
            t = Template(
                name=spec["name"],
                filename=filename,
                category=spec["category"],
                text_boxes=json.dumps(boxes),
            )
            session.add(t)
    session.commit()
    session.close()
    print(f"✅ Seeded / updated {len(specs)} local blank templates")


def _register_extra_local_templates():
    """Register any PNG already sitting in templates/ that is missing from the DB."""
    session = get_session()
    known_files = {t.filename for t in session.query(Template).all()}
    known_names = {t.name for t in session.query(Template).all()}
    extras = {
        "woman_yelling_cat.png": ("Woman Yelling At Cat (local)", "imgflip", 2),
        "galaxy_brain.png": ("Galaxy Brain", "expanding_brain", 4),
    }
    added = 0
    for fname, (name, cat, boxes_n) in extras.items():
        path = TEMPLATES_DIR / fname
        if not path.exists() or fname in known_files:
            continue
        final_name = name
        if final_name in known_names:
            final_name = f"{name} local"
        try:
            with Image.open(path) as img:
                w, h = img.size
            boxes = _guess_text_boxes(w, h, boxes_n, name=final_name)
            t = Template(name=final_name, filename=fname, category=cat, text_boxes=json.dumps(boxes))
            session.add(t)
            added += 1
            print(f"      + {final_name} (local extra)")
        except Exception as e:
            print(f"      ⚠️ Failed extra {fname}: {e}")
    session.commit()
    session.close()
    return added


def seed_templates():
    """
    Internet-only seeding + current trending:
    - Trending (changes over time – good for long-term)
    - Imgflip + memegen + justmeme bulk
    - NO local blank templates in the generation pool
    """
    init_db()
    try:
        n = download_trending_templates()
        if n:
            print(f"✅ Added {n} current TRENDING templates")
    except Exception as e:
        print(f"⚠️ Trending download skipped: {e}")
    try:
        added = download_imgflip_templates(max_count=100)
        if added:
            print(f"✅ Added {added} Imgflip templates (internet)")
    except Exception as e:
        print(f"⚠️ Imgflip download skipped: {e}")
    try:
        added2 = download_memegen_templates(max_count=150)
        if added2:
            print(f"✅ Added {added2} memegen.link templates (internet)")
    except Exception as e:
        print(f"⚠️ memegen download skipped: {e}")
    try:
        added3 = download_justmeme_templates(max_count=500)
        if added3:
            print(f"✅ Added {added3} justmeme.wtf templates (internet)")
    except Exception as e:
        print(f"⚠️ justmeme download skipped: {e}")


def get_all_templates():
    session = get_session()
    templates = session.query(Template).all()
    session.close()
    return templates


def get_best_templates(limit: int = 40):
    """
    Return real photo templates from Imgflip + memegen + justmeme.
    Never returns plain dark / text-only blank templates.
    """
    session = get_session()
    real = (
        session.query(Template)
        .filter(
            (Template.filename.like("imgflip_%"))
            | (Template.filename.like("memegen_%"))
            | (Template.filename.like("justmeme_%"))
        )
        .order_by(Template.avg_score.desc(), Template.usage_count.desc())
        .limit(limit)
        .all()
    )
    session.close()
    return real

def _download_bytes(url: str, timeout: int = 15, retries: int = 3):
    """Download image bytes with simple retries."""
    last_err = None
    for attempt in range(retries):
        try:
            resp = requests.get(url, timeout=timeout)
            if resp.status_code == 200 and resp.content:
                return resp.content
            last_err = f"HTTP {resp.status_code}"
        except Exception as e:
            last_err = e
            time.sleep(0.8 * (attempt + 1))
    raise RuntimeError(last_err)
