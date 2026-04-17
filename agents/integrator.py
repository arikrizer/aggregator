import os
import sys
import json
from datetime import datetime
from groq import Groq

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

SYSTEM_PROMPT = """You are a senior analyst synthesizing daily intelligence on Human-AI Augmentation in Organizations.

You receive two lists of curated items: one from a Strategic analyst (macro trends, culture, power structures) and one from a Tactical analyst (tools, workflows, practical methods).

Your job: produce a daily digest in Hebrew.

## SELECTION RULE:
From all the incoming items, select the **10 to 15 most significant ones** for today's digest.
- Prefer items with high resonance (VIRAL > TRENDING > CITED > QUIET).
- Ensure a balance between strategic (macro) and tactical (practical) perspectives.
- Eliminate near-duplicates — keep only the most insightful version.
- Never exceed 15 items. Never drop below 10 (unless fewer than 10 unique items exist).
- The goal: maximum signal, minimum noise. Quality over quantity.

## OUTPUT FORMAT (JSON object):
{
  "date": "YYYY-MM-DD",
  "pulse": "דופק השוק — 2-3 משפטים בעברית: מה הנושא הדומיננטי היום, האם יש מתח/קונפליקט בין הפריטים, מה מפתיע",
  "top_read": {
    "title": "כותרת הפריט המומלץ לקריאה (באנגלית)",
    "url": "URL",
    "reason_hebrew": "למה דווקא זה — משפט אחד"
  },
  "items": [10-15 פריטים נבחרים, ממוינים לפי רלוונטיות — VIRAL קודם, אחר כך TRENDING, CITED, QUIET]
}

Keep the pulse honest — if items contradict each other, say so. If there's a dominant failure theme, highlight it."""


def run(strategist_items, tactician_items):
    groq = Groq(api_key=os.environ["GROQ_API_KEY"])

    all_items = strategist_items + tactician_items
    print(f"🔗 האינטגרטור — מאחד {len(strategist_items)} + {len(tactician_items)} פריטים...")

    if not all_items:
        print("  אין פריטים לאחד.")
        return None

    # Remove duplicates by URL
    seen = set()
    unique_items = []
    for item in all_items:
        url = item.get("url", "")
        if url not in seen:
            seen.add(url)
            unique_items.append(item)

    print(f"  {len(unique_items)} פריטים ייחודיים אחרי מיזוג")

    items_text = json.dumps(unique_items, ensure_ascii=False, indent=2)

    try:
        response = groq.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Today's date: {datetime.now().strftime('%Y-%m-%d')}\n\nStrategic items:\n{json.dumps(strategist_items, ensure_ascii=False)}\n\nTactical items:\n{json.dumps(tactician_items, ensure_ascii=False)}"},
            ],
            temperature=0.3,
            max_tokens=8000,
            response_format={"type": "json_object"},
        )

        digest = json.loads(response.choices[0].message.content)
        print(f"  ✅ דוח יומי נוצר")
        return digest

    except Exception as e:
        print(f"  ❌ שגיאה באינטגרטור: {e}")
        return None
