"""Submit batch jobs and track them in Firestore.

Handles uploading JSONL files, creating batch jobs, and recording
job metadata in the batch_jobs Firestore collection.
"""

import random
import re
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple

from ..config import config, logger
from ..firebase_client import save_batch_job, get_batch_job, get_batch_jobs_in_states, update_batch_job
from .client import (
    upload_jsonl_file,
    create_batch_job,
    poll_batch_job,
    is_not_found_error,
    IMPORTABLE_STATES,
    _state_str,
)

# Pseudo-state reported by poll_and_update when the job no longer exists in the Gemini API
STATE_NOT_FOUND = "NOT_FOUND"

ABANDON_HINT = "If it can never be completed, run: python -m src.main --mode batch --abandon-job {job_name}"

from shared.constants import GEMINI_MODEL, BATCH_ANALYSIS_VERSION


def submit_batch(
    jsonl_path: str,
    analysis_type: str,
    request_count: int,
    job_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Submit a JSONL file as a batch prediction job.

    Args:
        jsonl_path: Path to the prepared JSONL file.
        analysis_type: The analysis type ('thumbnail' or 'title_description').
        request_count: Number of requests in the JSONL file.
        job_name: Optional display name for the job.

    Returns:
        Dict with job info including 'jobName' and 'state'.
    """
    if not jsonl_path:
        raise ValueError("No JSONL file path provided")

    # Validate user-provided job name format
    if job_name and not re.match(r"^[A-Za-z0-9_-]{1,128}$", job_name):
        raise ValueError("Invalid job name. Use alphanumeric, dash, underscore only (max 128 chars).")

    # Generate display name with nonce to avoid timestamp collisions
    if job_name:
        display_name = job_name
    else:
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        nonce = random.randint(1000, 9999)
        display_name = f"batch_{analysis_type}_{timestamp}_{nonce}"

    print("\nSubmitting batch job...")
    print(f"  File: {jsonl_path}")
    print(f"  Requests: {request_count}")
    print(f"  Model: {GEMINI_MODEL}")

    # Upload JSONL file
    print("  Uploading JSONL file...")
    file_name = upload_jsonl_file(jsonl_path, display_name)
    print(f"  Uploaded as: {file_name}")

    # Create batch job
    print("  Creating batch job...")
    job = create_batch_job(GEMINI_MODEL, file_name)
    print(f"  Job created: {job.name}")
    print(f"  State: {job.state}")

    # Extract job ID for Firestore document key
    # job.name format: "batches/abc123"
    job_id = job.name.replace("/", "_") if "/" in job.name else job.name

    # Save to Firestore
    job_record = {
        "jobName": job.name,
        "displayName": display_name,
        "analysisType": analysis_type,
        "model": GEMINI_MODEL,
        "analysisVersion": BATCH_ANALYSIS_VERSION,
        "state": _state_str(job.state),
        "requestCount": request_count,
        "srcFileName": file_name,
        "jsonlPath": jsonl_path,
        "createdAt": datetime.utcnow().isoformat(),
        "completedAt": None,
        "importedAt": None,
        "importStats": None,
    }
    save_batch_job(job_id, job_record)
    print(f"  Tracked in Firestore: batch_jobs/{job_id}")

    # Estimated cost (batch pricing is ~50% of standard)
    # Rough estimate: ~$0.001 per request for text, ~$0.002 for vision
    if analysis_type == "thumbnail":
        cost_per_req = 0.002
    else:
        cost_per_req = 0.001
    est_cost = request_count * cost_per_req
    print(f"  Estimated cost: ~${est_cost:.2f} ({request_count} requests x ~${cost_per_req}/req at batch pricing)")

    return job_record


def poll_and_update(
    analysis_type: str,
    poll_interval: Optional[int] = None,
    job_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Poll a batch job until completion and update Firestore.

    Finds the latest active job for the analysis type, or uses the
    provided job_name. Polls until a terminal state is reached.

    Args:
        analysis_type: The analysis type to find jobs for.
        poll_interval: Seconds between polls (default: config value).
        job_name: Specific job name to poll (optional).

    Returns:
        Updated job record dict.
    """
    interval = poll_interval or config.BATCH_POLL_INTERVAL

    if job_name:
        # Poll specific job
        batch_job_name = job_name
        job_id = job_name.replace("/", "_") if "/" in job_name else job_name
    else:
        # Find latest active job for this analysis type
        job_record = _find_active_job(analysis_type)
        if not job_record:
            print(f"No active batch job found for {analysis_type}")
            return {}
        batch_job_name = job_record["jobName"]
        job_id = job_record["id"]

    print(f"\nPolling batch job: {batch_job_name}")
    print(f"  Analysis type: {analysis_type}")
    print(f"  Poll interval: {interval}s")

    # Poll until complete. A 404 is permanent (job deleted / expired from the API): mark the
    # job abandoned so it stops blocking new batches. Transient errors propagate unchanged.
    try:
        job = poll_batch_job(batch_job_name, poll_interval=interval)
    except Exception as e:
        if not is_not_found_error(e):
            raise
        reason = f"Job not found in Gemini API while polling: {e}"
        logger.error(f"{batch_job_name}: {reason}")
        mark_job_abandoned(job_id, reason)
        print(f"\nJob {batch_job_name} no longer exists in the Gemini API; marked as abandoned.")
        return {"state": STATE_NOT_FOUND, "abandoned": True, "jobName": batch_job_name, "jobId": job_id}

    # Update Firestore
    state = _state_str(job.state)
    updates = {"state": state}
    if state in IMPORTABLE_STATES:
        updates["completedAt"] = datetime.utcnow().isoformat()
        # Store destination info for result import
        if job.dest:
            if hasattr(job.dest, "file_name") and job.dest.file_name:
                updates["destFileName"] = job.dest.file_name
            if hasattr(job.dest, "gcs_uri") and job.dest.gcs_uri:
                updates["destGcsUri"] = job.dest.gcs_uri
            if hasattr(job.dest, "inlined_responses") and job.dest.inlined_responses:
                updates["hasInlinedResponses"] = True
    if hasattr(job, "completion_stats") and job.completion_stats:
        stats = job.completion_stats
        updates["completionStats"] = {
            "successCount": getattr(stats, "success_count", 0),
            "failureCount": getattr(stats, "failure_count", 0),
        }
    if hasattr(job, "error") and job.error:
        updates["error"] = str(job.error)

    update_batch_job(job_id, updates)

    print(f"\nJob completed: {state}")
    if "completionStats" in updates:
        cs = updates["completionStats"]
        print(f"  Success: {cs['successCount']}, Failures: {cs['failureCount']}")

    return {**updates, "jobName": batch_job_name, "jobId": job_id}


# Non-terminal google-genai JobState values (the job may still produce results)
ACTIVE_STATES = [
    "JOB_STATE_UNSPECIFIED",
    "JOB_STATE_QUEUED",
    "JOB_STATE_PENDING",
    "JOB_STATE_RUNNING",
    "JOB_STATE_PAUSED",
    "JOB_STATE_UPDATING",
    "JOB_STATE_CANCELLING",
]


def _live_jobs(analysis_type: str, states: List[str]) -> List[Dict[str, Any]]:
    """Jobs in the given states that have not been marked abandoned, newest first."""
    return [job for job in get_batch_jobs_in_states(analysis_type, states) if not job.get("abandonedAt")]


def _find_active_job(analysis_type: str) -> Optional[Dict[str, Any]]:
    """Find the latest non-terminal, non-abandoned batch job for an analysis type."""
    jobs = _live_jobs(analysis_type, ACTIVE_STATES)
    return jobs[0] if jobs else None


def find_unimported_job(analysis_type: str) -> Optional[Dict[str, Any]]:
    """Find the latest finished, non-abandoned job whose results have not been imported yet."""
    jobs = _live_jobs(analysis_type, sorted(IMPORTABLE_STATES))
    return next((job for job in jobs if not job.get("importedAt")), None)


def job_id_for(job_name: str) -> str:
    """Firestore batch_jobs document ID for a Gemini job name ("batches/abc" -> "batches_abc")."""
    return job_name.replace("/", "_")


def mark_job_abandoned(job_id: str, reason: str) -> None:
    """Record that a job can never be polled/imported, so it no longer blocks new batches."""
    update_batch_job(job_id, {"abandonedAt": datetime.utcnow().isoformat(), "abandonReason": reason})


def abandon_job(job_name: str, reason: str = "Abandoned manually (--abandon-job)") -> Dict[str, Any]:
    """Mark a tracked job as abandoned (CLI escape hatch). Returns the job record before the change.

    Raises:
        ValueError: If the job is not tracked in Firestore.
    """
    job_id = job_id_for(job_name)
    record = get_batch_job(job_id)
    if not record:
        raise ValueError(f"Batch job not found in Firestore: {job_name} (document batch_jobs/{job_id})")
    mark_job_abandoned(job_id, reason)
    return record


def find_blocking_job(analysis_type: str) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
    """Find a job that must be finished before a new batch may be submitted.

    Returns ("unimported", job), ("active", job) or (None, None). Firestore errors
    propagate: callers must not treat a failed lookup as "no job".
    """
    job = find_unimported_job(analysis_type)
    if job:
        return "unimported", job
    job = _find_active_job(analysis_type)
    if job:
        return "active", job
    return None, None
