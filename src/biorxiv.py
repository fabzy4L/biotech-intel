import requests, pandas as pd
from .common import read_lines, ts_utc, save_csv_dedup, backoff

BASE = "https://api.biorxiv.org/details/biorxiv/"

def run():
    kws = read_lines("config/keywords.txt")
    rows = []

    for kw in kws or ["bioprinting"]:
        for attempt in range(3):
            try:
                r = requests.get(f"{BASE}{kw}/0/100", timeout=60)
                r.raise_for_status()
                break
            except requests.RequestException:
                if attempt == 2:
                    raise
                backoff(attempt)

        for it in r.json().get("collection", []):
            rows.append({
                "source": "bioRxiv",
                "doi": it.get("doi"),
                "title": it.get("title"),
                "authors": it.get("authors"),
                "category": it.get("category"),
                "date": it.get("date"),
                "url": f"https://www.biorxiv.org/content/{it.get('doi')}v{it.get('version')}",
                "ingested_at": ts_utc(),
            })

    df = pd.DataFrame(rows)
    if not df.empty:
        save_csv_dedup(df, "biorxiv_preprints", "doi")
    return df
