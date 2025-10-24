import requests, pandas as pd
from .common import read_lines, ts_utc, save_csv

BASE="https://api.biorxiv.org/details/biorxiv/"

def run():
    kws = read_lines("config/keywords.txt")
    rows=[]
    for kw in kws or ["bioprinting"]:
        r = requests.get(f"{BASE}{kw}/0/100", timeout=60)
        r.raise_for_status()
        for it in r.json().get("collection", []):
            rows.append({
                "source":"bioRxiv",
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
        save_csv(df, "biorxiv_preprints")
    return df
