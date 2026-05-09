"""
test_collectors.py — integration tests for the five data-collection modules.

"Integration test" means we test the full run() function of each module,
but we mock (fake) the HTTP layer so no real network calls are made.

Key tools used here:
  - unittest.mock.patch: temporarily replaces any object in any module for
    the duration of one test. patch("src.biorxiv.requests.get") replaces
    requests.get *as imported inside biorxiv.py* — that's the boundary we
    control. Rule: mock where the call happens, not where it's defined.
  - side_effect=[r1, r2]: when a function is called multiple times, return a
    different mock each time. Used for PubMed's two-request flow.
  - monkeypatch.setattr: swap out read_lines so tests don't depend on real
    config files on disk.
"""

from unittest.mock import patch, MagicMock
import pandas as pd
import pytest

import src.biorxiv as biorxiv
import src.pubmed as pubmed
import src.clinicaltrials as clinicaltrials
import src.fda_cder as fda_cder
import src.sec_edgar as sec_edgar


def make_response(json_data):
    """
    Build a fake requests.Response that returns json_data from .json()
    and does nothing on .raise_for_status().
    """
    mock = MagicMock()
    mock.json.return_value = json_data
    mock.raise_for_status = MagicMock()
    return mock


# ── bioRxiv ───────────────────────────────────────────────────────────────────

BIORXIV_PAYLOAD = {
    "collection": [
        {
            "doi": "10.1101/2024.01.01.000001",
            "title": "CRISPR base editing corrects sickle cell mutation",
            "authors": "Smith J; Lee K",
            "category": "cell biology",
            "date": "2024-01-15",
            "version": "1",
        }
    ]
}


def test_biorxiv_returns_correct_columns(patch_output_dirs, monkeypatch):
    monkeypatch.setattr("src.biorxiv.read_lines", lambda _: ["CRISPR"])
    with patch("src.biorxiv.requests.get", return_value=make_response(BIORXIV_PAYLOAD)):
        df = biorxiv.run()

    assert not df.empty
    assert {"doi", "title", "authors", "date", "url", "source"}.issubset(df.columns)


def test_biorxiv_doi_matches_payload(patch_output_dirs, monkeypatch):
    monkeypatch.setattr("src.biorxiv.read_lines", lambda _: ["CRISPR"])
    with patch("src.biorxiv.requests.get", return_value=make_response(BIORXIV_PAYLOAD)):
        df = biorxiv.run()

    assert df.iloc[0]["doi"] == "10.1101/2024.01.01.000001"


def test_biorxiv_empty_collection_returns_empty_df(patch_output_dirs, monkeypatch):
    """Graceful handling: zero results from API should not crash the pipeline."""
    monkeypatch.setattr("src.biorxiv.read_lines", lambda _: ["CRISPR"])
    with patch("src.biorxiv.requests.get", return_value=make_response({"collection": []})):
        df = biorxiv.run()

    assert df.empty


# ── PubMed ────────────────────────────────────────────────────────────────────

ESEARCH_PAYLOAD = {"esearchresult": {"idlist": ["38000001"]}}
ESUMMARY_PAYLOAD = {
    "result": {
        "uids": ["38000001"],
        "38000001": {
            "uid": "38000001",
            "title": "CAR-T cell therapy in relapsed B-cell lymphoma",
            "fulljournalname": "Nature Medicine",
            "pubdate": "2024 Jan",
            "authors": [{"name": "Jones A"}, {"name": "Patel B"}],
            "articleids": [{"idtype": "doi", "identifier": "10.1038/nm.test"}],
        },
    }
}


def test_pubmed_returns_correct_columns(patch_output_dirs, monkeypatch):
    monkeypatch.setattr("src.pubmed.read_lines", lambda _: ["cell therapy"])
    with patch("src.pubmed.requests.get", side_effect=[
        make_response(ESEARCH_PAYLOAD),
        make_response(ESUMMARY_PAYLOAD),
    ]):
        df = pubmed.run()

    assert not df.empty
    assert {"pmid", "title", "journal", "pubdate", "authors", "doi", "url"}.issubset(df.columns)


def test_pubmed_pmid_matches_payload(patch_output_dirs, monkeypatch):
    monkeypatch.setattr("src.pubmed.read_lines", lambda _: ["cell therapy"])
    with patch("src.pubmed.requests.get", side_effect=[
        make_response(ESEARCH_PAYLOAD),
        make_response(ESUMMARY_PAYLOAD),
    ]):
        df = pubmed.run()

    assert df.iloc[0]["pmid"] == "38000001"


def test_pubmed_empty_search_returns_empty_df(patch_output_dirs, monkeypatch):
    """If esearch returns no IDs, run() should return early without calling esummary."""
    monkeypatch.setattr("src.pubmed.read_lines", lambda _: ["cell therapy"])
    with patch("src.pubmed.requests.get", return_value=make_response(
        {"esearchresult": {"idlist": []}}
    )):
        df = pubmed.run()

    assert df.empty


# ── ClinicalTrials ────────────────────────────────────────────────────────────

CT_PAYLOAD = {
    "studies": [
        {
            "protocolSection": {
                "identificationModule": {
                    "nctId": "NCT12345678",
                    "briefTitle": "Phase 2 CRISPR Editing Trial in Sickle Cell",
                },
                "conditionsModule": {"conditions": ["Sickle Cell Disease"]},
                "armsInterventionsModule": {"interventions": [{"name": "CTX001"}]},
                "designModule": {"phases": ["Phase 2"]},
                "statusModule": {
                    "overallStatus": "Recruiting",
                    "startDateStruct": {"date": "2023-06-01"},
                    "lastUpdatePostDateStruct": {"date": "2024-01-10"},
                },
                "sponsorCollaboratorsModule": {"leadSponsor": {"name": "CRISPR Therapeutics"}},
            }
        }
    ]
    # no nextPageToken key → single page, loop exits after one fetch
}


