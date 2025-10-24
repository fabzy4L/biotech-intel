import requests, pandas as pd
from .common import ts_utc, save_csv

URL = "https://api.fda.gov/drug/drugsfda.json"  # approvals via openFDA (subset)
# fallback note: for full CDER files, switch to FDA data files CSV if needed.

def run():
    params = {"search":"products.application_type:(\"BLA\"+\"NDA\")","limit":100}
    r = requests.get(URL, params=params, timeout=60)
    r.raise_for_status()
    data = r.json().get("results", [])
    rows = []
    for it in data:
        app = it.get("application_number")
        sponsor = it.get("sponsor_name")
        for p in it.get("products", []):
            for a in p.get("approval_dates", []):
                rows.append({
                    "source":"FDA",
                    "company": sponsor,
                    "application": app,
                    "product": p.get("brand_name"),
                    "dosage_form": p.get("dosage_form"),
                    "route": p.get("route"),
                    "approval_date": a.get("approval_date"),
                    "event_type":"approval",
                    "url": f"https://www.accessdata.fda.gov/scripts/cder/daf/index.cfm?event=overview.process&ApplNo={app}",
                    "ingested_at": ts_utc(),
                })
    df = pd.DataFrame(rows)
    if not df.empty:
        save_csv(df, "fda_approvals")
    return df
