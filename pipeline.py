"""
Daily Workflow Orchestrator
generate → filter → rank → publish → learn
"""

import json
import random
from datetime import datetime
from pathlib import Path

from config import MEMES_TO_GENERATE, MEMES_TO_KEEP, HUMOR_STYLES, GENERATED_DIR
from database import init_db, get_session, Meme, Template
from trend_discovery import discover_trends, get_hot_topics
from template_collector import seed_templates, get_best_templates, get_all_templates
from ai_brain import generate_caption
from meme_generator import create_meme_from_template
from quality_checker import check_meme
from ranking_engine import score_meme
from instagram_publisher import publish_meme
from analytics_ai import collect_and_learn, get_top_performing_styles


def run_daily_pipeline(verbose: bool = True):
    print("=" * 60)
    print(f"🚀 AI MEME AGENCY – Daily Pipeline  |  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)

    init_db()
    seed_templates()

    print("\n📡 1. Discovering trends...")
    trends = discover_trends(30)
    topics = get_hot_topics(16)
    if verbose:
        print(f"   Hot topics: {', '.join(topics)}")

    print("\n🖼️  2. Selecting best templates (internet only)...")
    try:
        from template_collector import (
            download_imgflip_templates,
            download_memegen_templates,
            download_justmeme_templates,
            download_trending_templates,
        )
        download_trending_templates()
        download_imgflip_templates(max_count=100)
        download_memegen_templates(max_count=150)
        download_justmeme_templates(max_count=300)
    except Exception as e:
        print(f"   ⚠️ Template refresh skipped: {e}")

    all_templates = get_all_templates()
    BAD_NAME_PARTS = (
        "trade offer", "watermark", "imgflip.com", "made with",
        "i receive", "you receive", "always has been", "boardroom",
        "suggestion", "waiting skeleton", "first world problems",
        "change my mind", "grus plan", "gru's plan",
    )
    templates = [
        t for t in all_templates
        if t.filename and (
            t.filename.startswith("imgflip_")
            or t.filename.startswith("memegen_")
            or t.filename.startswith("justmeme_")
        )
        and not any(b in (t.name or "").lower() for b in BAD_NAME_PARTS)
    ]

    if not templates:
        print("   ❌ No internet templates found – run: python main.py --seed")
        return {"generated": 0, "passed": 0, "kept": 0, "published": 0, "top_ids": []}

    session = get_session()
    used_forever_ids = {
        row[0]
        for row in session.query(Meme.template_id)
        .filter(Meme.template_id.isnot(None))
        .distinct()
        .all()
        if row[0]
    }
    session.close()

    fresh = [t for t in templates if t.id not in used_forever_ids]

    if not fresh:
        print("   ⚠️ No never-used templates left – downloading more…")
        try:
            from template_collector import (
                download_imgflip_templates,
                download_memegen_templates,
                download_justmeme_templates,
            )
            download_imgflip_templates(max_count=100)
            download_memegen_templates(max_count=150)
            download_justmeme_templates(max_count=400)
        except Exception as e:
            print(f"   ⚠️ Extra download failed: {e}")
        all_templates = get_all_templates()
        fresh = [
            t for t in all_templates
            if t.filename and (
                t.filename.startswith("imgflip_")
                or t.filename.startswith("memegen_")
                or t.filename.startswith("justmeme_")
            )
            and t.id not in used_forever_ids
        ]

    if not fresh:
        print("   ❌ No unused templates left (forever ban).")
        return {"generated": 0, "passed": 0, "kept": 0, "published": 0, "top_ids": []}

    templates = fresh
    print(f"   Forever-blocked: {len(used_forever_ids)}")
    print(f"   Never-used left: {len(templates)}")
    random.shuffle(templates)
    templates = templates[:MEMES_TO_GENERATE]
    print(f"   Using {len(templates)} brand-new templates")

    print(f"\n🧠 3-4. Generating {len(templates)} meme ideas & images...")
    session = get_session()
    existing_hashes = [m.phash for m in session.query(Meme.phash).filter(Meme.phash.isnot(None)).all()]
    used_caption_keys = set()
    for top, bottom in session.query(Meme.top_text, Meme.bottom_text).all():
        used_caption_keys.add(f"{(top or '').upper()}||{(bottom or '').upper()}")
    session.close()

    candidates = []
    for i, template in enumerate(templates):
        if topics:
            topic = topics[i % len(topics)]
        else:
            topic = f"today update {random.randint(1000, 9999)}"

        # High priority: relatable, POV, absurd, dark, reaction
        style = random.choices(
            ["relatable", "pov", "absurd", "dark", "reaction", "sarcastic", "gaming"],
            weights=[30, 20, 18, 15, 12, 3, 2],
            k=1,
        )[0]

        caption = generate_caption(
            style=style,
            topic=topic,
            format_hint=template.category,
            used_keys=used_caption_keys,
        )
        print(f"   · [{style}] {topic[:45]} → {str(caption.get('top_text', ''))[:40]}")
        cap_key = f"{caption.get('top_text', '')}||{caption.get('bottom_text', '')}"
        used_caption_keys.add(cap_key)

        session = get_session()
        meme = Meme(
            template_id=template.id,
            top_text=caption.get("top_text", ""),
            bottom_text=caption.get("bottom_text", ""),
            caption=caption.get("caption", ""),
            style=style,
            filename="",
        )
        session.add(meme)
        session.commit()
        meme_id = meme.id
        session.close()

        try:
            out_path = create_meme_from_template(template, caption, meme_id)
        except Exception as e:
            print(f"   ⚠️ Generation failed for #{meme_id}: {e}")
            continue

        report = check_meme(
            out_path,
            caption.get("top_text", ""),
            caption.get("bottom_text", ""),
            caption.get("caption", ""),
            existing_hashes,
        )
        scores = score_meme(
            caption.get("top_text", ""),
            caption.get("bottom_text", ""),
            style,
            template.category,
            topic or "",
        )

        session = get_session()
        meme = session.query(Meme).filter(Meme.id == meme_id).first()
        if meme:
            meme.filename = out_path.name
            meme.phash = report["phash"]
            meme.is_duplicate = report["is_duplicate"]
            meme.is_nsfw = report["is_nsfw"]
            meme.funny_score = scores["funny_score"]
            meme.relatable_score = scores["relatable_score"]
            meme.trending_score = scores["trending_score"]
            meme.original_score = scores["original_score"]
            meme.viral_score = scores["viral_score"]
            meme.total_score = scores["total_score"]
            session.commit()
        session.close()

        if report["passed"]:
            candidates.append({
                "id": meme_id,
                "path": out_path,
                "caption": caption,
                "scores": scores,
                "template": template.name,
            })
            existing_hashes.append(report["phash"])
            if verbose and (i + 1) % 5 == 0:
                print(f"   Generated {i+1}/{len(templates)} ...")
        else:
            if verbose:
                print(f"   ❌ Filtered meme #{meme_id}: {report['reasons']}")

    candidates.sort(key=lambda x: x["scores"]["total_score"], reverse=True)
    top = candidates[:MEMES_TO_KEEP]
    print(f"\n🏆 5-6. Kept top {len(top)} memes (from {len(candidates)} that passed quality)")
    for c in top:
        print(f"   • #{c['id']}  score={c['scores']['total_score']:.3f}  "
              f"[{c['template']}]  {c['caption'].get('top_text', '')[:40]}...")

    print("\n📤 7-8. Publishing / scheduling...")
    published_ids = []
    for c in top:
        publish_meme(
            c["id"],
            c["path"],
            c["caption"].get("caption", ""),
            c["caption"].get("hashtags", []),
        )
        published_ids.append(c["id"])

    print("\n📊 9-10. Collecting engagement & updating learning model...")
    eng_results = collect_and_learn(published_ids)
    for e in eng_results[:3]:
        print(f"   Meme #{e['meme_id']}: ❤️ {e['likes']}  💬 {e['comments']}  🔄 {e['shares']}")

    styles = get_top_performing_styles(5)
    if styles:
        print("\n📈 Top styles by learned performance:")
        for s, v in styles:
            print(f"   {s}: {v:.3f}")

    print("\n✅ Pipeline complete. Tomorrow's memes will be smarter.")
    print("=" * 60)
    return {
        "generated": len(templates),
        "passed": len(candidates),
        "kept": len(top),
        "published": len(published_ids),
        "top_ids": published_ids,
    }


if __name__ == "__main__":
    run_daily_pipeline(verbose=True)