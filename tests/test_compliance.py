# tests/test_compliance.py
from pathlib import Path

import pytest

from site_builder.compliance import (
    HYPOTHETICAL_ALLOWLIST,
    check_hypothetical_allowlist,
)


def test_no_violations_in_clean_html(tmp_path):
    (tmp_path / "a.html").write_text("<html><body><p>clean copy</p></body></html>")
    assert check_hypothetical_allowlist(tmp_path) == []


def test_detects_hypothetical_word_outside_allowlist(tmp_path):
    (tmp_path / "a.html").write_text(
        "<html><body><p>This shows hypothetical performance.</p></body></html>"
    )
    out = check_hypothetical_allowlist(tmp_path)
    assert len(out) == 1
    path, line, snippet = out[0]
    assert path.name == "a.html"
    assert line == 1
    assert "hypothetical" in snippet.lower()


def test_allowlisted_sentence_passes(tmp_path, monkeypatch):
    sentence = "Hypothetical losses can exceed margin requirements."
    monkeypatch.setattr(
        "site_builder.compliance.HYPOTHETICAL_ALLOWLIST",
        {sentence},
    )
    (tmp_path / "a.html").write_text(
        f"<html><body><p>{sentence}</p></body></html>"
    )
    assert check_hypothetical_allowlist(tmp_path) == []


def test_partial_match_still_violates(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "site_builder.compliance.HYPOTHETICAL_ALLOWLIST",
        {"Hypothetical losses can exceed margin requirements."},
    )
    # Different sentence with "hypothetical" → must violate
    (tmp_path / "a.html").write_text(
        "<html><body><p>This is a hypothetical scenario.</p></body></html>"
    )
    out = check_hypothetical_allowlist(tmp_path)
    assert len(out) == 1


def test_recurses_into_subdirs(tmp_path):
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "b.html").write_text(
        "<html><body><p>hypothetical leak</p></body></html>"
    )
    out = check_hypothetical_allowlist(tmp_path)
    assert len(out) == 1
    assert out[0][0].parent.name == "sub"


def test_case_insensitive_match(tmp_path):
    (tmp_path / "a.html").write_text(
        "<html><body><p>HYPOTHETICAL all caps</p></body></html>"
    )
    out = check_hypothetical_allowlist(tmp_path)
    assert len(out) == 1
