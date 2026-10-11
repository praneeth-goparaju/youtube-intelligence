"""Batch recovery checks with file processing intact and external services replaced."""

import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from analyzer.src import firebase_client, main
from analyzer.src.batch_api import client, import_results, prepare, submit


CHANNEL_ID = "UC" + "a" * 22


def result_row(index, response=None):
    return {
        "key": f"{CHANNEL_ID}_{index:011}_thumbnail",
        "response": response
        if response is not None
        else {"candidates": [{"content": {"parts": [{"text": '{"scene":{"location":"kitchen"}}'}]}}]},
    }


@pytest.fixture
def batch_environment(monkeypatch, tmp_path):
    records = {}
    rows = []
    saved = []
    monkeypatch.setattr(firebase_client, "get_db", Mock(side_effect=AssertionError("Unexpected Firestore access")))

    def jobs_by_state(state, analysis_type=None):
        return sorted(
            (
                record
                for record in records.values()
                if record["state"] == state and (analysis_type is None or record["analysisType"] == analysis_type)
            ),
            key=lambda record: record["createdAt"],
            reverse=True,
        )

    def latest_job(analysis_type, state=None):
        matches = [
            record
            for record in records.values()
            if record["analysisType"] == analysis_type and (state is None or record["state"] == state)
        ]
        return max(matches, key=lambda record: record["createdAt"], default=None)

    def download(_file_name, output_path):
        with open(output_path, "w") as output:
            output.write("\n".join(json.dumps(row) for row in rows))
        return output_path

    monkeypatch.setattr(import_results.config, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(import_results, "download_result_file", download)
    monkeypatch.setattr(import_results, "get_batch_job_record", records.get)
    monkeypatch.setattr(import_results, "get_all_channels_unfiltered", lambda: [{"id": CHANNEL_ID}])
    monkeypatch.setattr(import_results, "update_batch_job", lambda key, values: records[key].update(values))
    monkeypatch.setattr(import_results, "save_analysis", lambda *args: saved.append(args))
    monkeypatch.setattr(
        import_results,
        "get_batch_job_status",
        lambda _name: SimpleNamespace(state="JOB_STATE_SUCCEEDED", dest=SimpleNamespace(file_name="files/results")),
    )
    monkeypatch.setattr(firebase_client, "get_batch_jobs_by_state", jobs_by_state)
    monkeypatch.setattr(firebase_client, "get_latest_batch_job", latest_job)
    monkeypatch.setattr(firebase_client, "get_batch_job", records.get)
    return SimpleNamespace(records=records, rows=rows, saved=saved)


def add_job(environment, job_id="batches_test", **overrides):
    record = {
        "id": job_id,
        "jobName": job_id.replace("_", "/", 1),
        "analysisType": "thumbnail",
        "state": "JOB_STATE_SUCCEEDED",
        "createdAt": "2026-10-01",
        "requestCount": len(environment.rows),
        "importedAt": None,
        **overrides,
    }
    environment.records[job_id] = record
    return record


def test_interrupted_import_remains_recoverable(monkeypatch, batch_environment):
    environment = batch_environment
    environment.rows.extend(result_row(index) for index in range(100))
    record = add_job(environment)
    save = Mock(side_effect=[ConnectionError("Firestore temporarily unavailable")] * 3 + [None] * 100)
    monkeypatch.setattr(import_results, "save_analysis", save)

    stats = import_results.import_batch_results("thumbnail", record["jobName"])

    assert stats["aborted"] is True
    assert stats["imported"] == 7
    assert record["importedAt"] is None

    save.side_effect = None
    resumed = import_results.import_batch_results("thumbnail")
    assert resumed["aborted"] is False
    assert resumed["imported"] == 100
    assert record["importedAt"] is not None


def test_terminal_response_errors_do_not_discard_valid_rows(batch_environment):
    environment = batch_environment
    environment.rows.extend(result_row(index, {}) for index in range(3))
    environment.rows.extend(result_row(index) for index in range(3, 100))
    record = add_job(environment)

    stats = import_results.import_batch_results("thumbnail", record["jobName"])

    assert stats["aborted"] is False
    assert stats["total"] == 100
    assert stats["imported"] == 97
    assert stats["failed"] == 3
    assert record["importedAt"] is not None


def test_malformed_rows_do_not_crash_or_block_valid_results(batch_environment):
    environment = batch_environment
    environment.rows.extend([[], {"key": None, "response": None}, result_row(1, {"candidates": [None]}), result_row(2)])
    record = add_job(environment)

    stats = import_results.import_batch_results("thumbnail", record["jobName"])

    assert stats["total"] == 4
    assert stats["imported"] == 1
    assert stats["parseErrors"] + stats["failed"] == 3
    assert record["importedAt"] is not None


def test_older_unfinished_job_is_found_after_latest_was_imported(batch_environment):
    environment = batch_environment
    environment.rows.append(result_row(0))
    older = add_job(environment, "batches_older")
    add_job(environment, "batches_newer", createdAt="2026-10-02", importedAt="2026-10-03")

    stats = import_results.import_batch_results("thumbnail")

    assert stats["imported"] == 1
    assert older["importedAt"] is not None


def test_truncated_result_file_does_not_mark_import_complete(batch_environment):
    environment = batch_environment
    environment.rows.append(result_row(0))
    record = add_job(environment, requestCount=2)

    stats = import_results.import_batch_results("thumbnail", record["jobName"])

    assert stats["aborted"] is True
    assert record["importedAt"] is None


@pytest.mark.parametrize("entry_point", ["loop_iteration", "default_phase"])
def test_recovery_network_error_cannot_submit_duplicate_work(monkeypatch, batch_environment, entry_point):
    environment = batch_environment
    record = add_job(environment, state="JOB_STATE_RUNNING")
    monkeypatch.setattr(prepare, "get_all_channels", lambda: [{"id": CHANNEL_ID}])
    monkeypatch.setattr(
        prepare,
        "get_all_channel_videos_for_batch",
        lambda _channel: [{"id": "a" * 11, "thumbnailStoragePath": "thumbnail.jpg"}],
    )
    monkeypatch.setattr(prepare, "get_analyzed_video_ids", lambda *args: set())
    monkeypatch.setattr(prepare, "download_thumbnail", lambda _path: b"image")
    monkeypatch.setattr(submit, "upload_jsonl_file", lambda *args: "files/request")
    created = Mock(return_value=SimpleNamespace(name="batches/duplicate", state="JOB_STATE_PENDING"))
    monkeypatch.setattr(submit, "create_batch_job", created)
    monkeypatch.setattr(submit, "save_batch_job", lambda *args: None)
    monkeypatch.setattr(submit, "update_batch_job", lambda *args: None)

    def get_job(*, name):
        if name == record["jobName"]:
            raise ConnectionError("Temporary API outage")
        return SimpleNamespace(state="JOB_STATE_SUCCEEDED", dest=None)

    monkeypatch.setattr(client, "get_client", lambda: SimpleNamespace(batches=SimpleNamespace(get=get_job)))
    args = SimpleNamespace(channel=None, batch_size=25, poll_interval=1, job_name=None)

    if entry_point == "default_phase":
        outcome = main._run_batch_phase("all", "thumbnail", args)
    else:
        outcome = main._run_batch_phase_with_stats("thumbnail", args)

    assert outcome["success"] is False
    created.assert_not_called()


@pytest.mark.parametrize("failure", ["download", "rows", "empty"])
def test_loop_stops_after_import_cannot_progress(monkeypatch, batch_environment, failure):
    environment = batch_environment
    if failure != "empty":
        environment.rows.append(result_row(0, {} if failure == "rows" else None))
    record = add_job(environment)
    calls = 0

    def get_job(_name):
        nonlocal calls
        calls += 1
        if calls > 1:
            pytest.fail("The loop attempted the unsuccessful import again")
        return SimpleNamespace(
            state="JOB_STATE_SUCCEEDED",
            dest=None if failure == "download" else SimpleNamespace(file_name="files/results"),
        )

    monkeypatch.setattr(import_results, "get_batch_job_status", get_job)
    args = SimpleNamespace(loop=True, channel=None, batch_size=25, poll_interval=1, job_name=None)
    main._run_batch_loop("all", "thumbnail", args)
    assert calls == 1
    if failure == "download":
        assert record["importedAt"] is None


def test_default_phase_resumes_the_requested_job(batch_environment):
    environment = batch_environment
    environment.rows.append(result_row(0))
    older = add_job(environment, "batches_older")
    requested = add_job(environment, "batches_requested", createdAt="2026-10-02")
    args = SimpleNamespace(channel=None, batch_size=25, poll_interval=1, job_name=requested["jobName"])

    outcome = main._run_batch_phase("all", "thumbnail", args)

    assert outcome["success"] is True
    assert requested["importedAt"] is not None
    assert older["importedAt"] is None


def test_loop_moves_past_an_explicit_completed_job(monkeypatch, batch_environment):
    environment = batch_environment
    environment.rows.append(result_row(0))
    record = add_job(environment)
    monkeypatch.setattr(prepare, "get_all_channels", lambda: [])
    get_job = Mock(
        return_value=SimpleNamespace(state="JOB_STATE_SUCCEEDED", dest=SimpleNamespace(file_name="files/results"))
    )
    original_get = get_job

    def get_once(name):
        if original_get.call_count:
            pytest.fail("The loop imported the explicitly named job twice")
        return original_get(name)

    monkeypatch.setattr(import_results, "get_batch_job_status", get_once)
    args = SimpleNamespace(loop=True, channel=None, batch_size=25, poll_interval=1, job_name=record["jobName"])

    main._run_batch_loop("all", "thumbnail", args)

    get_job.assert_called_once_with(record["jobName"])
    assert args.job_name == record["jobName"]
