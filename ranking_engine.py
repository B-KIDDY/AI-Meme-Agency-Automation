"""
6. AI Ranking Engine
Scores every meme on Funny / Relatable / Trending / Original / Viral potential.
Uses simple heuristics + historical learning stats.
"""

import random
from typing import Dict
from database import get_session, LearningStat


def _get_learning_boost(key: str) -> float:
    session = get_session()
    stat = session.query(LearningStat).filter(LearningStat.key == key).first()
    session.close()
    if stat:
        return min(0.25, max(-0.15, (stat.value - 0.5) * 0.3))
    return 0.0


def score_meme(
    top_text: str,
    bottom_text: str,
    style: str,
    template_category: str,
    topic: str = "",
) -> Dict[str, float]:
    """
    Returns scores 0-1 for each dimension + total.
    """
    text = f"{top_text} {bottom_text}".lower()
    words = text.split()

    # Funny: length balance, punch, presence of contrast words
    funny = 0.55
    if 4 <= len(words) <= 18:
        funny += 0.15
    if any(w in text for w in ["vs", "when", "me", "nobody", "expect"]):
        funny += 0.1
    if len(top_text) > 5 and len(bottom_text) > 5:
        funny += 0.08
    funny += random.uniform(-0.05, 0.12)
    funny += _get_learning_boost(f"style:{style}")

    # Relatable
    relatable = 0.5
    relatable_words = ["me", "my", "when", "everyone", "nobody", "why", "how"]
    relatable += 0.08 * sum(1 for w in relatable_words if w in text)
    relatable = min(0.95, relatable + random.uniform(-0.05, 0.1))
    relatable += _get_learning_boost(f"style:{style}:relatable")

    # Trending (boost if topic/style historically good)
    trending = 0.45 + random.uniform(0, 0.3)
    trending += _get_learning_boost(f"template:{template_category}")
    trending += _get_learning_boost(f"topic:{topic[:30]}") if topic else 0

    # Originality (penalize very common phrases a bit, reward unusual)
    original = 0.6
    common = ["when you", "me explaining", "nobody:", "expectation vs reality"]
    if any(c in text for c in common):
        original -= 0.12
    if len(set(words)) / max(1, len(words)) > 0.8:
        original += 0.1
    original += random.uniform(-0.08, 0.15)

    # Viral potential (combination + length)
    viral = (funny * 0.35 + relatable * 0.25 + trending * 0.25 + original * 0.15)
    viral += random.uniform(-0.05, 0.08)

    # Clamp
    def clamp(v):
        return round(max(0.05, min(0.99, v)), 3)

    scores = {
        "funny_score": clamp(funny),
        "relatable_score": clamp(relatable),
        "trending_score": clamp(trending),
        "original_score": clamp(original),
        "viral_score": clamp(viral),
    }
    scores["total_score"] = round(
        scores["funny_score"] * 0.3
        + scores["relatable_score"] * 0.2
        + scores["trending_score"] * 0.15
        + scores["original_score"] * 0.15
        + scores["viral_score"] * 0.2,
        3,
    )
    return scores
