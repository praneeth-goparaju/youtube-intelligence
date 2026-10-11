"""Provenance metadata for analysis result documents.

Every analysis document — sync or batch, thumbnail or title_description —
should carry identical provenance fields. Centralizing the stamping here keeps
modelUsed / analysisVersion single-sourced so they cannot drift between the
sync analyzers and the batch import path (as analysisVersion previously did).
"""

from datetime import UTC, datetime
from typing import Any, Dict

from shared.constants import GEMINI_MODEL, BATCH_ANALYSIS_VERSION


def stamp_analysis_metadata(result: Dict[str, Any]) -> Dict[str, Any]:
    """Stamp standard provenance fields onto an analysis result in place.

    Sets analyzedAt (UTC ISO timestamp), modelUsed, and analysisVersion, then
    returns the same dict for convenience.
    """
    # Preserve the existing UTC string representation stored in Firestore.
    result["analyzedAt"] = datetime.now(UTC).replace(tzinfo=None).isoformat()
    result["modelUsed"] = GEMINI_MODEL
    result["analysisVersion"] = BATCH_ANALYSIS_VERSION
    return result
