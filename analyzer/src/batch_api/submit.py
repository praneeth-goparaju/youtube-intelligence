"""Submit batch jobs and track them in Firestore.

Handles uploading JSONL files, creating batch jobs, and recording
job metadata in the batch_jobs Firestore collection.
"""

from datetime import datetime
from typing import Optional, Dict, Any

from ..config import config
from ..firebase_client import save_batch_job, get_latest_batch_job, update_batch_job
from .client import (
    upload_jsonl_file,
    create_batch_job,
    poll_batch_job,
    COMPLETED_STATES,
    _state_str,
)

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

    # Generate display name
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    display_name = job_name or f"batch_{analysis_type}_{timestamp}"

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

    # Poll until complete
    job = poll_batch_job(batch_job_name, poll_interval=interval)

    # Update Firestore
    state = _state_str(job.state)
    updates = {"state": state}
    if state == "JOB_STATE_SUCCEEDED":
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


def _find_active_job(analysis_type: str) -> Optional[Dict[str, Any]]:
    """Find the latest non-terminal batch job for an analysis type."""
    # Check for running jobs first
    for state in ("JOB_STATE_RUNNING", "JOB_STATE_PENDING", "JOB_STATE_QUEUED"):
        job = get_latest_batch_job(analysis_type, state=state)
        if job:
            return job

    # Fall back to any job that doesn't have a completedAt
    job = get_latest_batch_job(analysis_type)
    if job and job.get("state") not in COMPLETED_STATES:
        return job

    return None
