import os, json, pandas as pd
from pathlib import Path
from datetime import datetime, timezone

DOCS = Path("docs"); DOCS.mkdir(exist_ok=True, parents=True)

def load_csvs():
    base = Path("output")
    data = {}
    for name in ["fda_approvals","clinical_trials","pubmed_papers","biorxiv_preprints","sec_filings"]:
        p = base / f"{name}.csv"
        data[name] = pd.read_csv(p).to_dict(orient="records") if p.exists() else []
    return data

SYSTEM = "Summarize biotech events for an operator-investor. Output: sections: Approvals, Trials, Filings, Papers, Preprints, Watchlist Risks, Action Items. Be concise and specific."

def call_openai(prompt: str) -> str:
    from openai import OpenAI
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role":"system","content":SYSTEM},{"role":"user","content":prompt}],
        temperature=0.2,
        max_tokens=800
    )
    return resp.choices[0].message.content

def run_llm_summary():
    data = load_csvs()
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "counts": {k: len(v) for k,v in data.items()},
        "samples": {k: v[:30] for k,v in data.items()}  # cap tokens
    }
    prompt = "Summarize the following JSON:\n" + json.dumps(payload, ensure_ascii=False)
    md = call_openai(prompt)
    (DOCS / "summary_llm.md").write_text(md, encoding="utf-8")

if __name__ == "__main__":
    run_llm_summary()
