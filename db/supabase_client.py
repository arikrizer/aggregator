import os
import sys
import requests
from datetime import date

sys.stdout.reconfigure(encoding="utf-8")

def get_headers():
    key = os.environ["SUPABASE_KEY"]
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "resolution=ignore-duplicates",
    }

def get_base():
    return os.environ["SUPABASE_URL"] + "/rest/v1"

def save_articles(items, agent_name, run_date=None):
    if not items:
        return
    if run_date is None:
        run_date = str(date.today())

    rows = []
    for item in items:
        rows.append({
            "run_date": run_date,
            "title": item.get("title", ""),
            "url": item.get("url", ""),
            "source_type": item.get("source_type", ""),
            "source_emoji": item.get("source_emoji", ""),
            "summary_hebrew": item.get("summary_hebrew", ""),
            "sts_angle_hebrew": item.get("sts_angle_hebrew", ""),
            "model_level": item.get("model_level"),
            "model_concept": item.get("model_concept", ""),
            "hr_relevant": item.get("hr_relevant", False),
            "resonance": item.get("resonance", ""),
            "tags": item.get("tags", []),
            "published_date": item.get("published_date", ""),
            "agent": agent_name,
        })

    resp = requests.post(
        f"{get_base()}/articles",
        headers=get_headers(),
        json=rows,
    )

    if resp.status_code in (200, 201):
        print(f"  💾 {len(rows)} פריטים נשמרו ב-Supabase ({agent_name})")
    else:
        print(f"  ⚠️ שגיאה בשמירה: {resp.status_code} {resp.text[:200]}")

def save_digest(digest, run_date=None):
    if not digest:
        return
    if run_date is None:
        run_date = str(date.today())

    top_read = digest.get("top_read", {})
    selected_urls = [i["url"] for i in digest.get("items", []) if i.get("url")]
    row = {
        "run_date": run_date,
        "pulse": digest.get("pulse", ""),
        "top_read_title": top_read.get("title", ""),
        "top_read_url": top_read.get("url", ""),
        "top_read_reason": top_read.get("reason_hebrew", ""),
        "selected_urls": selected_urls,
    }

    resp = requests.post(
        f"{get_base()}/digests",
        headers={**get_headers(), "Prefer": "resolution=merge-duplicates,return=minimal"},
        json=row,
    )
    # אם קיים — עדכן
    if resp.status_code == 409:
        resp = requests.patch(
            f"{get_base()}/digests",
            headers=get_headers(),
            params={"run_date": f"eq.{run_date}"},
            json=row,
        )

    if resp.status_code in (200, 201, 204):
        print(f"  💾 דוח יומי נשמר ב-Supabase")
    else:
        print(f"  ⚠️ שגיאה בשמירת דוח: {resp.status_code} {resp.text[:200]}")

def fetch_all_articles():
    resp = requests.get(
        f"{get_base()}/articles",
        headers=get_headers(),
        params={"order": "run_date.desc,created_at.desc", "limit": 1000},
    )
    if resp.status_code == 200:
        return resp.json()
    print(f"⚠️ שגיאה בטעינה: {resp.status_code}")
    return []

def fetch_all_digests():
    resp = requests.get(
        f"{get_base()}/digests",
        headers=get_headers(),
        params={"order": "run_date.desc", "limit": 100},
    )
    if resp.status_code == 200:
        return resp.json()
    print(f"⚠️ שגיאה בטעינה: {resp.status_code}")
    return []
