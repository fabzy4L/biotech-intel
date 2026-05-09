import requests, pandas as pd
from .common import ts_utc, save_csv_dedup, backoff, stable_hash

URL = "https://api.fda.gov/drug/drugsfda.json"

def run():
    params = {"search": "products.application_type:(BLA NDA)", "limit": 100}

    for attempt in range(3):
        try:
            r = requests.get(URL, params=params, timeout=60)
            r.raise_for_status()
            break
        except requests.RequestException:
            if attempt == 2:
                raise
            backoff(attempt)

    data = r.json().get("results", [])
    rows = []
    for it in data:
        app = it.get("application_number", "")
        sponsor = it.get("sponsor_name", "")
        for p in it.get("products", []):
            for a in p.get("approval_dates", []):
                approval_date = a.get("approval_date", "")
                rows.append({
                    "source": "FDA",
                    "accession": stable_hash(f"{app}|{approval_date}"),
                    "company": sponsor,
                    "application": app,
                    "product": p.get("brand_name"),
                    "dosage_form": p.get("dosage_form"),
                    "route": p.get("route"),
                    "approval_date": approval_date,
                    "event_type": "approval",
                    "url": f"https://www.accessdata.fda.gov/scripts/cder/daf/index.cfm?event=overview.process&ApplNo={app}",
                    "ingested_at": ts_utc(),
                })

    df = pd.DataFrame(rows)
    if not df.empty:
        save_csv_dedup(df, "fda_approvals", "accession")
    return df
