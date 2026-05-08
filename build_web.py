import os
import sys
import json
import glob
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
sys.stdout.reconfigure(encoding="utf-8")

from db.supabase_client import fetch_all_articles, fetch_all_digests

# טעינה מ-Supabase
all_articles = fetch_all_articles()
all_digests = fetch_all_digests()

# אם Supabase ריק — fallback לקבצים מקומיים
if not all_articles:
    print("Supabase ריק — טוען מקבצים מקומיים...")
    digest_files = sorted(glob.glob("output/digest_*.json"))
    raw_files = sorted(glob.glob("output/raw_*.json"))
    if not digest_files or not raw_files:
        print("אין קבצי output")
        sys.exit(1)
    with open(digest_files[-1], encoding="utf-8") as f:
        digest = json.load(f)
    with open(raw_files[-1], encoding="utf-8") as f:
        raw = json.load(f)
    all_raw = raw.get("strategist", []) + raw.get("tactician", [])
    seen = set()
    items_today = []
    for item in all_raw:
        if item["url"] not in seen:
            seen.add(item["url"])
            items_today.append(item)
    today = digest.get("date", datetime.now().strftime("%Y-%m-%d"))
    digests_by_date = {today: {
        "pulse": digest.get("pulse", ""),
        "top_read_title": digest.get("top_read", {}).get("title", ""),
        "top_read_url": digest.get("top_read", {}).get("url", ""),
        "top_read_reason": digest.get("top_read", {}).get("reason_hebrew", ""),
    }}
    articles_by_date = {today: items_today}
else:
    print(f"נטענו {len(all_articles)} פריטים ו-{len(all_digests)} דוחות מ-Supabase")
    digests_by_date = {d["run_date"]: d for d in all_digests}

    # קיבוץ לפי תאריך — dedup per day
    articles_by_date = {}
    for item in all_articles:
        d = item.get("run_date", "")[:10]
        if d not in articles_by_date:
            articles_by_date[d] = []
        articles_by_date[d].append(item)

    # סינון לפי בחירת האינטגרטור
    for d in articles_by_date:
        digest_row = digests_by_date.get(d, {})
        selected = digest_row.get("selected_urls")
        if selected:
            url_order = {url: i for i, url in enumerate(selected)}
            filtered = [a for a in articles_by_date[d] if a["url"] in url_order]
            filtered.sort(key=lambda a: url_order.get(a["url"], 999))
            articles_by_date[d] = filtered

# נרמול model_concept — underscore לרווח
CONCEPT_MAP = {
    "Hybrid_Intelligence": "Hybrid Intelligence",
    "Human-AI_Teaming": "Human-AI Teaming",
    "Human-in-the-Loop": "Human-in-the-Loop",
    "Augmented_OB": "Augmented OB",
    "Augmented_Intelligence": "Hybrid Intelligence",
}
for d in articles_by_date:
    for item in articles_by_date[d]:
        raw = item.get("model_concept", "")
        item["model_concept"] = CONCEPT_MAP.get(raw, raw)

# תאריכים מסודרים מהחדש לישן
all_dates = sorted(articles_by_date.keys(), reverse=True)
all_items_flat = [item for d in all_dates for item in articles_by_date[d]]

def format_date_he(date_str):
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        months = ["","ינואר","פברואר","מרץ","אפריל","מאי","יוני",
                  "יולי","אוגוסט","ספטמבר","אוקטובר","נובמבר","דצמבר"]
        return f"{dt.day} {months[dt.month]} {dt.year}"
    except:
        return date_str

# בניית sections לפי ימים
days_data = []
for d in all_dates:
    digest_row = digests_by_date.get(d, {})
    days_data.append({
        "date": d,
        "date_he": format_date_he(d),
        "pulse": digest_row.get("pulse", ""),
        "top_read_title": digest_row.get("top_read_title", ""),
        "top_read_url": digest_row.get("top_read_url", ""),
        "top_read_reason": digest_row.get("top_read_reason", ""),
        "items": articles_by_date[d],
    })

