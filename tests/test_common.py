"""
test_common.py — unit tests for src/common.py

"Unit test" means we test one function in isolation, with no network calls
and no dependency on other modules. These are the fastest tests in the suite
and should always run first.

Pattern: Arrange → Act → Assert
  Arrange: set up any data the function needs
  Act:     call the function
  Assert:  check the result with assert
"""

import pandas as pd
import pytest

from src.common import stable_hash, read_lines, save_csv_dedup


# ── stable_hash ───────────────────────────────────────────────────────────────

def test_stable_hash_same_input_gives_same_output():
    """Hashing is deterministic — the same string always produces the same hash."""
    assert stable_hash("BLA761174|20220816") == stable_hash("BLA761174|20220816")


def test_stable_hash_different_inputs_give_different_outputs():
    """Different strings must not collide — otherwise dedup would silently merge rows."""
    assert stable_hash("BLA761174|20220816") != stable_hash("NDA213969|20210601")


def test_stable_hash_returns_12_chars():
    """The hash is truncated to 12 hex characters (defined in common.py)."""
    assert len(stable_hash("anything")) == 12


# ── read_lines ────────────────────────────────────────────────────────────────

def test_read_lines_returns_non_empty_lines(tmp_path):
    """
    tmp_path is a pytest built-in fixture that gives each test its own
    temporary directory. We write a file there and read it back.
    """
    config = tmp_path / "keywords.txt"
    config.write_text("CRISPR\n\n  \ncell therapy\n", encoding="utf-8")

    result = read_lines(str(config))

    assert result == ["CRISPR", "cell therapy"]


def test_read_lines_strips_whitespace(tmp_path):
    config = tmp_path / "sponsors.txt"
    config.write_text("  Novartis  \n  Beam Therapeutics  \n", encoding="utf-8")

    result = read_lines(str(config))

    assert result == ["Novartis", "Beam Therapeutics"]


# ── save_csv_dedup ────────────────────────────────────────────────────────────
#
# These tests use the patch_output_dirs fixture from conftest.py.
# That fixture redirects OUT and DOCS to a temp folder so we don't write
# real files during testing.

def test_save_csv_dedup_creates_file_on_first_write(patch_output_dirs):
    out_dir, _ = patch_output_dirs
    df = pd.DataFrame([{"nct_id": "NCT001", "title": "First trial"}])

    save_csv_dedup(df, "clinical_trials", "nct_id")

    assert (out_dir / "clinical_trials.csv").exists()


def test_save_csv_dedup_does_not_grow_on_duplicate_id(patch_output_dirs):
    """
    The core dedup guarantee: writing the same record twice should not add a row.
    This is the test that proves the daily runs won't produce unbounded CSVs.
    """
    out_dir, _ = patch_output_dirs
    df = pd.DataFrame([{"nct_id": "NCT001", "title": "First trial"}])

    save_csv_dedup(df, "clinical_trials", "nct_id")
    save_csv_dedup(df, "clinical_trials", "nct_id")  # exact same record again

    result = pd.read_csv(out_dir / "clinical_trials.csv")
    assert len(result) == 1


def test_save_csv_dedup_appends_new_id(patch_output_dirs):
    """A record with a new ID should be added, bringing the total to 2."""
    out_dir, _ = patch_output_dirs

    save_csv_dedup(
        pd.DataFrame([{"nct_id": "NCT001", "title": "First trial"}]),
        "clinical_trials", "nct_id",
    )
    save_csv_dedup(
        pd.DataFrame([{"nct_id": "NCT002", "title": "Second trial"}]),
        "clinical_trials", "nct_id",
    )

    result = pd.read_csv(out_dir / "clinical_trials.csv")
    assert len(result) == 2
    assert set(result["nct_id"]) == {"NCT001", "NCT002"}


def test_save_csv_dedup_mirrors_to_docs(patch_output_dirs):
    """Every CSV write must also appear in docs/ for GitHub Pages."""
    out_dir, docs_dir = patch_output_dirs
    df = pd.DataFrame([{"doi": "10.1101/test", "title": "Preprint"}])

    save_csv_dedup(df, "biorxiv_preprints", "doi")

    assert (docs_dir / "biorxiv_preprints.csv").exists()
