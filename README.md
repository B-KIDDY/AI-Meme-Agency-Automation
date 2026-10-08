# 🤖 AI Meme Agency

**Fully automated meme discovery → AI captioning → high-quality generation → ranking → Instagram publishing → self-learning system.**

Works **out of the box** in simulation mode (no API keys required).  
Add your OpenAI + Instagram Graph API keys for live operation.

---

## Features (all 10 modules)

| # | Module                    | Status |
|---|---------------------------|--------|
| 1 | Trend Discovery Engine    | ✅ Curated + random (ready for Reddit/Twitter APIs) |
| 2 | Meme Template Collector   | ✅ 10 classic templates auto-seeded |
| 3 | AI Brain                  | ✅ Local humor engine + optional OpenAI |
| 4 | Meme Generator            | ✅ Pillow, auto font size, outline, HD export |
| 5 | Quality Checker           | ✅ pHash duplicates, OCR, NSFW/offensive filter |
| 6 | AI Ranking Engine         | ✅ Funny / Relatable / Trending / Original / Viral |
| 7 | Database                  | ✅ SQLite (SQLAlchemy) – templates, memes, performance, learning |
| 8 | Instagram Publisher       | ✅ Simulation + Graph API ready |
| 9 | Analytics AI              | ✅ Engagement tracking (simulated or real) |
|10 | Self-Learning AI          | ✅ Updates style/template scores from performance |

---

## Quick Start

```bash
# 1. Unzip and enter
cd ai_meme_agency

# 2. Install dependencies
pip install -r requirements.txt

# 3. (Optional) copy env and add keys
cp .env.example .env
# edit .env → OPENAI_API_KEY=sk-...   RUN_MODE=live

# 4. Run one full daily pipeline
python main.py

# 5. Or start the dashboard
python main.py --dashboard
# → open http://127.0.0.1:5000
```

---

## Daily Workflow (exactly as designed)

```
08:00 AM
   │
   ▼ Collect trending topics & templates
   ▼ AI selects best templates
   ▼ Generate N meme ideas (default 30)
   ▼ Create finished meme images
   ▼ Quality filter (duplicates / NSFW / empty)
   ▼ Rank & keep top K (default 10)
   ▼ Publish / schedule to Instagram
   ▼ Collect engagement data
   ▼ Self-learning updates rankings
   ▼ Tomorrow’s memes are better
```

---

## Project Structure

```
ai_meme_agency/
├── main.py                 # Entry point
├── pipeline.py             # Full daily orchestrator
├── config.py
├── database.py
├── trend_discovery.py
├── template_collector.py
├── ai_brain.py
├── meme_generator.py
├── quality_checker.py
├── ranking_engine.py
├── instagram_publisher.py
├── analytics_ai.py
├── dashboard.py
├── requirements.txt
├── .env.example
├── templates/              # Blank meme templates
├── generated_memes/        # Output PNGs
├── data/                   # SQLite DB
└── logs/                   # Publish log
```

---

## Configuration (`.env`)

| Variable                      | Default | Description |
|-------------------------------|---------|-------------|
| `RUN_MODE`                    | `sim`   | `sim` = offline, `live` = real APIs |
| `OPENAI_API_KEY`              |         | Optional – falls back to local engine |
| `INSTAGRAM_ACCESS_TOKEN`      |         | Graph API token |
| `INSTAGRAM_BUSINESS_ACCOUNT_ID` |       | IG Business account ID |
| `MEMES_TO_GENERATE`           | 30      | Ideas per run |
| `MEMES_TO_KEEP`               | 10      | Final posts per run |
| `HUMOR_STYLES`                | relatable,dark,gaming,... | Comma list |

---

## Notes

- **Simulation mode** is fully functional: generates real meme images, ranks them, “publishes” to a log, simulates likes/comments, and improves future rankings.
- Templates are procedurally generated classic formats (Drake, Expanding Brain, Top/Bottom, etc.). Replace the PNGs in `templates/` with real meme images if you want authentic backgrounds.
- For production Instagram posting you need a public image URL (CDN) + Facebook App with Instagram Graph permissions.
- Tesseract OCR is used for quality checks (already present on most Linux systems).

---

## License

MIT – build your empire.

## Database location

By default the SQLite database is created at `/tmp/ai_meme_agency.db` (works in restricted environments).
To keep data between reboots, edit `config.py` and set:

```python
DB_PATH = DATA_DIR / "meme_agency.db"
```


---

## Real Instagram Posting

See **[INSTAGRAM_SETUP.md](INSTAGRAM_SETUP.md)** for the complete step-by-step guide.

Quick summary:
1. Instagram Business account linked to a Facebook Page
2. Facebook App + long-lived Page Access Token
3. Instagram Business Account ID
4. Public image host (Imgur Client-ID is the easiest)

Then set in `.env`:
```
RUN_MODE=live
INSTAGRAM_ACCESS_TOKEN=...
INSTAGRAM_BUSINESS_ACCOUNT_ID=...
IMGUR_CLIENT_ID=...
```

The system will automatically upload the image and publish via the official Graph API.
