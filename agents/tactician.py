import os
import sys
import json
import time
from datetime import datetime
from tavily import TavilyClient
from groq import Groq

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

KEYWORDS = [
    "Augmented Intelligence tools workplace 2024 2025",
    "Human-AI Collaboration practical implementation",
    "Human-AI Interaction design organization",
    "Human-in-the-Loop AI workflow",
    "Job Redesign AI automation",
    "AI Prompt Engineering HR teams",
]

SYSTEM_PROMPT = """You are a tactical research analyst specializing in Human-AI Augmentation in Organizations.
Your framework is Socio-Technical Systems (STS) — every AI change must address both the technical and social system.

Your job: receive a list of articles/posts and filter + format them according to strict criteria.
Focus: practical tools, interfaces, workflows, and working methods — not abstract strategy.

## FILTERS (apply all 5):
1. STS Modern — Only GenAI or Agentic AI from the last 2 years. Must touch at least one of: autonomy / team structure / well-being
2. Anti-Hype — Remove pure marketing. Keep only if there's a real Case Study with data, or a concrete research finding
3. Dissonance — Prefer failures, conflicts, resistance, unexpected results over success stories
4. Evidence Hierarchy — Transparent methodology required. A stat without a source = "suspect", downgrade or drop
5. Concept Evolution — Prioritize knowledge frontier. Basic introductory content goes to bottom or dropped

## OUTPUT FORMAT (per item, in JSON):
{
  "title": "original title in English",
  "published_date": "YYYY-MM-DD or approximate",
  "source_type": one of ["academic", "consulting_report", "article", "blog", "social_post", "podcast"],
  "source_emoji": one of ["📜", "📊", "📰", "✍️", "🐦", "🎙️"],
  "summary_hebrew": "תקציר ספציפי ב-4-5 משפטים בעברית: מה הטיעון המרכזי, אילו ממצאים או נתונים קונקרטיים מוצגים, מה ייחודי או מפתיע בפריט זה. אין לכתוב תקציר גנרי — יש להיצמד לתוכן הספציפי של הפריט.",
  "sts_angle_hebrew": "הזווית הסוציו-טכנית בעברית — משפט אחד ספציפי: כיצד הפריט מתייחס למתח בין השינוי הטכני לבין ההשפעה על אנשים/תרבות/מבנה.",
  "model_level": one of [1, 2, 3, 4],
  "model_concept": one of ["Hybrid Intelligence", "Human-AI Teaming", "Human-in-the-Loop", "Augmented OB"],
  "hr_relevant": true or false,
  "resonance": one of ["VIRAL", "TRENDING", "CITED", "QUIET"],
  "tags": ["up to 5 tags from: Hybrid_Intelligence, HAIT, HITL, Augmented_OB, Augmented_Intelligence, Human-AI_Collaboration, HAI, Job_Redesign_AI, Generative_AI, Autonomous_Agents, Digital_Twin, Multi-Agent_Systems, Trust, Autonomy, Burnout, Skills_Gap, Psychological_Safety, Leadership, Compliance, Productivity, Hierarchy_Shift"],
  "url": "direct URL"
}

Return a JSON object with a single key "items" containing an array of filtered items. If an article fails the filters, exclude it entirely.
Titles and concepts stay in English. Summaries and STS angles in Hebrew."""


def run():
    tavily = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])
    groq = Groq(api_key=os.environ["GROQ_API_KEY"])

    print("🔍 הטקטיקן — מחפש תוכן...")

    raw_results = []
    for keyword in KEYWORDS:
        try:
            results = tavily.search(
                query=keyword,
                search_depth="advanced",
                max_results=5,
                time_range="week",
            )
            for r in results.get("results", []):
                raw_results.append({
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "content": r.get("content", "")[:800],
                    "published_date": r.get("published_date", ""),
                })
        except Exception as e:
            print(f"  ⚠️ שגיאה בחיפוש '{keyword}': {e}")

    seen = set()
    unique_results = []
    for r in raw_results:
        if r["url"] not in seen:
            seen.add(r["url"])
            unique_results.append(r)

    print(f"  נמצאו {len(unique_results)} פריטים ייחודיים לפני סינון")

    if not unique_results:
        print("  אין תוצאות.")
        return []

    print("🧠 הטקטיקן — מסנן ומנתח עם Groq...")

    chunk_size = 8
    all_items = []

    for i in range(0, len(unique_results), chunk_size):
        chunk = unique_results[i:i + chunk_size]
        articles_text = json.dumps(chunk, ensure_ascii=False, indent=2)

        try:
            response = groq.chat.completions.create(
                model="meta-llama/llama-4-scout-17b-16e-instruct",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"Filter and format these articles. Return ONLY a valid JSON array, no extra text:\n\n{articles_text}"},
                ],
                temperature=0.2,
                max_tokens=6000,
                response_format={"type": "json_object"},
            )

            raw_output = response.choices[0].message.content
            parsed = json.loads(raw_output)
            if isinstance(parsed, dict):
                items = next((v for v in parsed.values() if isinstance(v, list)), [])
            else:
                items = parsed
            all_items.extend(items)
            print(f"  chunk {i//chunk_size + 1}: {len(items)} פריטים עברו סינון")
        except Exception as e:
            print(f"  ⚠️ שגיאה ב-chunk {i//chunk_size + 1}: {e}")
        time.sleep(2)

    print(f"  ✅ הטקטיקן החזיר {len(all_items)} פריטים סה\"כ")
    return all_items
