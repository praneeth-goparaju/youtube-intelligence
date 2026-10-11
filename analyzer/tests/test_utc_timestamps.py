"""UTC clock and legacy timestamp compatibility without deprecated APIs."""

from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from analyzer.src import analysis_metadata
from analyzer.src.batch_api import import_results, prepare, submit
from analyzer.src.processors import progress


NOW = datetime(2026, 10, 11, 6, 0, 0, 123456, tzinfo=UTC)
STORED_NOW = "2026-10-11T06:00:00.123456"
CHANNEL_ID = "UC" + "a" * 22
VIDEO_ID = "b" * 11
pytestmark = pytest.mark.filterwarnings("error:datetime.datetime.utcnow.*:DeprecationWarning")


class FixedDatetime(datetime):
    @classmethod
    def now(cls, tz=None):
        return NOW.astimezone(tz) if tz is not None else NOW.replace(tzinfo=None)


@pytest.fixture(autouse=True)
def fixed_utc_clock(monkeypatch):
    for module in (analysis_metadata, progress, import_results, prepare, submit):
        monkeypatch.setattr(module, "datetime", FixedDatetime)


def test_analysis_metadata_preserves_stored_utc_string_format():
    result = analysis_metadata.stamp_analysis_metadata({})
    assert result["analyzedAt"] == STORED_NOW
    assert datetime.fromisoformat(result["analyzedAt"]).tzinfo is None


def test_progress_uses_aware_utc_internally_and_preserves_serialized_format(monkeypatch):
    saved = Mock()
    monkeypatch.setattr(progress, "save_analysis_progress", saved)
    tracker = progress.ProgressTracker("thumbnail")

    tracker.start(10)

    assert tracker.start_time == NOW
    assert tracker.start_time.tzinfo is UTC
    assert tracker.get_stats()["elapsedSeconds"] == 0
    assert saved.call_args.args[1]["startTime"] == STORED_NOW


@pytest.mark.parametrize(
    "stored_start",
    ["2026-10-11T05:30:00.123456", "2026-10-11T05:30:00.123456Z", "2026-10-11T11:00:00.123456+05:30"],
)
def test_progress_resumes_legacy_and_offset_timestamps_as_utc(monkeypatch, stored_start):
    monkeypatch.setattr(progress, "get_analysis_progress", lambda _type: {"startTime": stored_start, "processed": 3})
    tracker = progress.ProgressTracker("thumbnail")

    assert tracker.load() is True
    assert tracker.start_time.tzinfo is UTC
    assert tracker.get_stats()["elapsedSeconds"] == 1800
    assert tracker.get_stats()["startTime"] == "2026-10-11T05:30:00.123456"


def test_batch_submission_and_completion_keep_utc_strings_sortable_with_legacy_records(monkeypatch):
    monkeypatch.setattr(submit, "upload_jsonl_file", lambda *_args: "files/requests")
    monkeypatch.setattr(
        submit, "create_batch_job", lambda *_args: SimpleNamespace(name="batches/test", state="JOB_STATE_PENDING")
    )
    saved = Mock()
    monkeypatch.setattr(submit, "save_batch_job", saved)
    monkeypatch.setattr(
        submit, "poll_batch_job", lambda *_args, **_kwargs: SimpleNamespace(state="JOB_STATE_SUCCEEDED", dest=None)
    )
    updated = Mock()
    monkeypatch.setattr(submit, "update_batch_job", updated)

    record = submit.submit_batch("requests.jsonl", "thumbnail", 1)
    result = submit.poll_and_update("thumbnail", job_name="batches/test")

    assert record["createdAt"] == STORED_NOW
    assert record["displayName"].startswith("batch_thumbnail_20261011_060000_")
    assert "2026-10-11T05:59:59" < record["createdAt"] < "2026-10-11T06:00:01"
    assert saved.call_args.args[1]["createdAt"] == STORED_NOW
    assert result["completedAt"] == STORED_NOW
    assert updated.call_args.args[1]["completedAt"] == STORED_NOW


def test_batch_preparation_retains_utc_filename_format(monkeypatch, tmp_path):
    monkeypatch.setattr(prepare.config, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(prepare, "get_all_channels", lambda: [{"id": CHANNEL_ID}])
    monkeypatch.setattr(
        prepare,
        "get_all_channel_videos_for_batch",
        lambda _id: [{"id": VIDEO_ID, "title": "Recipe", "description": "Steps"}],
    )
    monkeypatch.setattr(prepare, "get_analyzed_video_ids", lambda *_args: set())

    output_path, request_count = prepare.prepare_batch_requests("title_description")

    assert request_count == 1
    assert Path(output_path).name == "batch_title_description_20261011_060000.jsonl"
    assert Path(output_path).is_file()


def test_batch_import_retains_utc_timestamp_and_output_filename(monkeypatch, tmp_path):
    record = {"jobName": "batches/test", "requestCount": 1}
    result_row = {
        "key": f"{CHANNEL_ID}_{VIDEO_ID}_thumbnail",
        "response": {"candidates": [{"content": {"parts": [{"text": '{"scene":{"location":"kitchen"}}'}]}}]},
    }
    monkeypatch.setattr(import_results.config, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(import_results, "get_batch_job_record", lambda _id: record)
    monkeypatch.setattr(
        import_results,
        "get_batch_job_status",
        lambda _name: SimpleNamespace(
            state="JOB_STATE_SUCCEEDED", dest=SimpleNamespace(inlined_responses=[result_row])
        ),
    )
    monkeypatch.setattr(import_results, "get_all_channels_unfiltered", lambda: [{"id": CHANNEL_ID}])
    monkeypatch.setattr(import_results, "save_analysis", lambda *_args: None)
    monkeypatch.setattr(import_results, "update_batch_job", lambda _id, updates: record.update(updates))

    result = import_results.import_batch_results("thumbnail", "batches/test")

    assert result["imported"] == 1
    assert record["importedAt"] == STORED_NOW
    assert (tmp_path / "data/batch/results/results_thumbnail_20261011_060000.jsonl").is_file()
