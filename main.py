#!/usr/bin/env python3
"""
AI MEME AGENCY – Main Entry Point

Usage:
  python main.py              # Run one full daily pipeline
  python main.py --dashboard  # Start web dashboard
  python main.py --seed       # Only seed templates
"""

import argparse
import sys


def main():
    parser = argparse.ArgumentParser(description="AI Meme Agency")
    parser.add_argument("--dashboard", action="store_true", help="Start Flask dashboard")
    parser.add_argument("--seed", action="store_true", help="Seed templates only")
    parser.add_argument("--quiet", action="store_true", help="Less console output")
    args = parser.parse_args()

    if args.seed:
        from template_collector import seed_templates
        from database import init_db
        init_db()
        seed_templates()
        print("Templates ready.")
        return

    if args.dashboard:
        from dashboard import app
        print("🌐 Opening dashboard at http://127.0.0.1:5000")
        app.run(host="0.0.0.0", port=5000, debug=False)
        return

    # Default: run pipeline
    from pipeline import run_daily_pipeline
    run_daily_pipeline(verbose=not args.quiet)


if __name__ == "__main__":
    main()
