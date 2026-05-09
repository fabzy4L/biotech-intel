"""
conftest.py — shared setup that every test file can use automatically.

pytest loads this file before running any tests. Anything defined here as a
@pytest.fixture is available to any test just by listing it as a parameter.

Two things live here:
  1. patch_output_dirs  — redirects CSV writes to a temp folder so tests never
                          touch the real output/ or docs/ directories.
  2. make_response      — a helper that fakes an HTTP response so tests never
                          hit real APIs.
"""

import pytest


@pytest.fixture()
def patch_output_dirs(tmp_path, monkeypatch):
    """
    Redirect all CSV writes to a throwaway temp directory.

    Why: save_csv_dedup() uses the OUT and DOCS Path objects defined at the
    top of common.py. monkeypatch.setattr() replaces those objects for the
    duration of one test and restores them automatically when the test ends.

    Usage: list `patch_output_dirs` as a parameter in any test that calls
    a collector's run() or save_csv_dedup() directly.

    Returns (out_dir, docs_dir) so tests can read the written CSVs.
    """
    import src.common as common

    out_dir = tmp_path / "output"
    docs_dir = tmp_path / "docs"
    out_dir.mkdir()
    docs_dir.mkdir()

    monkeypatch.setattr(common, "OUT", out_dir)
    monkeypatch.setattr(common, "DOCS", docs_dir)

    return out_dir, docs_dir


