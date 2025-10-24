import requests, pandas as pd, urllib.parse as u
from .common import read_lines, ts_utc, save_csv

BASE = "https://clinicaltrials.gov/api/query/study_fields"
FIELDS = "NCTId,Condition,InterventionName,Phase,OverallStatus,StartDate,LastUpdatePostDate,LeadSponsorName,BriefTitle"

def run():
    sponsors = read_lines("config/sponsors.txt")
    q = " OR ".join([f'AREA[LeadSponsorName]{u.quote_plus(s)}' for s in sponsors]) or "AREA[Phase]Early Phase 1"
    params = {"expr": q, "fields": FIELDS, "min_rnk": 1, "max_rnk": 500, "fmt":"json"}
    r = requests.get(BASE, params=params, timeout=60)
    r.raise_for_status()
    studies = r.json()["StudyFieldsResponse"]["StudyFields"]
    rows=[]
    for s in studies:
        rows.append({
            "source":"ClinicalTrials",
            "nct_id": ";".join(s.get("NCTId",[])),
            "title": ";".join(s.get("BriefTitle",[])),
            "condition": ";".join(s.get("Condition",[])),
            "intervention": ";".join(s.get("InterventionName",[])),
            "phase": ";".join(s.get("Phase",[])),
            "status": ";".join(s.get("OverallStatus",[])),
            "start_date": ";".join(s.get("StartDate",[])),
            "last_update": ";".join(s.get("LastUpdatePostDate",[])),
            "sponsor": ";".join(s.get("LeadSponsorName",[])),
            "url": f"https://clinicaltrials.gov/study/{';'.join(s.get('NCTId',[]))}",
            "ingested_at": ts_utc(),
        })
    df = pd.DataFrame(rows)
    if not df.empty:
        save_csv(df, "clinical_trials")
    return df
