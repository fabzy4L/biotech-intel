import pandas as pd, pathlib, datetime, html
DOCS = pathlib.Path("docs"); OUT = pathlib.Path("output")
DOCS.mkdir(parents=True, exist_ok=True)

def read_md(p):
    return pathlib.Path(p).read_text(encoding="utf-8") if pathlib.Path(p).exists() else ""

def table_csv(name, n=15):
    p = OUT / f"{name}.csv"
    if not p.exists(): return ""
    df = pd.read_csv(p).tail(n)
    return df.to_html(index=False, escape=False)

def main():
    now = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    parts = []
    parts.append(f"<h1>Biotech Daily Brief</h1><p><em>{now}</em></p>")
    # summaries
    sm = read_md("docs/summary.md")
    sl = read_md("docs/summary_llm.md")
    if sm: parts.append(f"<h2>Rule-based Summary</h2>\n{html.escape(sm).replace('\\n','<br>')}")
    if sl: parts.append(f"<h2>LLM Summary</h2>\n{html.escape(sl).replace('\\n','<br>')}")
    # key tables
    parts.append("<h2>Key Tables (latest 15)</h2>")
    parts.append("<h3>FDA Approvals</h3>"+table_csv("fda_approvals"))
    parts.append("<h3>ClinicalTrials</h3>"+table_csv("clinical_trials"))
    parts.append("<h3>SEC Filings</h3>"+table_csv("sec_filings"))
    parts.append("<h3>PubMed</h3>"+table_csv("pubmed_papers"))
    parts.append("<h3>bioRxiv</h3>"+table_csv("biorxiv_preprints"))
    html_doc = "<html><head><meta charset='utf-8'><style>body{font-family:sans-serif} table{border-collapse:collapse;width:100%} th,td{border:1px solid #ddd;padding:6px;font-size:12px} h1,h2,h3{margin-top:18px}</style></head><body>"+ "".join(parts) + "</body></html>"
    (DOCS/"daily_brief.html").write_text(html_doc, encoding="utf-8")

if __name__ == "__main__":
    main()
