"""Import results from completed Gemini Batch API jobs.

Downloads output JSONL, parses each result line, and saves analysis
data to the appropriate Firestore subcollection.
"""

import json
import os
from datetime import datetime
from typing import Optional, Dict, Any, Tuple

from ..config import config, logger
from ..firebase_client import (
    save_analysis,
    get_video,
    get_batch_job as get_batch_job_record,
    get_latest_batch_job,
    update_batch_job,
)
from ..analyzers.local_text_features import extract_local_features, deep_merge
from .client import (
    get_batch_job as get_batch_job_status,
    download_result_file,
    _state_str,
)

from shared.constants import BATCH_ANALYSIS_VERSION, GEMINI_MODEL


def import_batch_results(
    analysis_type: str,
    job_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Import results from a completed batch job into Firestore.

    Finds the latest succeeded-but-not-imported job for the analysis type,
    or uses the provided job_name. Downloads the result file and processes
    each line into Firestore.

    Args:
        analysis_type: The analysis type ('thumbnail' or 'title_description').
        job_name: Specific job name to import from (optional).

    Returns:
        Import statistics dict.
    """
    # Find the job to import
    if job_name:
        job_id = job_name.replace('/', '_') if '/' in job_name else job_name
        job_record = get_batch_job_record(job_id)
        if not job_record:
            print(f"Batch job not found in Firestore: {job_name}")
            return {'error': 'Job not found'}
    else:
        job_record = _find_importable_job(analysis_type)
        if not job_record:
            print(f"No completed batch job found to import for {analysis_type}")
            return {'error': 'No importable job found'}
        job_id = job_record['id']

    batch_job_name = job_record['jobName']
    request_count = job_record.get('requestCount', '?')
    print(f"\nImporting results from batch job: {batch_job_name}")
    print(f"  Analysis type: {analysis_type}"
          + (" (hybrid: Gemini + local features)" if analysis_type == 'title_description' else ""))
    print(f"  Expected results: {request_count}")

    # Get the actual job status to find result location
    job = get_batch_job_status(batch_job_name)

    if _state_str(job.state) != 'JOB_STATE_SUCCEEDED':
        print(f"  Job state is {job.state}, cannot import results")
        return {'error': f'Job not in succeeded state: {job.state}'}

    # Download results
    output_path = _download_results(job, job_record, analysis_type)
    if not output_path:
        return {'error': 'Could not download results'}

    # Process results
    stats = _process_result_file(output_path, analysis_type)

    # Update job record
    update_batch_job(job_id, {
        'importedAt': datetime.utcnow().isoformat(),
        'importStats': stats,
    })

    print(f"\n  Import complete:")
    print(f"    Total results:       {stats['total']}")
    print(f"    Successful imports:  {stats['imported']}")
    print(f"    Failed imports:      {stats['failed']}")
    print(f"    Parse errors:        {stats['parseErrors']}")
    if stats.get('localFeaturesMerged', 0) > 0:
        print(f"    Local features:      {stats['localFeaturesMerged']} merged (title_description)")

    return stats


def _find_importable_job(analysis_type: str) -> Optional[Dict[str, Any]]:
    """Find the latest succeeded job that hasn't been imported yet."""
    job = get_latest_batch_job(analysis_type, state='JOB_STATE_SUCCEEDED')
    if job and not job.get('importedAt'):
        return job
    return None


def _download_results(job, job_record: Dict[str, Any],
                       analysis_type: str) -> Optional[str]:
    """Download result file from a completed batch job."""
    output_dir = os.path.join(config.PROJECT_ROOT, 'data', 'batch', 'results')
    os.makedirs(output_dir, exist_ok=True)

    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    output_path = os.path.join(output_dir, f"results_{analysis_type}_{timestamp}.jsonl")

    # Try dest.file_name (Gemini Developer API)
    if job.dest and hasattr(job.dest, 'file_name') and job.dest.file_name:
        print(f"  Downloading from file: {job.dest.file_name}")
        download_result_file(job.dest.file_name, output_path)
        return output_path

    # Try dest.gcs_uri (Vertex AI)
    if job.dest and hasattr(job.dest, 'gcs_uri') and job.dest.gcs_uri:
        print(f"  Result at GCS: {job.dest.gcs_uri}")
        # For GCS URIs, use gsutil or storage client
        logger.warning("GCS URI download not implemented — use gsutil manually")
        return None

    # Try inlined responses
    if job.dest and hasattr(job.dest, 'inlined_responses') and job.dest.inlined_responses:
        print("  Processing inlined responses...")
        with open(output_path, 'w') as f:
            for resp in job.dest.inlined_responses:
                f.write(json.dumps(_serialize_response(resp)) + '\n')
        return output_path

    # Check destFileName from our Firestore record
    dest_file = job_record.get('destFileName')
    if dest_file:
        print(f"  Downloading from tracked file: {dest_file}")
        download_result_file(dest_file, output_path)
        return output_path

    logger.error("Could not determine result location for batch job")
    return None


def _serialize_response(resp) -> Dict[str, Any]:
    """Serialize a batch response object to dict."""
    if isinstance(resp, dict):
        return resp
    if hasattr(resp, 'to_dict'):
        return resp.to_dict()
    return {'raw': str(resp)}


def _process_result_file(file_path: str, analysis_type: str) -> Dict[str, Any]:
    """Process a JSONL result file and import each result to Firestore.

    Each line in the JSONL is expected to have:
    - key: "{channelId}_{videoId}_{analysisType}"
    - response: The Gemini API response object

    Returns:
        Statistics dict.
    """
    stats = {
        'total': 0,
        'imported': 0,
        'failed': 0,
        'parseErrors': 0,
        'localFeaturesMerged': 0,
    }

    # Count total lines for progress display
    with open(file_path, 'r') as f:
        total_lines = sum(1 for line in f if line.strip())

    current_channel = None

    with open(file_path, 'r') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue

            stats['total'] += 1

            try:
                result = json.loads(line)
            except json.JSONDecodeError as e:
                logger.error(f"JSON parse error on line {line_num}: {e}")
                stats['parseErrors'] += 1
                continue

            # Track channel changes for progress display
            key = result.get('key', '')
            if key and len(key) >= 24 and key[0:2] == 'UC':
                ch_id = key[:24]
                if ch_id != current_channel:
                    current_channel = ch_id

            try:
                merged_local = _import_single_result(result, analysis_type)
                stats['imported'] += 1
                if merged_local:
                    stats['localFeaturesMerged'] += 1
            except Exception as e:
                logger.error(f"Import error on line {line_num}: {e}")
                stats['failed'] += 1

            # Progress logging every 100 results
            if stats['total'] % 100 == 0:
                ch_display = current_channel or '?'
                print(f"  [{stats['total']:>{len(str(total_lines))}}/{total_lines}]  {ch_display} — "
                      f"{stats['imported']} imported, {stats['failed']} failed")

    return stats


def _import_single_result(result: Dict[str, Any], analysis_type: str) -> bool:
    """Import a single batch result into Firestore.

    Parses the key to extract channelId and videoId, then extracts
    the JSON response text and saves it as analysis data.

    Returns:
        True if local features were merged, False otherwise.
    """
    key = result.get('key', '')
    response = result.get('response', {})

    # Parse key: "{channelId}_{videoId}_{analysisType}"
    # Channel IDs are 24 chars starting with UC, video IDs are 11 chars
    channel_id, video_id = _parse_result_key(key, analysis_type)

    if not channel_id or not video_id:
        raise ValueError(f"Could not parse key: {key}")

    # Extract response text from Gemini response structure
    analysis_data = _extract_analysis_data(response)

    if not analysis_data:
        raise ValueError(f"No analysis data in response for key: {key}")

    # For title_description, merge locally-computed deterministic features
    merged_local = False
    if analysis_type == 'title_description':
        video_doc = get_video(channel_id, video_id)
        if video_doc:
            title = video_doc.get('title', '')
            description = video_doc.get('description', '')
            local_features = extract_local_features(title, description)
            analysis_data = deep_merge(analysis_data, local_features)
            merged_local = True

    # Add metadata
    analysis_data['analyzedAt'] = datetime.utcnow().isoformat()
    analysis_data['modelUsed'] = GEMINI_MODEL
    analysis_data['analysisVersion'] = BATCH_ANALYSIS_VERSION
    analysis_data['batchMode'] = True

    # Save to Firestore
    save_analysis(channel_id, video_id, analysis_type, analysis_data)
    return merged_local


def _parse_result_key(key: str, analysis_type: str) -> Tuple[str, str]:
    """Parse a batch result key into channel_id and video_id.

    Key format: "{channelId}_{videoId}_{analysisType}"
    Channel IDs: 24 chars starting with UC
    Video IDs: 11 chars
    """
    # Remove the analysis type suffix
    suffix = f"_{analysis_type}"
    if key.endswith(suffix):
        key = key[:-len(suffix)]

    # Channel ID is 24 chars, video ID is 11 chars, separated by _
    # Format: UC<22chars>_<11chars>
    if len(key) >= 36 and key[0:2] == 'UC' and key[24] == '_':
        channel_id = key[:24]
        video_id = key[25:]
        return channel_id, video_id

    # Fallback: split on underscore, first part is channel, rest is video
    parts = key.split('_', 1)
    if len(parts) == 2:
        return parts[0], parts[1]

    return '', ''


def _extract_analysis_data(response: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Extract analysis JSON from a Gemini batch response.

    The response structure from the batch API contains candidates
    with content parts. The text part contains our JSON analysis.
    """
    # Handle different response formats
    candidates = response.get('candidates', [])
    if not candidates:
        return None

    candidate = candidates[0]
    content = candidate.get('content', {})
    parts = content.get('parts', [])

    if not parts:
        return None

    text = parts[0].get('text', '')
    if not text:
        return None

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try cleaning markdown formatting
        clean = text.strip()
        if clean.startswith('```json'):
            clean = clean[7:]
        elif clean.startswith('```'):
            clean = clean[3:]
        if clean.endswith('```'):
            clean = clean[:-3]
        return json.loads(clean.strip())
