import requests, pandas as pd
from .common import read_lines, ts_utc, save_csv

BASE="https://data.sec.gov/submissions/CIK{cik}.json"
# Simple: map tickers → CIK via SEC's company-tickers JSON once, then static map here for MVP.
T2CIK = {
    "AMZN":"0001018724",
    "NVDA":"0001045810",
    "VRTX":"0000875320",
    "REGN":"0000872589"
}

HEADERS={"User-Agent":"research-contact@example.com"}  # replace with your email

def run():
    tickers = read_lines("config/tickers.txt")
    rows=[]
    for t in tickers:
        cik = T2CIK.get(t.upper())
        if not cik: continue
        r = requests.get(BASE.format(cik=cik.zfill(10)), headers=HEADERS, timeout=60)
        r.raise_for_status()
        filings = r.json().get("filings",{}).get("recent",{})
        for form, date, acc in zip(filings.get("form",[]), filings.get("filingDate",[]), filings.get("accessionNumber",[])):
            if form in ("8-K","10-Q","10-K"):
                rows.append({
                    "source":"SEC",
                    "ticker": t.upper(),
                    "form": form,
                    "filed_at": date,
                    "accession": acc,
                    "url": f"https://www.sec.gov/ixviewer/doc?action=display&accno={acc.replace('-','')}",
                    "ingested_at": ts_utc(),
                })
    df = pd.DataFrame(rows)
    if not df.empty:
        save_csv(df, "sec_filings")
    return df
