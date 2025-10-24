import requests, pandas as pd
from urllib.parse import quote_plus
from .common import read_lines, ts_utc, save_csv

ESEARCH="https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
ESUMMARY="https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"

def run():
    kws = read_lines("config/keywords.txt")
    query = " OR ".join(kws) if kws else "bioprinting"
    ids = requests.get(ESEARCH, params={"db":"pubmed","term":query,"retmode":"json","retmax":200}, timeout=60).json()["esearchresult"]["idlist"]
    if not ids: return pd.DataFrame()
    summ = requests.get(ESUMMARY, params={"db":"pubmed","id":",".join(ids),"retmode":"json"}, timeout=60).json()["result"]
    rows=[]
    for k,v in summ.items():
        if k=="uids": continue
        rows.append({
            "source":"PubMed",
            "pmid": v.get("uid"),
            "title": v.get("title"),
            "journal": v.get("fulljournalname"),
            "pubdate": v.get("pubdate"),
            "authors": "; ".join([a.get("name","") for a in v.get("authors",[])]),
            "doi": next((i["identifier"] for i in v.get("articleids",[]) if i.get("idtype")=="doi"), ""),
            "url": f"https://pubmed.ncbi.nlm.nih.gov/{v.get('uid')}/",
            "ingested_at": ts_utc(),
        })
    df = pd.DataFrame(rows)
    if not df.empty:
        save_csv(df, "pubmed_papers")
    return df
