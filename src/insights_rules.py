import pandas as pd
from pathlib import Path
OUT = Path("output"); DOCS = Path("docs"); DOCS.mkdir(exist_ok=True, parents=True)

def load(path):
    p = OUT / path
    return pd.read_csv(p) if p.exists() else pd.DataFrame()

def top_events():
    fda = load("fda_approvals.csv")
    sec = load("sec_filings.csv")
    trl = load("clinical_trials.csv")
    pm  = load("pubmed_papers.csv")
    bx  = load("biorxiv_preprints.csv")

    lines = []
    if not fda.empty:
        recent = fda.sort_values("approval_date", ascending=False).head(5)
        for _,r in recent.iterrows():
            lines.append(f"FDA approval: {r.get('product','?')} ({r.get('company','?')}) on {r.get('approval_date','?')} — {r.get('url','')}")
    if not sec.empty:
        recent = sec.sort_values("filed_at", ascending=False).head(5)
        for _,r in recent.iterrows():
            lines.append(f"SEC {r.get('form','?')} filed by {r.get('ticker','?')} on {r.get('filed_at','?')} — {r.get('url','')}")
    if not trl.empty:
        recent = trl.sort_values("last_update", ascending=False).head(5)
        for _,r in recent.iterrows():
            lines.append(f"Trial update: {r.get('nct_id','?')} {r.get('phase','')} {r.get('status','')} — {r.get('title','')}")
    if not pm.empty:
        recent = pm.sort_values("pubdate", ascending=False).head(5)
        for _,r in recent.iterrows():
            lines.append(f"PubMed: {r.get('title','?')} — {r.get('url','')}")
    if not bx.empty:
        recent = bx.sort_values("date", ascending=False).head(5)
        for _,r in recent.iterrows():
            lines.append(f"bioRxiv: {r.get('title','?')} — {r.get('url','')}")
    return lines

def write_markdown():
    items = top_events()
    md = ["# Biotech Daily Brief", ""]
    if items:
        md += [f"- {x}" for x in items]
    else:
        md.append("_No new items._")
    (DOCS / "summary.md").write_text("\n".join(md), encoding="utf-8")

if __name__ == "__main__":
    write_markdown()
