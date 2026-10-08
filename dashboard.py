"""
Simple Flask Dashboard
View generated memes, scores, performance, and trigger a new run.
"""

import os
from pathlib import Path
from flask import Flask, render_template_string, send_from_directory, jsonify, request
from database import init_db, get_session, Meme, Performance, Template, LearningStat
from config import GENERATED_DIR, TEMPLATES_DIR
from pipeline import run_daily_pipeline

app = Flask(__name__)
init_db()

HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>AI Meme Agency</title>
  <style>
    :root { --bg:#0f0f13; --card:#1a1a24; --accent:#7c5cfc; --text:#e8e8f0; --muted:#888; }
    * { box-sizing:border-box; margin:0; padding:0; }
    body { font-family: system-ui, sans-serif; background:var(--bg); color:var(--text); padding:24px; }
    h1 { font-size:1.8rem; margin-bottom:8px; }
    .sub { color:var(--muted); margin-bottom:24px; }
    .grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(280px,1fr)); gap:16px; }
    .card { background:var(--card); border-radius:12px; overflow:hidden; border:1px solid #2a2a3a; }
    .card img { width:100%; display:block; background:#111; }
    .card .body { padding:12px; }
    .score { color:var(--accent); font-weight:700; }
    .meta { font-size:0.8rem; color:var(--muted); margin-top:4px; }
    .btn { background:var(--accent); color:#fff; border:none; padding:10px 18px; border-radius:8px;
           cursor:pointer; font-weight:600; margin-bottom:20px; }
    .btn:hover { opacity:0.9; }
    .stats { display:flex; gap:20px; margin-bottom:24px; flex-wrap:wrap; }
    .stat { background:var(--card); padding:12px 20px; border-radius:10px; }
    .stat b { display:block; font-size:1.4rem; }
  </style>
</head>
<body>
  <h1>🤖 AI Meme Agency</h1>
  <p class="sub">Automated meme discovery → generation → ranking → publishing</p>

  <form method="POST" action="/run" style="display:inline">
    <button class="btn" type="submit">▶ Run Daily Pipeline Now</button>
  </form>

  <div class="stats">
    <div class="stat"><b>{{ total_memes }}</b>Memes</div>
    <div class="stat"><b>{{ published }}</b>Published</div>
    <div class="stat"><b>{{ templates }}</b>Templates</div>
    <div class="stat"><b>{{ avg_score }}</b>Avg Score</div>
  </div>

  <div class="grid">
    {% for m in memes %}
    <div class="card">
      {% if m.filename %}
      <img src="/memes/{{ m.filename }}" alt="meme" loading="lazy">
      {% endif %}
      <div class="body">
        <div class="score">★ {{ '%.3f'|format(m.total_score or 0) }}</div>
        <div>{{ m.top_text[:60] }}</div>
        <div>{{ m.bottom_text[:60] }}</div>
        <div class="meta">
          {{ m.style }} · {{ m.created_at.strftime('%Y-%m-%d %H:%M') if m.created_at else '' }}
          {% if m.is_published %} · ✅ Published{% endif %}
        </div>
      </div>
    </div>
    {% else %}
    <p>No memes yet. Click the button above to generate the first batch.</p>
    {% endfor %}
  </div>
</body>
</html>
"""


@app.route("/")
def index():
    session = get_session()
    memes = (
        session.query(Meme)
        .order_by(Meme.total_score.desc())
        .limit(40)
        .all()
    )
    total = session.query(Meme).count()
    published = session.query(Meme).filter(Meme.is_published == True).count()
    templates = session.query(Template).count()
    avg = session.query(Meme).filter(Meme.total_score > 0).count()
    avg_score = 0.0
    if avg:
        from sqlalchemy import func
        avg_score = session.query(func.avg(Meme.total_score)).scalar() or 0
    session.close()

    return render_template_string(
        HTML,
        memes=memes,
        total_memes=total,
        published=published,
        templates=templates,
        avg_score=f"{avg_score:.3f}",
    )


@app.route("/memes/<path:filename>")
def serve_meme(filename):
    return send_from_directory(GENERATED_DIR, filename)


@app.route("/templates/<path:filename>")
def serve_template(filename):
    return send_from_directory(TEMPLATES_DIR, filename)


@app.route("/run", methods=["POST"])
def run_pipeline():
    result = run_daily_pipeline(verbose=False)
    return jsonify(result)


@app.route("/api/stats")
def api_stats():
    session = get_session()
    styles = session.query(LearningStat).filter(LearningStat.key.like("style:%")).all()
    session.close()
    return jsonify({s.key: s.value for s in styles})


if __name__ == "__main__":
    print("🌐 Dashboard → http://127.0.0.1:5000")
    app.run(host="0.0.0.0", port=5000, debug=False)
