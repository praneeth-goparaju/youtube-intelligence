"""Prepare JSONL request files for Gemini Batch API.

Collects unanalyzed videos from Firestore and builds JSONL files
with the proper request format for thumbnail and title_description analysis.
"""

import json
import os
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

from ..config import config, logger
from ..firebase_client import (
    get_all_channels,
    get_channel,
    has_analysis,
    get_all_channel_videos_for_batch,
)
from ..prompts import (
    THUMBNAIL_SYSTEM_INSTRUCTION,
    THUMBNAIL_USER_PROMPT,
    TITLE_DESC_SYSTEM_INSTRUCTION,
    TITLE_DESC_USER_PROMPT,
    build_title_description_input,
)
from .schemas import ThumbnailAnalysisSchema, TitleDescriptionAnalysisSchema

from shared.constants import (
    ANALYSIS_TYPE_THUMBNAIL,
    ANALYSIS_TYPE_TITLE_DESCRIPTION,
    GEMINI_MODEL,
)


def _build_thumbnail_request(channel_id: str, video_id: str,
                              thumbnail_storage_path: str) -> Dict[str, Any]:
    """Build a single thumbnail batch request.

    Uses GCS URI directly since Firebase Storage IS Google Cloud Storage.
    """
    gcs_uri = f"{config.GCS_BUCKET_URI}/{thumbnail_storage_path}"

    return {
        "key": f"{channel_id}_{video_id}_{ANALYSIS_TYPE_THUMBNAIL}",
        "request": {
            "model": f"models/{GEMINI_MODEL}",
            "contents": [{
                "parts": [
                    {"text": THUMBNAIL_USER_PROMPT},
                    {
                        "file_data": {
                            "file_uri": gcs_uri,
                            "mime_type": "image/jpeg",
                        }
                    },
                ]
            }],
            "system_instruction": {
                "parts": [{"text": THUMBNAIL_SYSTEM_INSTRUCTION}]
            },
            "generation_config": {
                "response_mime_type": "application/json",
                "response_schema": _pydantic_to_schema(ThumbnailAnalysisSchema),
                "temperature": 0.1,
                "max_output_tokens": 8192,
            },
        },
    }


def _build_title_description_request(channel_id: str, video_id: str,
                                      title: str, description: str) -> Dict[str, Any]:
    """Build a single title+description batch request."""
    input_text = build_title_description_input(title, description)
    user_prompt = f"{TITLE_DESC_USER_PROMPT}\n\nText to analyze:\n{input_text}"

    return {
        "key": f"{channel_id}_{video_id}_{ANALYSIS_TYPE_TITLE_DESCRIPTION}",
        "request": {
            "model": f"models/{GEMINI_MODEL}",
            "contents": [{
                "parts": [{"text": user_prompt}]
            }],
            "system_instruction": {
                "parts": [{"text": TITLE_DESC_SYSTEM_INSTRUCTION}]
            },
            "generation_config": {
                "response_mime_type": "application/json",
                "response_schema": _pydantic_to_schema(TitleDescriptionAnalysisSchema),
                "temperature": 0.1,
                "max_output_tokens": 8192,
            },
        },
    }


def _pydantic_to_schema(model_class) -> Dict[str, Any]:
    """Convert a Pydantic model to JSON Schema dict for the Batch API.

    The Batch API JSONL format requires a raw JSON Schema dict (not a Pydantic
    model object) since it's serialized to JSON. We use Pydantic's built-in
    json_schema() method to generate the schema.
    """
    return model_class.model_json_schema()


def prepare_batch_requests(
    analysis_type: str,
    channel_id: Optional[str] = None,
    batch_size: int = 50000,
) -> Tuple[str, int]:
    """Prepare a JSONL file with batch requests for unanalyzed videos.

    Args:
        analysis_type: 'thumbnail' or 'title_description'.
        channel_id: Optional single channel ID. If None, processes all channels.
        batch_size: Maximum requests per JSONL file.

    Returns:
        Tuple of (jsonl_file_path, request_count).
    """
    if analysis_type not in (ANALYSIS_TYPE_THUMBNAIL, ANALYSIS_TYPE_TITLE_DESCRIPTION):
        raise ValueError(f"Unknown analysis type: {analysis_type}")

    # Get channels to process
    if channel_id:
        channel = get_channel(channel_id)
        if not channel:
            raise ValueError(f"Channel not found: {channel_id}")
        channels = [channel]
    else:
        channels = get_all_channels()

    # Create temp JSONL file
    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    output_dir = os.path.join(config.PROJECT_ROOT, 'data', 'batch')
    os.makedirs(output_dir, exist_ok=True)
    jsonl_path = os.path.join(output_dir, f"batch_{analysis_type}_{timestamp}.jsonl")

    request_count = 0
    skipped_count = 0

    print(f"\nPreparing {analysis_type} batch requests...")
    print(f"Scanning {len(channels)} channels for unanalyzed videos...")

    with open(jsonl_path, 'w') as f:
        for channel in channels:
            ch_id = channel['id']
            videos = get_all_channel_videos_for_batch(ch_id)

            for video in videos:
                if request_count >= batch_size:
                    break

                video_id = video['id']

                # Check if already analyzed
                if has_analysis(ch_id, video_id, analysis_type):
                    skipped_count += 1
                    continue

                request = _build_request(analysis_type, ch_id, video_id, video)
                if request is None:
                    skipped_count += 1
                    continue

                f.write(json.dumps(request) + '\n')
                request_count += 1

            if request_count >= batch_size:
                print(f"  Reached batch size limit ({batch_size})")
                break

    print(f"\nBatch preparation complete:")
    print(f"  Requests written: {request_count}")
    print(f"  Skipped (already analyzed or missing data): {skipped_count}")
    print(f"  Output file: {jsonl_path}")

    if request_count == 0:
        # Clean up empty file
        os.remove(jsonl_path)
        print("  No requests to process — all videos already analyzed.")
        return '', 0

    return jsonl_path, request_count


def _build_request(analysis_type: str, channel_id: str, video_id: str,
                    video: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Build a single batch request based on analysis type."""
    if analysis_type == ANALYSIS_TYPE_THUMBNAIL:
        thumbnail_path = video.get('thumbnailStoragePath', '')
        if not thumbnail_path:
            return None
        return _build_thumbnail_request(channel_id, video_id, thumbnail_path)

    elif analysis_type == ANALYSIS_TYPE_TITLE_DESCRIPTION:
        title = video.get('title', '')
        if not title or not title.strip():
            return None
        description = video.get('description', '')
        return _build_title_description_request(channel_id, video_id, title, description)

    return None