latest_date_he = days_data[0]["date_he"] if days_data else ""
total_items = len(all_items_flat)

items_json = json.dumps(all_items_flat, ensure_ascii=False)
days_json = json.dumps(days_data, ensure_ascii=False)

# --- Pre-render feed HTML so crawlers & LLMs can read the content ---
import html as _html

RESONANCE_ICONS = {"VIRAL": "🔥", "TRENDING": "💬", "CITED": "🎓", "QUIET": "🔇"}
CONCEPT_LEVEL_PY = {
    "Hybrid Intelligence": 1,
    "Human-AI Teaming": 2,
    "Human-in-the-Loop": 3,
    "Augmented OB": 4,
}

def _e(s):
    """Escape HTML special chars."""
    return _html.escape(str(s or ""), quote=True)

def build_feed_html(days_data, all_items_flat):
    url_to_idx = {item["url"]: i for i, item in enumerate(all_items_flat)}
    parts = []
    for di, day in enumerate(days_data):
        # day header
        pulse_html = ""
        if day["pulse"]:
            pulse_html = f"""
      <div class="pulse-box">
        <div class="pulse-label">⚡ דופק השוק</div>
        <div class="pulse-text">{_e(day["pulse"])}</div>
      </div>"""

        top_read_html = ""
        if day["top_read_title"]:
            tr_url   = _e(day["top_read_url"])
            tr_title = _e(day["top_read_title"])
            tr_reason = _e(day["top_read_reason"])
            top_read_html = f"""
      <div class="top-read-box">
        <div class="top-read-icon">⭐</div>
        <div class="top-read-content">
          <div class="top-read-label">מומלץ לקריאה</div>
          <div class="top-read-title"><a href="{tr_url}" target="_blank">{tr_title}</a></div>
          <div class="top-read-reason">{tr_reason}</div>
          <label class="card-checkbox" style="margin-top:8px;">
            <input type="checkbox" onchange="toggleReading('{tr_url}', '{tr_title}', -1)">
            הוסף לרשימת קריאה
          </label>
        </div>
      </div>"""

        cards_html = []
        for ii, item in enumerate(day["items"]):
            idx = url_to_idx.get(item["url"], -1)
            concept = item.get("model_concept", "")
            level   = CONCEPT_LEVEL_PY.get(concept) or item.get("model_level", "")
            res     = item.get("resonance", "")
            icon    = RESONANCE_ICONS.get(res, "")
            hr_badge = '<span class="badge badge-hr">📢 HR</span>' if item.get("hr_relevant") else ""
            pub = f'<span class="badge" style="background:#f7fafc;color:#718096;border:1px solid #e2e8f0">{_e(item["published_date"])}</span>' if item.get("published_date") else ""
            tags_html = " ".join(
                f'<span class="tag" onclick="filterByTag(\'{_e(t)}\'">#{_e(t.replace("_"," "))}</span>'
                for t in (item.get("tags") or [])
            )
            item_url   = _e(item.get("url",""))
            item_title = _e(item.get("title",""))
            cards_html.append(f"""
    <div class="card" id="card-{di}-{ii}" data-idx="{idx}">
      <div class="card-top">
        <span class="source-emoji">{item.get("source_emoji","📰")}</span>
        <div class="card-title"><a href="{item_url}" target="_blank">{item_title}</a></div>
      </div>
      <div class="badges">
        <span class="badge badge-{_e(res)}">{icon} {_e(res)}</span>
        <span class="badge badge-level">רמה {level} · {_e(concept)}</span>
        {hr_badge}{pub}
      </div>
      <div class="summary">{_e(item.get("summary_hebrew",""))}</div>
      <div class="sts">⬡ STS — {_e(item.get("sts_angle_hebrew",""))}</div>
      <div class="tags">{tags_html}</div>
      <label class="card-checkbox">
        <input type="checkbox" onchange="toggleReading('{item_url}', '{item_title}', {idx})">
        הוסף לרשימת קריאה
      </label>
    </div>""")

        parts.append(f"""
  <div class="day-section" id="day-{di}">
    <div class="day-date-simple" id="day-date-simple-{di}" style="display:none; font-size:0.85rem; color:#718096; font-weight:600; margin-bottom:10px; padding: 4px 0;">{day["date_he"]}</div>
    <div class="day-header">
      <div class="day-title">⚡ <span>{day["date_he"]}</span> — {len(day["items"])} פריטים</div>
      <div class="day-divider"></div>
      <div class="day-summary">{pulse_html}{top_read_html}</div>
    </div>
    {"".join(cards_html)}
  </div>""")
    return "\n".join(parts)

