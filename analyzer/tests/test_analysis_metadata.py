"""Tests for the shared analysis-provenance metadata helper."""

from src.analysis_metadata import stamp_analysis_metadata
from shared.constants import GEMINI_MODEL, BATCH_ANALYSIS_VERSION


def test_stamps_single_sourced_provenance_fields():
    result = {"existing": "value"}
    returned = stamp_analysis_metadata(result)

    # Mutates in place and returns the same dict.
    assert returned is result
    # Provenance fields come from the shared constants (no hardcoded strings).
    assert returned["modelUsed"] == GEMINI_MODEL
    assert returned["analysisVersion"] == BATCH_ANALYSIS_VERSION
    assert returned["analyzedAt"]  # non-empty ISO timestamp
    # Existing keys are preserved.
    assert returned["existing"] == "value"


def test_analysis_version_matches_across_call_sites():
    # The whole point of the helper: every stamped doc gets the same version.
    a = stamp_analysis_metadata({})
    b = stamp_analysis_metadata({})
    assert a["analysisVersion"] == b["analysisVersion"] == BATCH_ANALYSIS_VERSION
