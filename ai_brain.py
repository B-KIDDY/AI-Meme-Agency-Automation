"""
3. AI Brain — LIVE topics only (no stored full meme bank)
High priority: relatable, POV, absurd, dark, reaction
"""

import json
import random
import re
from typing import Dict, List, Optional
from config import OPENAI_API_KEY, HUMOR_STYLES, RUN_MODE

_TOPIC_STRUCTURES = [
    ("Me when {topic}", "{punch}"),
    ("That feeling when {topic}", "{punch}"),
    ("Me pretending {topic} is fine", "{punch}"),
    ("My brain during {topic}", "{punch}"),
    ("POV: {topic}", "{punch}"),
    ("POV: dealing with {topic}", "{punch}"),
    ("POV: you just heard about {topic}", "{punch}"),
    ("When {topic} happens", "My reaction:"),
    ("People talking about {topic}", "Me:"),
    ("Someone mentions {topic}", "{punch}"),
    ("My face when {topic}", "{punch}"),
    ("Nobody asked but", "{topic} {punch}"),
    ("Random thought about {topic}", "{punch}"),
    ("Why does {topic} feel like", "{punch}"),
    ("Me after {topic}", "{punch}"),
    ("Expectation: {topic}", "Reality: {punch}"),
]

_PUNCHLINES = {
    "relatable": [
        "That's literally me",
        "Why is it always me",
        "I felt that",
        "Brain left the chat",
        "This is fine (it isn't)",
        "I need a nap and a raise",
        "Send help",
        "Same energy every day",
        "No thoughts just vibes",
        "I said I'd start tomorrow",
    ],
    "pov": [
        "You're not ready",
        "This is your life now",
        "Good luck explaining this",
        "No escape",
        "It's too late",
        "You already know",
        "Welcome to the club",
        "That's the whole plot",
    ],
    "absurd": [
        "And I respect that",
        "Scientists hate this",
        "Gone wrong gone viral",
        "For no reason at all",
        "As one does",
        "Chaos is the plan",
        "Make it make sense",
        "What if we just didn't",
    ],
    "dark": [
        "Laughing so I don't cry",
        "Still cheaper than therapy",
        "Pain. Just pain.",
        "Hope has left the chat",
        "I'm fine (lie)",
        "Emotional damage",
        "Nothing matters",
        "Scheduled breakdown at 3pm",
    ],
    "reaction": [
        "Real",
        "No words",
        "I'm done",
        "Not again",
        "Please stop",
        "I can't",
        "Dead",
        "Help",
    ],
    "sarcastic": [
        "Living the dream",
        "Couldn't be me (it is)",
        "Wow thanks I'm cured",
        "What a surprise",
        "Noted will ignore",
        "Peak performance",
    ],
    "gaming": [
        "Skill issue",
        "GG go next",
        "Boss fight vs real life",
        "AFK from reality",
    ],
}


def _dynamic_from_topic(style: str, topic: str, used_keys: set):
    topic_clean = re.sub(r"\s+", " ", (topic or "")).strip()
    topic_clean = re.sub(r"[^\w\s\-']", "", topic_clean)
    words = topic_clean.split()
    if len(words) > 4:
        topic_clean = " ".join(words[:4])
    if len(topic_clean) < 3:
        topic_clean = "todays news"

    punches = list(_PUNCHLINES.get(style, _PUNCHLINES["relatable"]))
    for s, plist in _PUNCHLINES.items():
        punches.extend(plist)
    punches = list(dict.fromkeys(punches))
    random.shuffle(punches)

    structs = list(_TOPIC_STRUCTURES)
    random.shuffle(structs)

    for struct_top, struct_bot in structs:
        for punch in punches:
            top = struct_top.format(topic=topic_clean, punch=punch).replace("\n", " ").strip()
            bottom = struct_bot.format(topic=topic_clean, punch=punch).strip()
            key = f"{top.upper()}||{bottom.upper()}"
            if key not in used_keys:
                return top, bottom

    punch = random.choice(punches)
    return f"Me when {topic_clean}", punch


