"""
9. Analytics AI + 10. Self-Learning AI
Tracks engagement (simulated or real) and updates learning stats
so future ranking & template selection improve.
"""

import random
from datetime import datetime
from database import get_session, Meme, Performance, LearningStat, Template


def simulate_engagement(meme_id: int) -> dict:
    """Generate realistic-looking engagement numbers based on the meme's viral_score."""
    session = get_session()
    meme = session.query(Meme).filter(Meme.id == meme_id).first()
    if not meme:
        session.close()
        return {}

    base = meme.viral_score or 0.5
    likes = int(random.gauss(80 * base, 40) * random.uniform(0.7, 1.6))
    comments = int(likes * random.uniform(0.02, 0.12))
    shares = int(likes * random.uniform(0.01, 0.08))
    saves = int(likes * random.uniform(0.03, 0.15))
    reach = int(likes * random.uniform(4, 18))

    likes = max(0, likes)
    comments = max(0, comments)
    shares = max(0, shares)
    saves = max(0, saves)
    reach = max(likes, reach)

    perf = Performance(
        meme_id=meme_id,
        likes=likes,
        comments=comments,
        shares=shares,
        saves=saves,
        reach=reach,
    )
    session.add(perf)
    session.commit()
    session.close()

    return {
        "meme_id": meme_id,
        "likes": likes,
        "comments": comments,
        "shares": shares,
        "saves": saves,
        "reach": reach,
    }


def update_learning(meme_id: int, engagement: dict):
    """
    Update LearningStat based on performance.
    Higher engagement → boost the style / template / etc.
    """
    session = get_session()
    meme = session.query(Meme).filter(Meme.id == meme_id).first()
    if not meme:
        session.close()
        return

    # Engagement score 0-1
    eng = min(1.0, (engagement.get("likes", 0) / 300.0) * 0.5
              + (engagement.get("saves", 0) / 50.0) * 0.3
              + (engagement.get("shares", 0) / 30.0) * 0.2)

    keys = [
        f"style:{meme.style}",
        f"template:{meme.template.category if meme.template else 'unknown'}",
    ]

    for key in keys:
        stat = session.query(LearningStat).filter(LearningStat.key == key).first()
        if not stat:
            stat = LearningStat(key=key, value=0.5)
            session.add(stat)
        # Exponential moving average
        stat.value = round(stat.value * 0.85 + eng * 0.15, 4)
        stat.updated_at = datetime.utcnow()

    # Also update template avg_score
    if meme.template:
        t = meme.template
        old = t.avg_score or 0.5
        t.avg_score = round(old * 0.8 + eng * 0.2, 4)
        t.usage_count = (t.usage_count or 0) + 1

    session.commit()
    session.close()


def collect_and_learn(meme_ids: list):
    """Batch: simulate engagement + update learning for a list of published memes."""
    results = []
    for mid in meme_ids:
        eng = simulate_engagement(mid)
        if eng:
            update_learning(mid, eng)
            results.append(eng)
    return results


def get_top_performing_styles(limit: int = 5):
    session = get_session()
    stats = (
        session.query(LearningStat)
        .filter(LearningStat.key.like("style:%"))
        .order_by(LearningStat.value.desc())
        .limit(limit)
        .all()
    )
    session.close()
    return [(s.key.replace("style:", ""), s.value) for s in stats]
