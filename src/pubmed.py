import requests, pandas as pd
from urllib.parse import quote_plus
from .common import read_lines, ts_utc, save_csv_dedup, backoff

ESEARCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
ESUMMARY = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"

def _get(url, params):
    for attempt in range(3):
        try:
            r = requests.get(url, params=params, timeout=60)
            r.raise_for_status()
            return r
        except requests.RequestException:
            if attempt == 2:
                raise
            backoff(attempt)

def run():
    kws = read_lines("config/keywords.txt")
    query = " OR ".join(kws) if kws else "bioprinting"

    ids = _get(ESEARCH, {"db": "pubmed", "term": query, "retmode": "json", "retmax": 200}).json()["esearchresult"]["idlist"]
    if not ids:
        return pd.DataFrame()

    summ = _get(ESUMMARY, {"db": "pubmed", "id": ",".join(ids), "retmode": "json"}).json()["result"]
    rows = []
    for k, v in summ.items():
        if k == "uids":
            continue
        rows.append({
            "source": "PubMed",
            "pmid": v.get("uid"),
            "title": v.get("title"),
            "journal": v.get("fulljournalname"),
            "pubdate": v.get("pubdate"),
            "authors": "; ".join([a.get("name", "") for a in v.get("authors", [])]),
            "doi": next((i["identifier"] for i in v.get("articleids", []) if i.get("idtype") == "doi"), ""),
            "url": f"https://pubmed.ncbi.nlm.nih.gov/{v.get('uid')}/",
            "ingested_at": ts_utc(),
        })

    df = pd.DataFrame(rows)
    if not df.empty:
        save_csv_dedup(df, "pubmed_papers", "pmid")
    return df
