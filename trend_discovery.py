"""
1. Trend Discovery Engine

Live worldwide sources (no API keys required):
  • Google News RSS (top stories + world)
  • Reddit public JSON (r/all, r/memes, r/news, r/worldnews)
  • FreeNewsAPI headlines (if reachable)
  • Fallback: rotating local world-event pool
"""

import re
import random
import xml.etree.ElementTree as ET
from datetime import datetime, date
from typing import List, Dict, Optional
import requests

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; AI-Meme-Agency/2.0; +https://localhost)",
    "Accept": "application/json, text/xml, */*",
}


def _clean_topic(text: str, max_words: int = 6) -> str:
    """Turn a headline into a short meme-friendly topic."""
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"^(BREAKING|UPDATE|LIVE|JUST IN)[:\-\s]+", "", text, flags=re.I)
    text = re.sub(r"\s*[\|\-–—]\s*.*$", "", text)
    words = text.split()
    if len(words) > max_words:
        text = " ".join(words[:max_words])
    return text.strip(" .,:;!-")[:60]


def _fetch_google_news() -> List[Dict]:
    feeds = [
        "https://news.google.com/rss?hl=en-US&gl=US&ceid=US:en",
        "https://news.google.com/rss/headlines/section/topic/WORLD?hl=en-US&gl=US&ceid=US:en",
        "https://news.google.com/rss/headlines/section/topic/TECHNOLOGY?hl=en-US&gl=US&ceid=US:en",
        "https://news.google.com/rss/headlines/section/topic/BUSINESS?hl=en-US&gl=US&ceid=US:en",
        "https://news.google.com/rss/headlines/section/topic/SPORTS?hl=en-US&gl=US&ceid=US:en",
        "https://news.google.com/rss/headlines/section/topic/ENTERTAINMENT?hl=en-US&gl=US&ceid=US:en",
    ]
    results = []
    for url in feeds:
        try:
            resp = requests.get(url, timeout=12, headers=HEADERS)
            if resp.status_code != 200:
                continue
            root = ET.fromstring(resp.content)
            for item in root.findall(".//item")[:12]:
                title = (item.findtext("title") or "").strip()
                topic = _clean_topic(title)
                if len(topic) < 8:
                    continue
                results.append({
                    "type": "topic",
                    "value": topic,
                    "score": 0.92 + random.uniform(0, 0.08),
                    "source": "google_news",
                    "discovered_at": datetime.utcnow().isoformat(),
                })
        except Exception as e:
            print(f"   ⚠️ Google News feed failed: {e}")
    return results


def _fetch_reddit_hot() -> List[Dict]:
    subs = ["all", "news", "worldnews", "technology", "memes", "funny", "pics"]
    results = []
    for sub in subs:
        try:
            url = f"https://www.reddit.com/r/{sub}/hot.json?limit=15"
            resp = requests.get(url, timeout=12, headers=HEADERS)
            if resp.status_code != 200:
                continue
            data = resp.json()
            for child in data.get("data", {}).get("children", []):
                post = child.get("data", {})
                title = (post.get("title") or "").strip()
                if post.get("over_18"):
                    continue
                topic = _clean_topic(title, max_words=7)
                if len(topic) < 8:
                    continue
                ups = int(post.get("ups") or 0)
                results.append({
                    "type": "topic",
                    "value": topic,
                    "score": min(0.98, 0.7 + min(ups, 50000) / 50000 * 0.25),
                    "source": f"reddit/{sub}",
                    "discovered_at": datetime.utcnow().isoformat(),
                })
        except Exception as e:
            print(f"   ⚠️ Reddit r/{sub} failed: {e}")
    return results


def _fetch_free_news() -> List[Dict]:
    results = []
    queries = ["world", "technology", "sports", "politics", "celebrity"]
    for q in queries:
        try:
            url = f"https://freenewsapi.ai/v1/search?q={q}&size=8"
            resp = requests.get(url, timeout=12, headers=HEADERS)
            if resp.status_code != 200:
                continue
            data = resp.json()
            for art in data.get("results") or data.get("articles") or []:
                title = (art.get("title") or "").strip()
                topic = _clean_topic(title)
                if len(topic) < 8:
                    continue
                results.append({
                    "type": "topic",
                    "value": topic,
                    "score": 0.88 + random.uniform(0, 0.1),
                    "source": "freenewsapi",
                    "discovered_at": datetime.utcnow().isoformat(),
                })
        except Exception as e:
            print(f"   ⚠️ FreeNewsAPI failed: {e}")
    return results


