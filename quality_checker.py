"""
5. Quality Checker
- Duplicate detection via perceptual hash
- OCR text comparison
- Basic NSFW / offensive filtering
- Watermark-ish detection (very simple)
"""

import os
import re
from pathlib import Path
from typing import Tuple, List
import imagehash
from PIL import Image
import pytesseract

# Simple offensive word list (expand as needed)
OFFENSIVE_PATTERNS = [
    r"\b(nazi|hitler|kill yourself|kys)\b",
    r"\b(nigger|faggot|retard)\b",  # hard filters
]

NSFW_KEYWORDS = [
    "nude", "naked", "porn", "sex", "xxx", "onlyfans", "nsfw",
]


def compute_phash(image_path: Path) -> str:
    try:
        img = Image.open(image_path)
        return str(imagehash.phash(img))
    except Exception:
        return ""


def is_duplicate(phash: str, existing_hashes: List[str], threshold: int = 5) -> bool:
    """Return True if too similar to any existing meme."""
    if not phash:
        return False
    try:
        h = imagehash.hex_to_hash(phash)
        for eh in existing_hashes:
            if not eh:
                continue
            dist = h - imagehash.hex_to_hash(eh)
            if dist <= threshold:
                return True
    except Exception:
        pass
    return False


def ocr_text(image_path: Path) -> str:
    # OCR is optional & can be slow; skip by default for speed.
    # Set ENABLE_OCR=1 in environment to turn it on.
    if os.getenv("ENABLE_OCR", "0") != "1":
        return ""
    try:
        img = Image.open(image_path)
        text = pytesseract.image_to_string(img)
        return text.strip().lower()
    except Exception:
        return ""


def contains_offensive(text: str) -> bool:
    text = text.lower()
    for pat in OFFENSIVE_PATTERNS:
        if re.search(pat, text, re.IGNORECASE):
            return True
    return False


def is_nsfw(text: str, caption: str = "") -> bool:
    combined = (text + " " + caption).lower()
    return any(kw in combined for kw in NSFW_KEYWORDS)


def check_meme(
    image_path: Path,
    top_text: str,
    bottom_text: str,
    caption: str,
    existing_hashes: List[str],
) -> dict:
    """
    Returns quality report:
    {
      "passed": bool,
      "is_duplicate": bool,
      "is_offensive": bool,
      "is_nsfw": bool,
      "phash": str,
      "ocr_text": str,
      "reasons": list
    }
    """
    reasons = []
    phash = compute_phash(image_path)
    ocr = ocr_text(image_path)

    is_dup = is_duplicate(phash, existing_hashes)
    if is_dup:
        reasons.append("duplicate_image")

    full_text = f"{top_text} {bottom_text} {caption} {ocr}"
    offensive = contains_offensive(full_text)
    if offensive:
        reasons.append("offensive_content")

    nsfw = is_nsfw(full_text, caption)
    if nsfw:
        reasons.append("nsfw")

    # Very basic readability / emptiness check
    if len(top_text.strip()) < 2 and len(bottom_text.strip()) < 2:
        reasons.append("empty_text")

    passed = len(reasons) == 0

    return {
        "passed": passed,
        "is_duplicate": is_dup,
        "is_offensive": offensive,
        "is_nsfw": nsfw,
        "phash": phash,
        "ocr_text": ocr[:200],
        "reasons": reasons,
    }
