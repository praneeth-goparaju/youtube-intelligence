"""Gemini Batch API integration for YouTube Intelligence System.

Provides batch mode analysis as an alternative to sync mode.
50% cost savings via Gemini Batch API pricing.

Workflow:
    prepare  -> Build JSONL request file from unanalyzed videos
    submit   -> Upload file and create batch job
    poll     -> Monitor job until completion
    import   -> Download results and save to Firestore
"""

from .prepare import prepare_batch_requests
from .submit import submit_batch, poll_and_update
from .import_results import import_batch_results
from .client import list_batch_jobs

__all__ = [
    "prepare_batch_requests",
    "submit_batch",
    "poll_and_update",
    "import_batch_results",
    "list_batch_jobs",
]