def test_clinicaltrials_returns_correct_columns(patch_output_dirs, monkeypatch):
    monkeypatch.setattr("src.clinicaltrials.read_lines", lambda _: ["CRISPR Therapeutics"])
    with patch("src.clinicaltrials.requests.get", return_value=make_response(CT_PAYLOAD)):
        df = clinicaltrials.run()

    assert not df.empty
    assert {"nct_id", "title", "phase", "status", "sponsor", "condition", "url"}.issubset(df.columns)


def test_clinicaltrials_nct_id_matches_payload(patch_output_dirs, monkeypatch):
    monkeypatch.setattr("src.clinicaltrials.read_lines", lambda _: ["CRISPR Therapeutics"])
    with patch("src.clinicaltrials.requests.get", return_value=make_response(CT_PAYLOAD)):
        df = clinicaltrials.run()

    assert df.iloc[0]["nct_id"] == "NCT12345678"


def test_clinicaltrials_empty_studies_returns_empty_df(patch_output_dirs, monkeypatch):
    monkeypatch.setattr("src.clinicaltrials.read_lines", lambda _: ["Novartis"])
    with patch("src.clinicaltrials.requests.get", return_value=make_response({"studies": []})):
        df = clinicaltrials.run()

    assert df.empty


# ── FDA CDER ──────────────────────────────────────────────────────────────────

FDA_PAYLOAD = {
    "results": [
        {
            "application_number": "BLA761174",
            "sponsor_name": "bluebird bio, Inc.",
            "products": [
                {
                    "brand_name": "Zynteglo",
                    "dosage_form": "SUSPENSION",
                    "route": "INTRAVENOUS",
                    "approval_dates": [{"approval_date": "20220816"}],
                }
            ],
        }
    ]
}


def test_fda_returns_correct_columns(patch_output_dirs):
    with patch("src.fda_cder.requests.get", return_value=make_response(FDA_PAYLOAD)):
        df = fda_cder.run()

    assert not df.empty
    assert {"accession", "company", "application", "product", "approval_date", "url"}.issubset(df.columns)


def test_fda_application_number_matches_payload(patch_output_dirs):
    with patch("src.fda_cder.requests.get", return_value=make_response(FDA_PAYLOAD)):
        df = fda_cder.run()

    assert df.iloc[0]["application"] == "BLA761174"


def test_fda_accession_is_stable_across_runs(patch_output_dirs):
    """
    The synthetic accession is a hash of application_number + approval_date.
    Two runs on the same payload must produce the same hash, otherwise
    save_csv_dedup() treats the same approval as a new record every day.
    """
    with patch("src.fda_cder.requests.get", return_value=make_response(FDA_PAYLOAD)):
        df1 = fda_cder.run()
    with patch("src.fda_cder.requests.get", return_value=make_response(FDA_PAYLOAD)):
        df2 = fda_cder.run()

    assert df1.iloc[0]["accession"] == df2.iloc[0]["accession"]


def test_fda_empty_results_returns_empty_df(patch_output_dirs):
    with patch("src.fda_cder.requests.get", return_value=make_response({"results": []})):
        df = fda_cder.run()

    assert df.empty


# ── SEC EDGAR ─────────────────────────────────────────────────────────────────
#
# _get_cik_map() is decorated with @lru_cache, which means it stores its
# return value after the first call and never calls requests.get again.
# We bypass this by patching _get_cik_map itself (not requests.get inside it),
# so run() sees a controlled CIK map without touching the cache at all.

SUBMISSIONS_PAYLOAD = {
    "filings": {
        "recent": {
            "form": ["10-K", "8-K", "S-1"],
            "filingDate": ["2024-01-15", "2024-02-01", "2023-11-01"],
            "accessionNumber": [
                "0000875320-24-000001",
                "0000875320-24-000002",
                "0000875320-23-000001",
            ],
        }
    }
}


def test_sec_edgar_returns_correct_columns(patch_output_dirs, monkeypatch):
    monkeypatch.setattr("src.sec_edgar.read_lines", lambda _: ["VRTX"])
    with patch("src.sec_edgar._get_cik_map", return_value={"VRTX": "0000875320"}):
        with patch("src.sec_edgar.requests.get", return_value=make_response(SUBMISSIONS_PAYLOAD)):
            df = sec_edgar.run()

    assert not df.empty
    assert {"ticker", "form", "filed_at", "accession", "url", "source"}.issubset(df.columns)


def test_sec_edgar_filters_out_non_financial_forms(patch_output_dirs, monkeypatch):
    """
    S-1 (registration statement) is in the payload but must be excluded.
    Only 8-K, 10-Q, and 10-K are relevant for our intelligence use case.
    """
    monkeypatch.setattr("src.sec_edgar.read_lines", lambda _: ["VRTX"])
    with patch("src.sec_edgar._get_cik_map", return_value={"VRTX": "0000875320"}):
        with patch("src.sec_edgar.requests.get", return_value=make_response(SUBMISSIONS_PAYLOAD)):
            df = sec_edgar.run()

    assert set(df["form"].unique()).issubset({"8-K", "10-Q", "10-K"})
    assert "S-1" not in df["form"].values


def test_sec_edgar_unknown_ticker_produces_empty_df(patch_output_dirs, monkeypatch):
    """A ticker absent from the CIK map is skipped silently — no crash, no rows."""
    monkeypatch.setattr("src.sec_edgar.read_lines", lambda _: ["UNKNOWN"])
    with patch("src.sec_edgar._get_cik_map", return_value={"VRTX": "0000875320"}):
        df = sec_edgar.run()

    assert df.empty
