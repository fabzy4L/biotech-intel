import requests, pandas as pd
from .common import read_lines, ts_utc, save_csv_dedup, backoff

BASE = "https://clinicaltrials.gov/api/v2/studies"

def _fetch_page(params):
    for attempt in range(3):
        try:
            r = requests.get(BASE, params=params, timeout=60)
            r.raise_for_status()
            return r.json()
        except requests.RequestException:
            if attempt == 2:
                raise
            backoff(attempt)

def run():
    sponsors = read_lines("config/sponsors.txt")
    rows = []

    for sponsor in sponsors or ["Novartis"]:
        params = {
            "query.spons": sponsor,
            "pageSize": 100,
            "format": "json",
        }
        while True:
            data = _fetch_page(params)
            for study in data.get("studies", []):
                ps = study.get("protocolSection", {})
                id_mod = ps.get("identificationModule", {})
                cond_mod = ps.get("conditionsModule", {})
                arms_mod = ps.get("armsInterventionsModule", {})
                design_mod = ps.get("designModule", {})
                status_mod = ps.get("statusModule", {})
                sponsor_mod = ps.get("sponsorCollaboratorsModule", {})

                nct_id = id_mod.get("nctId", "")
                interventions = [i.get("name", "") for i in arms_mod.get("interventions", [])]
                rows.append({
                    "source": "ClinicalTrials",
                    "nct_id": nct_id,
                    "title": id_mod.get("briefTitle", ""),
                    "condition": "; ".join(cond_mod.get("conditions", [])),
                    "intervention": "; ".join(interventions),
                    "phase": "; ".join(design_mod.get("phases", [])),
                    "status": status_mod.get("overallStatus", ""),
                    "start_date": (status_mod.get("startDateStruct") or {}).get("date", ""),
                    "last_update": (status_mod.get("lastUpdatePostDateStruct") or {}).get("date", ""),
                    "sponsor": (sponsor_mod.get("leadSponsor") or {}).get("name", ""),
                    "url": f"https://clinicaltrials.gov/study/{nct_id}",
                    "ingested_at": ts_utc(),
                })

            next_token = data.get("nextPageToken")
            if not next_token:
                break
            params["pageToken"] = next_token

    df = pd.DataFrame(rows)
    if not df.empty:
        save_csv_dedup(df, "clinical_trials", "nct_id")
    return df
