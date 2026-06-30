"""Tests for shared.firebase_utils — the reusable Firebase helper module.

These live in the insights suite because CI runs pytest only for analyzer/ and
insights/ (shared/ has no standalone test run), and insights' conftest puts the
project root on sys.path so the top-level `shared` package is importable.

They assert that the helper functions log errors (rather than print) and return
their documented "safe" fallbacks when Firebase has not been initialized.
"""

import logging

from shared.firebase_utils import fetch_document, fetch_collection, save_document


def test_fetch_document_logs_and_returns_none_when_uninitialized(caplog):
    with caplog.at_level(logging.ERROR):
        result = fetch_document("channels", "missing-id")
    assert result is None
    assert any("Error fetching document" in record.message for record in caplog.records)


def test_fetch_collection_logs_and_returns_empty_when_uninitialized(caplog):
    with caplog.at_level(logging.ERROR):
        result = fetch_collection("channels")
    assert result == []
    assert any("Error fetching collection" in record.message for record in caplog.records)


def test_save_document_logs_and_returns_false_when_uninitialized(caplog):
    with caplog.at_level(logging.ERROR):
        result = save_document("channels", "doc-id", {"field": "value"})
    assert result is False
    assert any("Error saving document" in record.message for record in caplog.records)
