import os, requests, pandas as pd
from functools import lru_cache
from .common import read_lines, ts_utc, save_csv_dedup, backoff

BASE = "https://data.sec.gov/submissions/CIK{cik}.json"
CIK_MAP_URL = "https://www.sec.gov/files/company_tickers.json"
HEADERS = {"User-Agent": os.environ.get("SEC_USER_AGENT", "biotech-intel-bot contact@example.com")}

@lru_cache(maxsize=1)
def _get_cik_map():
    for attempt in range(3):
        try:
            r = requests.get(CIK_MAP_URL, headers=HEADERS, timeout=30)
            r.raise_for_status()
            return {v["ticker"].upper(): str(v["cik_str"]).zfill(10) for v in r.json().values()}
        except requests.RequestException:
            if attempt == 2:
                raise
            backoff(attempt)

def run():
    tickers = read_lines("config/tickers.txt")
    cik_map = _get_cik_map()
    rows = []

    for t in tickers:
        cik = cik_map.get(t.upper())
        if not cik:
            print(f"no CIK found for {t}")
            continue

        for attempt in range(3):
            try:
                r = requests.get(BASE.format(cik=cik), headers=HEADERS, timeout=60)
                r.raise_for_status()
                break
            except requests.RequestException:
                if attempt == 2:
                    raise
                backoff(attempt)

        filings = r.json().get("filings", {}).get("recent", {})
        for form, date, acc in zip(
            filings.get("form", []),
            filings.get("filingDate", []),
            filings.get("accessionNumber", []),
        ):
            if form in ("8-K", "10-Q", "10-K"):
                rows.append({
                    "source": "SEC",
                    "ticker": t.upper(),
                    "form": form,
                    "filed_at": date,
                    "accession": acc,
                    "url": f"https://www.sec.gov/ixviewer/doc?action=display&accno={acc.replace('-', '')}",
                    "ingested_at": ts_utc(),
                })

    df = pd.DataFrame(rows)
    if not df.empty:
        save_csv_dedup(df, "sec_filings", "accession")
    return df
