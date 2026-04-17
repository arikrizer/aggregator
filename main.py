import os
import sys
import json
from datetime import datetime
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

load_dotenv()

from agents.strategist import run as run_strategist
from agents.tactician import run as run_tactician
from agents.integrator import run as run_integrator
from db.supabase_client import save_articles, save_digest


def main():
    print(f"\n{'='*50}")
    print(f"האגרגטור — הרצה {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*50}\n")

    strategist_items = run_strategist()
    save_articles(strategist_items, "strategist")
    print()
    tactician_items = run_tactician()
    save_articles(tactician_items, "tactician")
    print()
    digest = run_integrator(strategist_items, tactician_items)
    save_digest(digest)

    os.makedirs("output", exist_ok=True)
    date_str = datetime.now().strftime("%Y%m%d_%H%M")

    # Save raw items
    raw_filename = f"output/raw_{date_str}.json"
    with open(raw_filename, "w", encoding="utf-8") as f:
        json.dump({
            "strategist": strategist_items,
            "tactician": tactician_items,
        }, f, ensure_ascii=False, indent=2)

    # Save digest
    if digest:
        digest_filename = f"output/digest_{date_str}.json"
        with open(digest_filename, "w", encoding="utf-8") as f:
            json.dump(digest, f, ensure_ascii=False, indent=2)
        print(f"\n💾 דוח יומי נשמר: {digest_filename}")

        print(f"\n{'='*50}")
        print(f"דופק השוק:")
        print(digest.get("pulse", ""))
        print(f"\nמומלץ לקריאה: {digest.get('top_read', {}).get('title', '')}")
        print(f"למה: {digest.get('top_read', {}).get('reason_hebrew', '')}")

        items = digest.get("items", [])
        print(f"\nסה\"כ {len(items)} פריטים:")
        for i, item in enumerate(items, 1):
            hr = "📢" if item.get("hr_relevant") else "  "
            print(f"{i}. {hr} [{item.get('resonance','?')}] {item.get('title','?')[:65]}")
    else:
        print("\n❌ לא נוצר דוח יומי.")

    print(f"\nנשמר גם: {raw_filename}")


if __name__ == "__main__":
    main()
