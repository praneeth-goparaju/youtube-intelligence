"""Operational failures must reach the processor's failure accounting."""

from unittest.mock import Mock

import pytest

from analyzer.src.analyzers import thumbnail, title_description
from analyzer.src.gemini_client import GeminiRateLimitError
from analyzer.src.processors import batch, progress


@pytest.mark.parametrize("analysis_type", ["thumbnail", "title_description"])
def test_rate_limit_is_recorded_as_failure_with_backoff(monkeypatch, analysis_type):
    video = {"id": "a" * 11, "title": "Recipe", "description": "", "thumbnailStoragePath": "thumbnail.jpg"}
    analyzer_module = thumbnail if analysis_type == "thumbnail" else title_description
    generation_function = "analyze_image" if analysis_type == "thumbnail" else "analyze_text"
    monkeypatch.setattr(batch, "get_unanalyzed_videos_paginated", lambda *args: [video])
    monkeypatch.setattr(progress, "save_analysis_progress", lambda *args: None)
    monkeypatch.setattr(analyzer_module, "has_analysis", lambda *args: False)
    monkeypatch.setattr(thumbnail, "download_thumbnail", lambda _path: b"image")
    monkeypatch.setattr(analyzer_module, generation_function, Mock(side_effect=GeminiRateLimitError("Quota exhausted")))
    sleep = Mock()
    monkeypatch.setattr(batch.time, "sleep", sleep)

    stats = batch.BatchProcessor(analysis_type).process_channel("UC" + "a" * 22)

    assert stats == {"processed": 1, "successful": 0, "failed": 1, "skipped": 0}
    assert [call.args[0] for call in sleep.call_args_list] == [
        batch.config.REQUEST_DELAY * 4,
        batch.config.REQUEST_DELAY,
    ]


def test_thumbnail_url_fetch_failure_propagates(monkeypatch):
    monkeypatch.setattr(thumbnail, "has_analysis", lambda *args: False)
    monkeypatch.setattr(thumbnail.requests, "get", Mock(side_effect=ConnectionError("Image unavailable")))

    with pytest.raises(ConnectionError, match="Image unavailable"):
        thumbnail.ThumbnailAnalyzer().analyze_from_url("UC" + "a" * 22, "a" * 11, "https://example.com/image.jpg")
