"""Gemini Batch API client wrapper using google-genai SDK.

Handles batch job lifecycle: create, poll, list, and result retrieval.
Uses the Gemini Developer API (not Vertex AI).
"""

import time
from typing import Optional, List, Dict, Any

from google import genai
from google.genai import types

from ..config import config, logger


# Terminal states for batch jobs
COMPLETED_STATES = {
    'JOB_STATE_SUCCEEDED',
    'JOB_STATE_FAILED',
    'JOB_STATE_CANCELLED',
    'JOB_STATE_PAUSED',
}

# Client singleton
_client: Optional[genai.Client] = None


def get_client() -> genai.Client:
    """Get or create the google-genai client."""
    global _client
    if _client is None:
        _client = genai.Client(api_key=config.GOOGLE_API_KEY)
    return _client


def upload_jsonl_file(file_path: str, display_name: str) -> str:
    """Upload a JSONL file for batch processing.

    Args:
        file_path: Local path to the JSONL file.
        display_name: Display name for the uploaded file.

    Returns:
        The file resource name (e.g., "files/abc123").
    """
    client = get_client()
    uploaded = client.files.upload(
        file=file_path,
        config=types.UploadFileConfig(display_name=display_name),
    )
    logger.info(f"Uploaded {file_path} as {uploaded.name}")
    return uploaded.name


def create_batch_job(model: str, src_file_name: str) -> Any:
    """Create a batch prediction job.

    Args:
        model: Model name (e.g., "gemini-2.5-flash").
        src_file_name: Uploaded file resource name (e.g., "files/abc123").

    Returns:
        BatchJob object.
    """
    client = get_client()
    job = client.batches.create(
        model=model,
        src=src_file_name,
    )
    logger.info(f"Created batch job: {job.name} (state: {job.state})")
    return job


def get_batch_job(job_name: str) -> Any:
    """Get current status of a batch job.

    Args:
        job_name: The batch job name (e.g., "batches/abc123").

    Returns:
        BatchJob object with current state.
    """
    client = get_client()
    return client.batches.get(name=job_name)


def poll_batch_job(job_name: str, poll_interval: int = 60, max_polls: int = 1440) -> Any:
    """Poll a batch job until it reaches a terminal state.

    Args:
        job_name: The batch job name.
        poll_interval: Seconds between polls.
        max_polls: Maximum number of polls before giving up (default: 24 hours at 60s).

    Returns:
        BatchJob object in terminal state.
    """
    client = get_client()
    job = client.batches.get(name=job_name)
    polls = 0

    while job.state not in COMPLETED_STATES and polls < max_polls:
        polls += 1
        logger.info(f"Job {job_name}: state={job.state} (poll {polls}/{max_polls})")
        print(f"  State: {job.state} | Waiting {poll_interval}s... (poll {polls})")
        time.sleep(poll_interval)
        job = client.batches.get(name=job_name)

    if job.state not in COMPLETED_STATES:
        logger.warning(f"Job {job_name} did not complete after {max_polls} polls")

    return job


def list_batch_jobs(limit: int = 20) -> List[Any]:
    """List recent batch jobs.

    Args:
        limit: Maximum number of jobs to return.

    Returns:
        List of BatchJob objects.
    """
    client = get_client()
    jobs = []
    for job in client.batches.list(config=types.ListBatchJobsConfig(page_size=limit)):
        jobs.append(job)
        if len(jobs) >= limit:
            break
    return jobs


def delete_batch_job(job_name: str) -> None:
    """Delete a batch job.

    Args:
        job_name: The batch job name.
    """
    client = get_client()
    client.batches.delete(name=job_name)
    logger.info(f"Deleted batch job: {job_name}")


def download_result_file(file_name: str, output_path: str) -> str:
    """Download the result file from a completed batch job.

    For the Gemini Developer API, batch results are available via the
    dest.file_name attribute on the completed job.

    Args:
        file_name: The file resource name from job.dest.file_name.
        output_path: Local path to save the downloaded file.

    Returns:
        The local output path.
    """
    client = get_client()
    # Download the file content
    response = client.files.download(name=file_name)
    with open(output_path, 'wb') as f:
        f.write(response)
    logger.info(f"Downloaded results to {output_path}")
    return output_path