feed_html = build_feed_html(days_data, all_items_flat)

html = f"""<!DOCTYPE html>
<html lang="he" dir="rtl">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>האגרגטור — Human-AI Augmentation</title>
  <meta name="description" content="אגרגטור תוכן יומי בתחום Human-AI Augmentation — Hybrid Intelligence, Human-AI Teaming, Human-in-the-Loop ו-Augmented OB. סקירה, ניתוח וזווית STS מדי יום.">
  <meta property="og:type" content="website">
  <meta property="og:url" content="https://arikrizer.github.io/aggregator/">
  <meta property="og:title" content="האגרגטור — Human-AI Augmentation">
  <meta property="og:description" content="אגרגטור תוכן יומי בתחום Human-AI Augmentation — Hybrid Intelligence, Human-AI Teaming, Human-in-the-Loop ו-Augmented OB. סקירה, ניתוח וזווית STS מדי יום.">
  <meta property="og:image" content="https://arikrizer.github.io/aggregator/assets/og-image.png">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="האגרגטור — Human-AI Augmentation">
  <meta name="twitter:description" content="אגרגטור תוכן יומי בתחום Human-AI Augmentation — Hybrid Intelligence, Human-AI Teaming, Human-in-the-Loop ו-Augmented OB. סקירה, ניתוח וזווית STS מדי יום.">
  <meta name="twitter:image" content="https://arikrizer.github.io/aggregator/assets/og-image.png">
  <link rel="alternate" type="application/json" title="Aggregator Feed" href="https://arikrizer.github.io/aggregator/feed.json">
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}

    body {{
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      background: #f7f8fc;
      color: #1a202c;
      min-height: 100vh;
    }}

    header {{
      background: #fff;
      border-bottom: 1px solid #e2e8f0;
      padding: 20px 32px;
      display: flex;
      align-items: center;
      justify-content: space-between;
    }}

    header h1 {{ font-size: 1.4rem; font-weight: 700; color: #1a202c; letter-spacing: -0.5px; }}
    header h1 span {{ color: #7c3aed; }}
    .date-badge {{ font-size: 0.83rem; color: #718096; }}

    .layout {{
      max-width: 1200px;
      margin: 0 auto;
      padding: 32px 20px;
      display: flex;
      gap: 32px;
      align-items: flex-start;
    }}

    .sidebar {{
      width: 220px;
      flex-shrink: 0;
      position: sticky;
      top: 24px;
    }}

    .sidebar-title {{
      font-size: 0.95rem;
      color: #4a5568;
      font-weight: 600;
      margin-bottom: 12px;
    }}

    .tag-cloud {{ display: flex; flex-wrap: wrap; gap: 6px; }}
    .tag-cloud.expanded {{ max-height: 220px; overflow-y: auto; }}
    .tag-expand-btn {{ margin-top: 8px; font-size: 0.78rem; color: #7c3aed; cursor: pointer; background: none; border: none; padding: 0; text-decoration: underline; }}

    .cloud-tag {{
      cursor: pointer;
      color: #6b46c1;
      background: #faf5ff;
      border: 1px solid #e9d8fd;
      border-radius: 4px;
      padding: 3px 8px;
      line-height: 1.4;
      transition: all 0.15s;
    }}
    .cloud-tag:hover {{ background: #7c3aed; color: #fff; border-color: #7c3aed; }}
    .cloud-tag.tag-active {{ background: #7c3aed !important; color: #fff !important; border-color: #7c3aed !important; }}

    .reading-list {{ margin-top: 28px; }}
    .reading-list-title {{ font-size: 0.95rem; color: #4a5568; font-weight: 600; margin-bottom: 10px; }}
    .reading-list-empty {{ font-size: 0.82rem; color: #cbd5e0; }}
    .reading-item {{ display: flex; align-items: flex-start; gap: 6px; margin-bottom: 8px; }}
    .reading-item a {{ font-size: 0.92rem; color: #4a5568; text-decoration: none; line-height: 1.4; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }}
    .reading-item a:hover {{ color: #7c3aed; }}
    .reading-item button {{ background: none; border: none; color: #cbd5e0; cursor: pointer; font-size: 0.75rem; padding: 0; flex-shrink: 0; margin-top: 1px; }}
    .reading-item button:hover {{ color: #fc8181; }}

    .container {{ flex: 1; min-width: 0; }}

    .filters-sticky {{
      position: sticky;
      top: 0;
      z-index: 100;
      background: #f7f8fc;
      padding: 12px 0 8px;
      margin-bottom: 8px;
      border-bottom: 2px solid #e2e8f0;
    }}

    .stats-bar {{ display: flex; gap: 16px; margin-bottom: 12px; flex-wrap: wrap; }}
    .stat {{ background: #fff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 10px 16px; font-size: 0.85rem; color: #4a5568; }}
    .stat strong {{ color: #1a202c; font-size: 1.1rem; display: block; }}

    .filters {{ display: flex; gap: 8px; margin-bottom: 6px; flex-wrap: wrap; }}
    .filter-btn {{ background: #fff; border: 1px solid #e2e8f0; color: #4a5568; padding: 6px 14px; border-radius: 20px; font-size: 0.83rem; cursor: pointer; transition: all 0.2s; }}
    .filter-btn:hover, .filter-btn.active {{ background: #7c3aed; border-color: #7c3aed; color: #fff; }}

    /* הפרדה יומית */
    .day-section {{ margin-bottom: 40px; }}

    .day-header {{
      background: #fff;
      border: 1px solid #e2e8f0;
      border-radius: 14px;
      padding: 20px 24px;
      margin-bottom: 16px;
    }}

    .day-title {{
      font-size: 1.2rem;
      font-weight: 700;
      color: #1a202c;
      margin-bottom: 12px;
      display: flex;
      align-items: center;
      gap: 10px;
    }}

    .day-title span {{ color: #7c3aed; }}

    .day-divider {{
      height: 2px;
      background: linear-gradient(to left, transparent, #e9d8fd, transparent);
      margin-bottom: 12px;
    }}

    .pulse-box {{
      background: #faf5ff;
      border-radius: 8px;
      padding: 12px 16px;
      margin-bottom: 10px;
    }}
    .pulse-label {{ font-size: 0.72rem; text-transform: uppercase; letter-spacing: 1px; color: #7c3aed; font-weight: 700; margin-bottom: 4px; }}
    .pulse-text {{ font-size: 0.95rem; color: #2d3748; line-height: 1.6; }}

    .top-read-box {{
      background: #fffbeb;
      border-radius: 8px;
      padding: 10px 14px;
      display: flex;
      align-items: flex-start;
      gap: 10px;
    }}
    .top-read-icon {{ font-size: 1.1rem; flex-shrink: 0; }}
    .top-read-content {{ flex: 1; }}
    .top-read-label {{ font-size: 0.72rem; text-transform: uppercase; letter-spacing: 1px; color: #b7791f; font-weight: 700; margin-bottom: 3px; }}
    .top-read-title {{ font-size: 0.9rem; font-weight: 600; color: #1a202c; }}
    .top-read-title a {{ color: inherit; text-decoration: none; }}
    .top-read-title a:hover {{ color: #7c3aed; }}
    .top-read-reason {{ font-size: 0.82rem; color: #92400e; margin-top: 2px; }}

    /* כרטיסים */
    .card {{
      background: #fff;
      border: 1px solid #e2e8f0;
      border-radius: 12px;
      padding: 20px 24px;
      margin-bottom: 12px;
      transition: border-color 0.2s, box-shadow 0.2s;
    }}
    .card:hover {{ border-color: #c4b5fd; box-shadow: 0 2px 12px rgba(124,58,237,0.07); }}
    .card.highlight {{ border-color: #7c3aed; box-shadow: 0 0 0 3px rgba(124,58,237,0.15); }}
    .card.hidden {{ display: none; }}

    .card-top {{ display: flex; align-items: flex-start; gap: 12px; margin-bottom: 12px; }}
    .source-emoji {{ font-size: 1.2rem; flex-shrink: 0; margin-top: 2px; }}
    .card-title {{ font-size: 1.05rem; font-weight: 600; color: #1a202c; line-height: 1.4; flex: 1; }}
    .card-title a {{ color: inherit; text-decoration: none; }}
    .card-title a:hover {{ color: #7c3aed; }}

    .badges {{ display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 10px; }}
    .badge {{ font-size: 0.75rem; padding: 2px 8px; border-radius: 4px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; }}
    .badge-VIRAL    {{ background: #fff0f0; color: #c53030; border: 1px solid #fed7d7; }}
    .badge-TRENDING {{ background: #ebf8ff; color: #2b6cb0; border: 1px solid #bee3f8; }}
    .badge-CITED    {{ background: #f0fff4; color: #276749; border: 1px solid #c6f6d5; }}
    .badge-QUIET    {{ background: #f7fafc; color: #718096; border: 1px solid #e2e8f0; }}
    .badge-level {{ background: #faf5ff; color: #6b46c1; border: 1px solid #e9d8fd; }}
    .badge-hr {{ background: #fffbeb; color: #b7791f; border: 1px solid #fefcbf; }}

    .summary {{ font-size: 1.0rem; color: #4a5568; line-height: 1.7; margin-bottom: 10px; }}
    .sts {{ font-size: 1.0rem; color: #6b46c1; background: #faf5ff; border-right: 3px solid #7c3aed; padding: 6px 10px; border-radius: 0 4px 4px 0; margin-bottom: 10px; }}

    .tags {{ display: flex; gap: 6px; flex-wrap: wrap; }}
    .tag {{ font-size: 0.75rem; color: #718096; background: #edf2f7; padding: 2px 8px; border-radius: 4px; cursor: pointer; }}
    .tag:hover {{ color: #6b46c1; background: #faf5ff; }}
    .tag-active {{ color: #fff !important; background: #7c3aed !important; }}

    .card-checkbox {{ display: flex; align-items: center; gap: 6px; margin-top: 10px; font-size: 0.82rem; color: #a0aec0; cursor: pointer; user-select: none; }}
    .card-checkbox input {{ accent-color: #7c3aed; cursor: pointer; }}
    .card-checkbox:hover {{ color: #7c3aed; }}

    .day-empty {{ text-align: center; color: #a0aec0; padding: 20px; font-size: 0.9rem; display: none; }}
    .day-empty.visible {{ display: block; }}

    @media (max-width: 768px) {{
      header {{ padding: 14px 16px; flex-direction: column; align-items: flex-start; gap: 6px; }}
      header h1 {{ font-size: 1.1rem; }}
      .layout {{ flex-direction: column; padding: 16px 12px; gap: 20px; }}
      .sidebar {{ width: 100%; position: static; }}
      .reading-list {{ display: none; }}
      .card {{ padding: 14px 16px; }}
      .card-title {{ font-size: 0.95rem; }}
      .summary, .sts {{ font-size: 0.9rem; }}
      .day-header {{ padding: 14px 16px; }}
      .day-title {{ font-size: 1rem; }}
    }}
  </style>
</head>
<body>

<header>
  <h1>ה<span>אגרגטור</span> — Human-AI Augmentation</h1>
  <span class="date-badge">{latest_date_he}</span>
</header>
<div style="background:#faf5ff; border-bottom:1px solid #e9d8fd; padding:6px 32px; font-size:0.8rem; color:#6b46c1; text-align:center;">
  🤖 לקריאה על ידי AI —
  <a href="https://arikrizer.github.io/aggregator/feed.txt" style="color:#7c3aed; text-decoration:none; font-weight:600;" target="_blank">feed.txt</a>
  &nbsp;|&nbsp;
  <a href="https://arikrizer.github.io/aggregator/feed.json" style="color:#7c3aed; text-decoration:none; font-weight:600;" target="_blank">feed.json</a>
</div>

<div class="layout">
  <div class="sidebar">
    <div class="sidebar-title">🏷️ תגיות</div>
    <div class="tag-cloud" id="tag-cloud"></div>
    <button class="tag-expand-btn" id="tag-expand-btn" onclick="toggleTagCloud()" style="display:none">הצג הכל ▾</button>
    <div class="reading-list">
      <div class="reading-list-title">📌 לקריאה</div>
      <div id="reading-list"><span class="reading-list-empty">אין פריטים עדיין</span></div>
    </div>
  </div>

  <div class="container">

    <div class="filters-sticky">
      <div class="stats-bar" id="stats"></div>
      <div class="filters">
        <button class="filter-btn active" onclick="filterBy('all', event)">הכל</button>
        <button class="filter-btn" onclick="filterBy('VIRAL', event)">🔥 Viral</button>
        <button class="filter-btn" onclick="filterBy('TRENDING', event)">💬 Trending</button>
        <button class="filter-btn" onclick="filterBy('CITED', event)">🎓 Cited</button>
        <button class="filter-btn" onclick="filterBy('QUIET', event)">🔇 Quiet</button>
        <button class="filter-btn" onclick="filterBy('hr', event)">📢 HR Relevant</button>
      </div>
      <div class="filters">
        <button class="filter-btn filter-level" onclick="filterBy('level_1', event)">1️⃣ Hybrid Intelligence</button>
        <button class="filter-btn filter-level" onclick="filterBy('level_2', event)">2️⃣ Human-AI Teaming</button>
        <button class="filter-btn filter-level" onclick="filterBy('level_3', event)">3️⃣ Human-in-the-Loop</button>
        <button class="filter-btn filter-level" onclick="filterBy('level_4', event)">4️⃣ Augmented OB</button>
      </div>
    </div>

    <div id="feed">{feed_html}</div>
    <div id="no-results" style="display:none; text-align:center; color:#a0aec0; padding:40px; font-size:0.95rem;">אין פריטים התואמים את הסינון</div>

  </div>
</div>

<script>
const DAYS = {days_json};
const ALL_ITEMS = {items_json};
const RESONANCE_ICONS = {{ VIRAL: '🔥', TRENDING: '💬', CITED: '🎓', QUIET: '🔇' }};
const CONCEPT_LEVEL = {{
  'Hybrid Intelligence': 1,
  'Human-AI Teaming': 2,
  'Human-in-the-Loop': 3,
  'Augmented OB': 4
}};

let currentFilter = 'all';
let currentTag = null;

function loadReadingList() {{
  try {{
    const saved = JSON.parse(localStorage.getItem('aggregator_reading') || '[]');
    return new Map(saved);
  }} catch {{ return new Map(); }}
}}

function saveReadingList() {{
  localStorage.setItem('aggregator_reading', JSON.stringify([...readingList.entries()]));
}}

let readingList = loadReadingList();

function toggleReading(url, title, idx) {{
  if (readingList.has(url)) readingList.delete(url);
  else readingList.set(url, {{ title, idx }});
  saveReadingList();
  renderReadingList();
  applyFilters();
}}

function removeReading(url) {{
  readingList.delete(url);
  saveReadingList();
  renderReadingList();
  applyFilters();
}}

function scrollToCard(idx) {{
  const cardEl = document.querySelector(`[data-idx="${{idx}}"]`);
  if (!cardEl) {{
    currentFilter = 'all'; currentTag = null;
    document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
    document.querySelector('.filter-btn').classList.add('active');
    updateSummaryVisibility(); renderTagCloud(); applyFilters();
    setTimeout(() => scrollToCard(idx), 150);
    return;
  }}
  cardEl.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
  cardEl.classList.add('highlight');
  setTimeout(() => cardEl.classList.remove('highlight'), 1800);
}}

function renderReadingList() {{
  const el = document.getElementById('reading-list');
  if (readingList.size === 0) {{ el.innerHTML = '<span class="reading-list-empty">אין פריטים עדיין</span>'; return; }}
  el.innerHTML = [...readingList.entries()].map(([url, {{title, idx}}]) => `
    <div class="reading-item">
      <button onclick="removeReading('${{url}}')" title="הסר">✕</button>
      <a href="#" onclick="scrollToCard(${{idx}}); return false;">${{title}}</a>
    </div>
  `).join('');
}}

function filterBy(type, e) {{
  currentFilter = type; currentTag = null;
  document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
  if (e) e.target.classList.add('active');
  renderTagCloud(); updateSummaryVisibility(); applyFilters();
}}

function filterByTag(tag) {{
  currentTag = (currentTag === tag) ? null : tag;
  if (currentTag) {{ currentFilter = 'all'; document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active')); document.querySelector('.filter-btn').classList.add('active'); }}
  renderTagCloud(); updateSummaryVisibility(); applyFilters();
}}

function itemVisible(item) {{
  if (currentFilter === 'hr' && !item.hr_relevant) return false;
  if (currentFilter === 'level_1' && item.model_concept !== 'Hybrid Intelligence') return false;
  if (currentFilter === 'level_2' && item.model_concept !== 'Human-AI Teaming') return false;
  if (currentFilter === 'level_3' && item.model_concept !== 'Human-in-the-Loop') return false;
  if (currentFilter === 'level_4' && item.model_concept !== 'Augmented OB') return false;
  if (currentFilter !== 'all' && currentFilter !== 'hr' && !currentFilter.startsWith('level_') && item.resonance !== currentFilter) return false;
  if (currentTag && !(item.tags||[]).includes(currentTag)) return false;
  return true;
}}

function updateSummaryVisibility() {{
  const showFull = currentFilter === 'all' && !currentTag;
  document.querySelectorAll('.day-header').forEach(el => {{
    el.style.display = showFull ? '' : 'none';
  }});
  document.querySelectorAll('.day-date-simple').forEach(el => {{
    el.style.display = showFull ? 'none' : '';
  }});
}}

function applyFilters() {{
  let totalVisible = 0;
  DAYS.forEach((day, di) => {{
    let visibleCount = 0;
    day.items.forEach((item, ii) => {{
      const el = document.getElementById('card-' + di + '-' + ii);
      if (!el) return;
      if (itemVisible(item)) {{ el.classList.remove('hidden'); visibleCount++; totalVisible++; }}
      else el.classList.add('hidden');
    }});
    const dateSimple = document.getElementById('day-date-simple-' + di);
    if (dateSimple && dateSimple.style.display !== 'none') {{
      dateSimple.style.display = visibleCount > 0 ? '' : 'none';
    }}
  }});
  const noResults = document.getElementById('no-results');
  if (noResults) {{ noResults.style.display = totalVisible === 0 ? '' : 'none'; }}
}}

function renderStats() {{
  const viral = ALL_ITEMS.filter(i => i.resonance === 'VIRAL').length;
  const trending = ALL_ITEMS.filter(i => i.resonance === 'TRENDING').length;
  const cited = ALL_ITEMS.filter(i => i.resonance === 'CITED').length;
  const hr = ALL_ITEMS.filter(i => i.hr_relevant).length;
  const days = DAYS.length;
  document.getElementById('stats').innerHTML = `
    <div class="stat"><strong>${{ALL_ITEMS.length}}</strong>פריטים</div>
    <div class="stat"><strong>${{days}}</strong>ימים</div>
    <div class="stat"><strong>${{viral}} 🔥 ${{trending}} 💬 ${{cited}} 🎓</strong>תהודה</div>
    <div class="stat"><strong>${{hr}} 📢</strong>HR</div>
  `;
}}

let tagCloudExpanded = false;
const TAG_PREVIEW = 6;

function toggleTagCloud() {{
  tagCloudExpanded = !tagCloudExpanded;
  const cloud = document.getElementById('tag-cloud');
  const btn = document.getElementById('tag-expand-btn');
  cloud.classList.toggle('expanded', tagCloudExpanded);
  btn.textContent = tagCloudExpanded ? 'סגור ▴' : 'הצג הכל ▾';
  renderTagCloud();
}}

function renderTagCloud() {{
  const counts = {{}};
  ALL_ITEMS.forEach(item => (item.tags||[]).forEach(t => counts[t] = (counts[t]||0) + 1));
  const max = Math.max(...Object.values(counts));
  const min = Math.min(...Object.values(counts));
  const sorted = Object.entries(counts).filter(([tag, count]) => count >= 3).sort((a,b) => b[1]-a[1]);
  const visible = tagCloudExpanded ? sorted : sorted.slice(0, TAG_PREVIEW);
  document.getElementById('tag-cloud').innerHTML = visible.map(([tag, count]) => {{
    const size = min===max ? 0.9 : 0.75 + ((count-min)/(max-min))*0.65;
    return `<span class="cloud-tag ${{currentTag===tag?'tag-active':''}}" style="font-size:${{size.toFixed(2)}}rem" onclick="filterByTag('${{tag}}')">#${{tag.replace(/_/g,' ')}}</span>`;
  }}).join('');
  const btn = document.getElementById('tag-expand-btn');
  if (btn) btn.style.display = sorted.length > TAG_PREVIEW ? '' : 'none';
}}

renderStats();
renderTagCloud();
renderReadingList();
applyFilters();
</script>
</body>
</html>"""