def _fetch_imgflip_popular() -> List[Dict]:
    try:
        resp = requests.get("https://api.imgflip.com/get_memes", timeout=10, headers=HEADERS)
        data = resp.json()
        if not data.get("success"):
            return []
        results = []
        for m in data["data"]["memes"]:
            results.append({
                "type": "format",
                "value": m["name"],
                "score": 0.75 + random.uniform(0, 0.2),
                "source": "imgflip",
                "template_id": m["id"],
                "template_url": m["url"],
                "width": m.get("width"),
                "height": m.get("height"),
                "box_count": m.get("box_count", 2),
                "discovered_at": datetime.utcnow().isoformat(),
            })
        return results
    except Exception as e:
        print(f"   ⚠️ Imgflip fetch failed: {e}")
        return []


def get_popular_imgflip_templates(limit: int = 100) -> List[Dict]:
    all_t = [t for t in _fetch_imgflip_popular() if t.get("template_url")]
    return all_t[:limit] if limit else all_t


BASE_TOPICS = [
    "AI taking jobs", "ChatGPT vs humans", "coding at 3am", "remote work",
    "Monday motivation", "coffee addiction", "procrastination", "adulting fails",
    "dating apps", "introvert energy", "burnout", "rent prices", "job interviews",
    "sleep schedule", "gym excuses", "phone addiction", "group chat silence",
    "climate debates", "heatwave survival", "stock market", "tech layoffs",
    "viral scandal", "new phone launch", "flight delays", "food inflation",
    "power outage", "app outage", "streaming wars", "quiet quitting",
]


def _fallback_topics(n: int = 16) -> List[Dict]:
    pool = list(BASE_TOPICS)
    random.shuffle(pool)
    return [{
        "type": "topic",
        "value": t,
        "score": 0.5 + random.uniform(0, 0.2),
        "source": "fallback",
        "discovered_at": datetime.utcnow().isoformat(),
    } for t in pool[:n]]


def discover_trends(limit: int = 30) -> List[Dict]:
    trends: List[Dict] = []

    print("   🌍 Fetching live Google News headlines…")
    trends.extend(_fetch_google_news())

    print("   👽 Fetching Reddit hot posts…")
    trends.extend(_fetch_reddit_hot())

    print("   📰 Fetching FreeNewsAPI headlines…")
    trends.extend(_fetch_free_news())

    print("   🖼️  Fetching Imgflip popular formats…")
    trends.extend(_fetch_imgflip_popular())

    live_topics = [t for t in trends if t.get("type") == "topic"]
    if len(live_topics) < 8:
        print("   ⚠️ Few live topics – adding fallback pool")
        trends.extend(_fallback_topics(16))

    seen = set()
    unique = []
    for t in trends:
        key = (t.get("value") or "").lower()[:70]
        if not key or key in seen:
            continue
        seen.add(key)
        unique.append(t)

    unique.sort(key=lambda x: x.get("score", 0), reverse=True)
    print(f"   ✅ {len(unique)} unique trends ({len([x for x in unique if x['type']=='topic'])} topics)")
    return unique[:limit]


def get_hot_topics(n: int = 16) -> List[str]:
    trends = discover_trends(max(n * 4, 40))
    topics = [t["value"] for t in trends if t.get("type") == "topic"]
    seen = set()
    out = []
    for t in topics:
        k = t.lower()
        if k not in seen:
            seen.add(k)
            out.append(t)
    if len(out) < n:
        extra = list(BASE_TOPICS)
        random.shuffle(extra)
        for t in extra:
            if t.lower() not in seen:
                out.append(t)
            if len(out) >= n:
                break
    random.shuffle(out)
    return out[:n]