"""Prepare JSONL request files for Gemini Batch API.

Collects unanalyzed videos from Firestore and builds JSONL files
with the proper request format for thumbnail and title_description analysis.
"""

import json
import os
from datetime import datetime
from typing import Dict, Any, Optional, Tuple

from ..config import config, logger
from ..firebase_client import (
    get_all_channels,
    get_channel,
    get_analyzed_video_ids,
    get_all_channel_videos_for_batch,
    download_thumbnail,
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


def _build_thumbnail_request(channel_id: str, video_id: str, image_bytes: bytes) -> Dict[str, Any]:
    """Build a single thumbnail batch request.

    Embeds the image as inline base64 data. GCS URIs don't work because the
    Gemini API service account lacks read access to the Firebase Storage bucket.
    """
    import base64

    b64_data = base64.b64encode(image_bytes).decode("ascii")

    return {
        "key": f"{channel_id}_{video_id}_{ANALYSIS_TYPE_THUMBNAIL}",
        "request": {
            "model": f"models/{GEMINI_MODEL}",
            "contents": [
                {
                    "parts": [
                        {"text": THUMBNAIL_USER_PROMPT},
                        {
                            "inline_data": {
                                "data": b64_data,
                                "mime_type": "image/jpeg",
                            }
                        },
                    ]
                }
            ],
            "system_instruction": {"parts": [{"text": THUMBNAIL_SYSTEM_INSTRUCTION}]},
            "generation_config": {
                "response_mime_type": "application/json",
                "response_json_schema": _pydantic_to_schema(ThumbnailAnalysisSchema),
                "temperature": 0.1,
                "max_output_tokens": 16384,
            },
        },
    }


def _build_title_description_request(channel_id: str, video_id: str, title: str, description: str) -> Dict[str, Any]:
    """Build a single title+description batch request."""
    input_text = build_title_description_input(title, description)
    user_prompt = f"{TITLE_DESC_USER_PROMPT}\n\nText to analyze:\n{input_text}"

    return {
        "key": f"{channel_id}_{video_id}_{ANALYSIS_TYPE_TITLE_DESCRIPTION}",
        "request": {
            "model": f"models/{GEMINI_MODEL}",
            "contents": [{"parts": [{"text": user_prompt}]}],
            "system_instruction": {"parts": [{"text": TITLE_DESC_SYSTEM_INSTRUCTION}]},
            "generation_config": {
                "response_mime_type": "application/json",
                "response_json_schema": _pydantic_to_schema(TitleDescriptionAnalysisSchema),
                "temperature": 0.1,
                "max_output_tokens": 16384,
            },
        },
    }


def _pydantic_to_schema(model_class) -> Dict[str, Any]:
    """Convert a Pydantic model to JSON Schema dict for the Batch API.

    The Batch API JSONL format requires a raw JSON Schema dict (not a Pydantic
    model object) since it's serialized to JSON. Pydantic generates $defs/$ref
    for nested models, but the Gemini Batch API doesn't support those — we must
    inline all references.
    """
    schema = model_class.model_json_schema()
    defs = schema.pop("$defs", {})
    if defs:
        schema = _resolve_refs(schema, defs)
    return schema


def _resolve_refs(node: Any, defs: Dict[str, Any]) -> Any:
    """Recursively resolve all $ref pointers by inlining from $defs."""
    if isinstance(node, dict):
        if "$ref" in node:
            ref_path = node["$ref"]  # e.g. "#/$defs/ThumbnailScene"
            ref_name = ref_path.split("/")[-1]
            resolved = defs.get(ref_name, {})
            # Recursively resolve in case of nested refs
            return _resolve_refs(resolved, defs)
        return {k: _resolve_refs(v, defs) for k, v in node.items()}
    if isinstance(node, list):
        return [_resolve_refs(item, defs) for item in node]
    return node


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
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    output_dir = os.path.join(config.PROJECT_ROOT, "data", "batch")
    os.makedirs(output_dir, exist_ok=True)
    jsonl_path = os.path.join(output_dir, f"batch_{analysis_type}_{timestamp}.jsonl")

    request_count = 0
    already_analyzed = 0
    missing_data = 0
    channels_scanned = 0
    channels_with_work = 0
    total_channels = len(channels)

    print(f"\nPreparing {analysis_type} batch requests...")
    print(f"Scanning up to {total_channels} channels (batch size: {batch_size})...\n")

    with open(jsonl_path, "w") as f:
        for channel in channels:
            if request_count >= batch_size:
                break

            ch_id = channel["id"]
            ch_name = channel.get("title", channel.get("name", ch_id))
            channels_scanned += 1

            print(f"  [{channels_scanned}/{total_channels}] {ch_name[:35]}...", end=" ", flush=True)

            videos = get_all_channel_videos_for_batch(ch_id)
            video_ids = [v["id"] for v in videos]

            # Batch check all analysis docs in one RPC instead of per-video
            analyzed_set = get_analyzed_video_ids(ch_id, analysis_type, video_ids)

            ch_needs = 0
            ch_analyzed = len(analyzed_set)
            already_analyzed += ch_analyzed

            for video in videos:
                if request_count >= batch_size:
                    break

                video_id = video["id"]

                if video_id in analyzed_set:
                    continue

                request = _build_request(analysis_type, ch_id, video_id, video)
                if request is None:
                    missing_data += 1
                    continue

                f.write(json.dumps(request) + "\n")
                request_count += 1
                ch_needs += 1

            if ch_needs > 0:
                channels_with_work += 1
                print(f"+{ch_needs} new  (total: {request_count})")
            else:
                print(f"all {ch_analyzed} done")

    remaining = total_channels - channels_scanned
    print("\n  Batch preparation complete:")
    print(
        f"    Requests written:  {request_count}" + (" (hit batch size limit)" if request_count >= batch_size else "")
    )
    print(f"    Already analyzed:  {already_analyzed}")
    print(f"    Missing data:      {missing_data}")
    print(
        f"    Channels scanned:  {channels_scanned}/{total_channels}"
        + (f" ({remaining} skipped — batch full)" if remaining > 0 else "")
    )
    print(f"    Output file:       {jsonl_path}")

    if request_count == 0:
        # Clean up empty file
        os.remove(jsonl_path)
        print("  No requests to process — all videos already analyzed.")
        return "", 0

    return jsonl_path, request_count


def _build_request(
    analysis_type: str, channel_id: str, video_id: str, video: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """Build a single batch request based on analysis type."""
    if analysis_type == ANALYSIS_TYPE_THUMBNAIL:
        thumbnail_path = video.get("thumbnailStoragePath", "")
        if not thumbnail_path:
            return None
        try:
            image_bytes = download_thumbnail(thumbnail_path)
        except Exception as e:
            logger.warning(f"Failed to download thumbnail {thumbnail_path}: {e}")
            return None
        return _build_thumbnail_request(channel_id, video_id, image_bytes)

    elif analysis_type == ANALYSIS_TYPE_TITLE_DESCRIPTION:
        title = video.get("title", "")
        if not title or not title.strip():
            return None
        description = video.get("description", "")
        return _build_title_description_request(channel_id, video_id, title, description)

    return None