os.makedirs("docs", exist_ok=True)
with open("docs/index.html", "w", encoding="utf-8") as f:
    f.write(html)

# --- feed.json ---
feed_items = []
for day in days_data:
    for item in day["items"]:
        status = []
        if item.get("resonance"):
            status.append(item["resonance"])
        if item.get("hr_relevant"):
            status.append("HR Relevant")
        feed_items.append({
            "title":    item.get("title", ""),
            "url":      item.get("url", ""),
            "date":     day["date"],
            "category": item.get("model_concept", ""),
            "summary":  item.get("summary_hebrew", ""),
            "tags":     item.get("tags", []),
            "status":   status,
        })

feed_json = json.dumps({
    "feed_url": "https://arikrizer.github.io/aggregator/feed.json",
    "home_page_url": "https://arikrizer.github.io/aggregator/",
    "title": "האגרגטור — Human-AI Augmentation",
    "description": "אגרגטור תוכן יומי בתחום Human-AI Augmentation",
    "items": feed_items,
}, ensure_ascii=False, indent=2)

with open("docs/feed.json", "w", encoding="utf-8") as f:
    f.write(feed_json)

# --- feed.txt ---
txt_lines = [
    "האגרגטור — Human-AI Augmentation",
    "https://arikrizer.github.io/aggregator/",
    f"עודכן: {latest_date_he}",
    "=" * 60,
    "",
]
for item in feed_items:
    txt_lines.append(f"כותרת: {item['title']}")
    txt_lines.append(f"קישור: {item['url']}")
    txt_lines.append(f"תאריך: {item['date']}")
    txt_lines.append(f"קטגוריה: {item['category']}")
    if item["status"]:
        txt_lines.append(f"סטטוס: {', '.join(item['status'])}")
    if item["summary"]:
        txt_lines.append(f"תיאור: {item['summary']}")
    if item["tags"]:
        txt_lines.append(f"תגיות: {', '.join(item['tags'])}")
    txt_lines.append("---")
    txt_lines.append("")

with open("docs/feed.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(txt_lines))

print(f"✅ דף עודכן — {len(all_dates)} ימים, {total_items} פריטים")
print(f"✅ feed.json — {len(feed_items)} פריטים")
print(f"✅ feed.txt — {len(feed_items)} פריטים")
