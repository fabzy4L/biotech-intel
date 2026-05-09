import time, json, hashlib, pandas as pd
from pathlib import Path
from datetime import datetime, timezone

OUT = Path("output")
DOCS = Path("docs")
OUT.mkdir(exist_ok=True, parents=True)
DOCS.mkdir(exist_ok=True, parents=True)

def ts_utc():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def save_csv(df: pd.DataFrame, name: str):
    df = df.sort_values(by=[c for c in df.columns if "date" in c.lower()] or df.columns.tolist())
    p = OUT / f"{name}.csv"
    df.to_csv(p, index=False)
    # mirror to docs for Pages
    df.to_csv(DOCS / f"{name}.csv", index=False)
    return p

def stable_hash(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()[:12]

def read_lines(path):
    return [x.strip() for x in Path(path).read_text(encoding="utf-8").splitlines() if x.strip()]

def backoff(attempt):
    time.sleep(min(60, 2 ** attempt))

def save_csv_dedup(df: pd.DataFrame, name: str, id_col: str):
    p = OUT / f"{name}.csv"
    if p.exists():
        existing = pd.read_csv(p)
        df = pd.concat([existing, df]).drop_duplicates(subset=[id_col]).reset_index(drop=True)
    df = df.sort_values(by=[c for c in df.columns if "date" in c.lower()] or df.columns.tolist())
    df.to_csv(p, index=False)
    df.to_csv(DOCS / f"{name}.csv", index=False)
    return p
