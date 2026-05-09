# biotech-intel

> **Status:** Dormant — cron disabled. Run manually via `workflow_dispatch` to demo.
> This project is a predecessor to [BLKPHXLABS.AI_BRIEFING](../BLKPHXLABS.AI_BRIEFING).

Automated daily intelligence pipeline for biotech operator-investors. Aggregates regulatory filings, clinical trial updates, SEC disclosures, and peer-reviewed literature from five public APIs, then generates a structured briefing via Gemini — delivered as Markdown, HTML, and PDF on every push to `main`.

---

## Table of contents

1. [Project overview](#project-overview)
2. [What it does](#what-it-does)
3. [Data sources](#data-sources)
4. [Architecture](#architecture)
5. [Project structure](#project-structure)
6. [Setup](#setup)
7. [GitHub Actions setup](#github-actions-setup)
8. [Output format](#output-format)
9. [Reliability](#reliability)
10. [Test suite](#test-suite)
11. [Extending the pipeline](#extending-the-pipeline)

---

## Project overview

biotech-intel was built to answer a specific question that comes up in biotech operations and investment work: *what happened today across the regulatory, clinical, financial, and scientific dimensions of the companies I'm watching?*

Traditional approaches to this require either expensive data subscriptions (Bloomberg, Evaluate Pharma) or hours of manual scanning across FDA.gov, ClinicalTrials.gov, SEC EDGAR, PubMed, and bioRxiv. This pipeline replaces that manual process with a fully automated system that runs daily, requires no maintenance once configured, and produces a single consolidated briefing.

The system is designed around five principles:

**Cross-domain coverage.** No single API tells the full story of a biotech company. A trial update on ClinicalTrials, a BLA approval on FDA, a material event 8-K on SEC, and a mechanism-of-action preprint on bioRxiv are all pieces of the same picture. The pipeline treats them as one dataset.

**Operator-grade reliability.** Each HTTP call retries on failure, each source runs independently so one outage doesn't kill the run, and every write deduplicates against prior runs so the CSVs don't grow unbounded over time.

**Zero-maintenance configuration.** Changing what companies or topics to track requires editing a plain text file — no code changes, no redeployment. SEC CIK numbers are resolved dynamically so any publicly listed ticker works automatically.

**LLM-augmented synthesis.** Raw API data is useful but noisy. The Gemini pass distills each day's records into a structured narrative organized by significance: Approvals, Trials, Filings, Papers, Preprints, Watchlist Risks, Action Items.

**Verifiable behavior.** A 25-test suite covers every collector and the core data utilities. Tests run in CI before every pipeline execution, so a broken parser is caught before it silently produces empty CSVs.

---

## What it does

Each day at 06:15 UTC, GitHub Actions runs two sequential workflows:

1. **Pipeline** — pulls fresh data from five sources, deduplicates against prior runs, and commits updated CSVs
2. **Insights** — reads those CSVs, runs a rule-based summary and a Gemini LLM summary, renders them into an HTML report, converts to PDF, and commits

The result is a `docs/daily_brief.pdf` that reads like a one-page operator briefing — new drug approvals, active trial updates for tracked sponsors, SEC filings for watched tickers, and the latest literature on configured keywords.

---

## Data sources

| Source | API | What's collected | Output file |
|---|---|---|---|
| FDA CDER | openFDA `drug/drugsfda` | BLA/NDA approvals — product, sponsor, date | `output/fda_approvals.csv` |
| ClinicalTrials.gov | v2 REST API | Active trials for configured sponsors — phase, status, interventions | `output/clinical_trials.csv` |
| SEC EDGAR | `data.sec.gov/submissions` | 8-K, 10-Q, 10-K filings for configured tickers | `output/sec_filings.csv` |
| PubMed | NCBI E-utilities | Abstracts matching configured keywords | `output/pubmed_papers.csv` |
| bioRxiv | bioRxiv REST API | Preprints matching configured keywords | `output/biorxiv_preprints.csv` |

All five CSVs are mirrored to `docs/` for GitHub Pages.

---

## Architecture

```
config/
  keywords.txt  ──► biorxiv.py        ──► biorxiv_preprints.csv ─┐
  keywords.txt  ──► pubmed.py         ──► pubmed_papers.csv      ─┤
  sponsors.txt  ──► clinicaltrials.py ──► clinical_trials.csv    ─┼──► insights_rules.py ──► summary.md
  tickers.txt   ──► sec_edgar.py      ──► sec_filings.csv        ─┤    insights_llm.py   ──► summary_llm.md
                    fda_cder.py        ──► fda_approvals.csv      ─┘    build_report.py   ──► daily_brief.html/pdf
```

`src/main.py` runs all five collectors in sequence; each failure is isolated so a single bad source does not abort the run. A combined `output/biotech_events.csv` is written at the end.

---

## Project structure

```
biotech-intel/
├── .github/workflows/
│   ├── pipeline.yml        # daily data collection (cron + workflow_dispatch)
│   └── insights.yml        # LLM briefing, triggered on pipeline success
├── config/
│   ├── keywords.txt        # bioRxiv + PubMed search terms (one per line)
│   ├── sponsors.txt        # ClinicalTrials sponsor names (one per line)
│   └── tickers.txt         # SEC EDGAR tickers (one per line)
├── src/
│   ├── main.py             # entry point — runs all collectors
│   ├── common.py           # shared utilities: save_csv_dedup, backoff, stable_hash
│   ├── biorxiv.py          # bioRxiv collector
│   ├── pubmed.py           # PubMed collector (esearch + esummary)
│   ├── clinicaltrials.py   # ClinicalTrials v2 collector with pagination
│   ├── fda_cder.py         # openFDA drug approvals collector
│   ├── sec_edgar.py        # SEC EDGAR filings collector (dynamic CIK resolution)
│   ├── insights_rules.py   # rule-based summary → docs/summary.md
│   ├── insights_llm.py     # Gemini summary → docs/summary_llm.md
│   └── build_report.py     # HTML report builder → docs/daily_brief.html
├── tests/
│   ├── conftest.py         # shared pytest fixtures
│   ├── test_common.py      # unit tests for data utilities
│   └── test_collectors.py  # integration tests for all five collectors
├── output/                 # CSVs written by collectors (committed by CI)
├── docs/                   # Mirrored CSVs + HTML/PDF report (GitHub Pages root)
└── requirements.txt
```

---

## Setup

### Prerequisites

- Python 3.11+
- A [Google AI Studio](https://aistudio.google.com/) API key (free tier is sufficient)

### Install dependencies

```bash
pip install -r requirements.txt
```

### Configure tracking targets

Edit the three config files — one entry per line, no quotes:

**`config/keywords.txt`** — drives bioRxiv and PubMed searches
```
bioprinting
regenerative medicine
CRISPR
cell therapy
```

**`config/sponsors.txt`** — drives ClinicalTrials sponsor filter (must match `LeadSponsorName` exactly)
```
Novartis
Bristol-Myers Squibb
Bluebird Bio
Beam Therapeutics
CRISPR Therapeutics
```

**`config/tickers.txt`** — drives SEC EDGAR filing pulls (any publicly listed ticker)
```
VRTX
REGN
CRSP
BLUE
BEAM
```

### Run locally

```bash
# Collect data (writes to output/ and docs/)
python -m src.main

# Generate rule-based summary
python -m src.insights_rules

# Generate LLM summary (requires GEMINI_API_KEY in environment)
GEMINI_API_KEY=<your-key> python -m src.insights_llm

# Build HTML report
python src/build_report.py
```

The briefing is written to `docs/daily_brief.html`. Convert to PDF locally with `wkhtmltopdf docs/daily_brief.html docs/daily_brief.pdf`.

### Run tests

```bash
python -m pytest tests/ -v
```

---

## GitHub Actions setup

The pipeline runs automatically once secrets are configured.

### Required secrets

In the repo: **Settings → Secrets and variables → Actions → New repository secret**

| Name | Value |
|---|---|
| `GEMINI_API_KEY` | Your Google AI Studio API key |
| `SEC_USER_AGENT` | Contact email for SEC EDGAR (required by their ToS — e.g. `yourname@example.com`) |

### Workflow schedule

| Workflow | Trigger | What it does |
|---|---|---|
| `pipeline.yml` | Daily 06:15 UTC + `workflow_dispatch` | Runs tests, then all collectors; commits updated CSVs |
| `insights.yml` | On `pipeline.yml` success + `workflow_dispatch` | Runs rule + LLM summaries; commits HTML/PDF report |

Trigger either workflow manually from **Actions → Run workflow** for an out-of-cycle refresh.

---

## Output format

### CSVs

Each source writes a deduplicated CSV with a stable ID column. Re-running the pipeline does not duplicate rows — new records are appended and existing records (matched on the ID) are preserved.

| File | ID column | Key fields |
|---|---|---|
| `fda_approvals.csv` | `accession` (hashed) | company, product, approval_date, route |
| `clinical_trials.csv` | `nct_id` | sponsor, phase, status, condition, intervention |
| `sec_filings.csv` | `accession` | ticker, form (8-K/10-Q/10-K), filed_at |
| `pubmed_papers.csv` | `pmid` | title, journal, pubdate, authors, doi |
| `biorxiv_preprints.csv` | `doi` | title, authors, category, date |

### Daily brief

`docs/daily_brief.html` (and `.pdf`) contains:
- **Rule-based summary** — top 5 most recent events per source, formatted as bullet points
- **LLM summary** — Gemini-generated narrative with sections: Approvals, Trials, Filings, Papers, Preprints, Watchlist Risks, Action Items
- **Data tables** — latest 15 rows from each source CSV

---

## Reliability

- **Retry logic** — every HTTP request retries up to 3 times with exponential backoff (1s, 2s, 4s) on any `requests.RequestException`
- **Source isolation** — a failure in one collector logs the error and continues; the other four sources still run
- **Dynamic CIK resolution** — SEC tickers are resolved against the full SEC company list at runtime, so any publicly listed ticker in `tickers.txt` works without code changes
- **ClinicalTrials pagination** — the v2 API returns up to 100 records per page; the collector follows `nextPageToken` until all results for each sponsor are retrieved

---

## Test suite

### Philosophy

The tests exist to answer one question: *does the code behave correctly regardless of what the external APIs return?* They do not test whether the APIs are up, whether the data they return is scientifically accurate, or whether Gemini's summary is good. Those are operational concerns, not code correctness concerns.

This distinction matters because the pipeline runs unattended every day. If a collector silently starts returning empty DataFrames due to an API schema change, the LLM briefing will produce nothing — and without tests, that failure is invisible until someone notices the report is blank. The tests make that failure loud and immediate.

### Structure

```
tests/
├── conftest.py         # shared fixtures available to all test files
├── test_common.py      # unit tests — one function, no dependencies
└── test_collectors.py  # integration tests — full run() with mocked HTTP
```

**`conftest.py`** defines fixtures: reusable setup and teardown logic that pytest injects into tests automatically. The key fixture here is `patch_output_dirs`, which redirects all CSV writes to a throwaway temp directory so tests never modify `output/` or `docs/`. It is restored automatically when each test ends.

**`test_common.py`** contains unit tests — tests that exercise one function in complete isolation with no network calls and no file I/O beyond what the test itself controls. These are the fastest tests and the most fundamental: if `save_csv_dedup` doesn't actually deduplicate, or `stable_hash` isn't deterministic, everything built on top of them is broken.

**`test_collectors.py`** contains integration tests — tests that exercise a full `run()` function but replace the HTTP boundary with controlled fake responses using `unittest.mock.patch`. This means each test defines exactly what the API returns and verifies that the collector parses it correctly.

### How mocking works

Every collector calls `requests.get()` internally. In tests, that call is intercepted:

```python
with patch("src.biorxiv.requests.get", return_value=make_response(BIORXIV_PAYLOAD)):
    df = biorxiv.run()
```

`patch("src.biorxiv.requests.get")` replaces `requests.get` *as it exists inside `biorxiv.py`* for the duration of the `with` block. The collector runs its full logic — parsing, field mapping, deduplication — but never touches the network. The rule is: mock where the call happens, not where the function is defined.

For PubMed, which makes two sequential requests (an ID search then a metadata fetch), `side_effect` is used to return a different response on each call:

```python
with patch("src.pubmed.requests.get", side_effect=[esearch_response, esummary_response]):
```

For SEC EDGAR, `_get_cik_map()` is decorated with `@lru_cache`, meaning it caches its result after the first call. Rather than fight the cache, the SEC tests mock `_get_cik_map` directly so `run()` sees a controlled CIK map without touching the network at all.

### What each test group determines

**`test_common.py` — data integrity guarantees**

| Test | What it determines |
|---|---|
| `test_stable_hash_same_input_gives_same_output` | FDA's synthetic accession key will match across runs — dedup will recognize the same approval tomorrow |
| `test_stable_hash_different_inputs_give_different_outputs` | Two different approvals won't hash to the same key and silently merge into one row |
| `test_stable_hash_returns_12_chars` | The hash length is fixed — no padding or truncation surprises in the CSV |
| `test_read_lines_returns_non_empty_lines` | Blank lines in config files are filtered; an accidental empty line won't generate an empty API query |
| `test_read_lines_strips_whitespace` | Leading/trailing spaces in config files don't create mismatched sponsor names |
| `test_save_csv_dedup_creates_file_on_first_write` | The output file is created on the first run, not just on the second |
| `test_save_csv_dedup_does_not_grow_on_duplicate_id` | Running the pipeline twice on the same day does not double the row count |
| `test_save_csv_dedup_appends_new_id` | A genuinely new record is added; dedup doesn't accidentally swallow novel data |
| `test_save_csv_dedup_mirrors_to_docs` | Every CSV write reaches `docs/` for GitHub Pages — the briefing always has current data |

**`test_collectors.py` — parser correctness and edge-case handling**

| Test | What it determines |
|---|---|
| `test_*_returns_correct_columns` | The DataFrame schema matches what downstream code (`insights_rules.py`, `build_report.py`) expects — a missing column here silently produces blank report sections |
| `test_*_*_matches_payload` | The field is being read from the right location in the API response — catches field-mapping regressions after API schema changes |
| `test_*_empty_*_returns_empty_df` | A source returning zero results doesn't crash the pipeline; `main.py`'s isolation logic only works if collectors return an empty DataFrame rather than raising |
| `test_fda_accession_is_stable_across_runs` | The synthetic key derived from `application_number + approval_date` is identical across two separate calls — if it weren't, the same FDA approval would appear as a new row every day |
| `test_sec_edgar_filters_out_non_financial_forms` | S-1 and other non-intelligence filings are excluded; the filter logic is correct |
| `test_sec_edgar_unknown_ticker_produces_empty_df` | An unrecognized ticker is skipped cleanly, not raised as an exception that kills the whole SEC run |

### Validity and limitations

The tests verify **code correctness** — that each module parses its input and produces output with the right shape and values. They do not and cannot verify:

- **API availability** — whether the real endpoints are reachable on any given day
- **Data quality** — whether ClinicalTrials.gov is returning accurate trial status or whether a PubMed record has complete author metadata
- **LLM output** — whether Gemini's synthesis is accurate, unbiased, or complete; the `insights_llm.py` module is excluded from the test suite because LLM outputs are non-deterministic
- **Schema drift** — if an API changes its response structure (e.g., ClinicalTrials moved from v1 to v2 in 2023), the mocked tests will still pass because they test against a hardcoded payload, not the live API

The practical implication: when a collector starts producing empty CSVs in production despite passing tests, the most likely cause is API schema drift. The fix is to update the mock payload in the test to match the new structure, then update the parser to match.

### Running the tests

```bash
# Run all 25 tests
python -m pytest tests/ -v

# Run only the unit tests
python -m pytest tests/test_common.py -v

# Run only one collector's tests
python -m pytest tests/test_collectors.py -k "fda" -v

# Stop on first failure
python -m pytest tests/ -x
```

Tests run in CI automatically before every pipeline execution. If any test fails, the data collection step is skipped.

---

## Portfolio context

This project was built to aggregate signal across the regulatory, clinical, financial, and scientific dimensions of the biotech space — a problem that otherwise requires either expensive subscriptions or hours of manual scanning.

**Lineage:**

| Project | What it proved |
|---|---|
| `email-digest-scheduler` | Email collection → LLM synthesis → structured digest delivery |
| `biotech-intel` (this) | Structured public API aggregation across five domains → daily briefing with deduplication and CI |
| `BLKPHXLABS.AI_BRIEFING` | Production-grade unification: GCP serverless deployment, three-pass RAG, TTS, video render |

Each project builds on the patterns validated by the previous one. `biotech-intel` specifically proved out multi-source API deduplication, retry reliability, and chained CI workflows — all of which are core to BLKPHXLABS.AI_BRIEFING's architecture.

---

## Extending the pipeline

**Add a new keyword** — append a line to `config/keywords.txt`. bioRxiv and PubMed will pick it up on the next run.

**Track a new sponsor** — append the exact `LeadSponsorName` string to `config/sponsors.txt`.

**Track a new ticker** — append the ticker symbol to `config/tickers.txt`. CIK resolution is automatic.

**Add a new source** — create `src/mysource.py` with a `run() -> pd.DataFrame` function following the same pattern as the existing collectors, then add it to the import list in `src/main.py`. Add a corresponding test in `tests/test_collectors.py` with a mock payload and column assertion before merging.