def _local_generate(
    style: str,
    topic: Optional[str] = None,
    format_hint: str = "top_bottom",
    used_keys: Optional[set] = None,
) -> Dict:
    """ONLY live topics — never stored full caption bank."""
    if style not in _PUNCHLINES:
        style = random.choice(["relatable", "pov", "absurd", "dark", "reaction"])
    used_keys = used_keys or set()

    if not topic or len(str(topic).strip()) < 3:
        topic = random.choice([
            "monday morning", "empty fridge", "low battery", "group chat",
            "rent due", "sleep schedule", "work emails", "weekend plans",
        ])

    pair = _dynamic_from_topic(style, topic, used_keys)
    if pair:
        top, bottom = pair
    else:
        top = f"Me when {str(topic)[:40]}"
        bottom = "That's literally me"

    extras = []
    if "brain" in (format_hint or "") or "expanding" in (format_hint or ""):
        extras = [random.choice(_PUNCHLINES.get(style, _PUNCHLINES["relatable"])) for _ in range(2)]

    return {
        "top_text": top.upper()[:80],
        "bottom_text": bottom.upper()[:80],
        "extra_texts": [e.upper() for e in extras],
        "caption": f"{top} | {bottom}",
        "hashtags": _make_hashtags(style, topic),
        "style": style,
        "source": "live_topic",
        "topic": topic or "",
    }


def _make_hashtags(style: str, topic: Optional[str] = None) -> List[str]:
    base = ["#meme", "#memes", "#funny", "#relatable", f"#{style}meme"]
    if topic:
        clean = re.sub(r"[^a-zA-Z0-9]", "", topic)[:20]
        if clean:
            base.append(f"#{clean}")
    extra = ["#viral", "#dankmemes", "#humor", "#lol", "#shitpost"]
    return base + random.sample(extra, min(2, len(extra)))


def _openai_generate(style: str, topic: Optional[str], format_hint: str) -> Optional[Dict]:
    if not OPENAI_API_KEY or not str(OPENAI_API_KEY).startswith("sk-"):
        return None
    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        prompt = f"""Write a universal meme. Goal: "bro that's literally me".
Under 2 seconds to understand. No niche knowledge.
Style: {style}
Topic from today's news: {topic or 'everyday life'}
Return ONLY JSON:
{{
  "top_text": "short setup max 8 words",
  "bottom_text": "short punchline max 6 words",
  "extra_texts": [],
  "caption": "one line ig caption",
  "hashtags": ["#meme", "#relatable"]
}}"""
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.95,
            max_tokens=250,
        )
        text = resp.choices[0].message.content.strip()
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            data = json.loads(match.group())
            data["style"] = style
            data["source"] = "openai"
            data["top_text"] = data.get("top_text", "").upper()
            data["bottom_text"] = data.get("bottom_text", "").upper()
            data["topic"] = topic or ""
            return data
    except Exception as e:
        print(f"⚠️ OpenAI failed, falling back to local: {e}")
    return None


def generate_caption(
    style: Optional[str] = None,
    topic: Optional[str] = None,
    format_hint: str = "top_bottom",
    used_keys: Optional[set] = None,
) -> Dict:
    style = style or random.choice(["relatable", "pov", "absurd", "dark", "reaction"])
    result = _openai_generate(style, topic, format_hint)
    if result is None:
        result = _local_generate(style, topic, format_hint, used_keys=used_keys)
    if used_keys is not None and result:
        key = f"{result.get('top_text', '')}||{result.get('bottom_text', '')}"
        if key in used_keys:
            result = _local_generate(style, topic, format_hint, used_keys=used_keys)
    return result


def generate_batch(n: int = 20, topics: Optional[List[str]] = None) -> List[Dict]:
    results = []
    for i in range(n):
        topic = topics[i % len(topics)] if topics else None
        style = random.choices(
            ["relatable", "pov", "absurd", "dark", "reaction"],
            weights=[30, 20, 18, 15, 17],
            k=1,
        )[0]
        results.append(generate_caption(style=style, topic=topic))
    return results