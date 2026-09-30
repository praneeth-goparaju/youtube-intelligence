"""Tests for batch job state handling, resume guards and result import.

Firestore / Gemini collaborators are replaced with in-memory fakes; the code under
test is the real orchestration and import logic.
"""

import json
from types import SimpleNamespace

import pytest

from src import main
from src.batch_api import client, import_results, submit

CHANNEL = "UC" + "a" * 22
VIDEO_OK = "vid_ok_0001"
VIDEO_BAD = "vid_bad_001"


class TestJobStates:
    @pytest.mark.parametrize(
        "state",
        [
            "JOB_STATE_SUCCEEDED",
            "JOB_STATE_FAILED",
            "JOB_STATE_CANCELLED",
            "JOB_STATE_EXPIRED",
            "JOB_STATE_PARTIALLY_SUCCEEDED",
        ],
    )
    def test_terminal_states_are_completed(self, state):
        assert state in client.COMPLETED_STATES
        assert state not in submit.ACTIVE_STATES

    def test_every_sdk_state_is_classified(self):
        from google.genai.types import JobState

        for state in JobState:
            assert (state.value in client.COMPLETED_STATES) != (state.value in submit.ACTIVE_STATES), state

    def test_expired_job_is_not_active(self, monkeypatch):
        jobs = {"JOB_STATE_EXPIRED": [{"id": "b_1", "jobName": "batches/1", "state": "JOB_STATE_EXPIRED"}]}
        monkeypatch.setattr(
            submit,
            "get_batch_jobs_in_states",
            lambda _type, states: [j for s in states for j in jobs.get(s, [])],
        )
        assert submit.find_blocking_job("thumbnail") == (None, None)

    def test_poll_stops_on_expired(self, monkeypatch):
        fake_job = SimpleNamespace(state=SimpleNamespace(value="JOB_STATE_EXPIRED"))
        fake_client = SimpleNamespace(batches=SimpleNamespace(get=lambda name: fake_job))
        monkeypatch.setattr(client, "get_client", lambda: fake_client)
        monkeypatch.setattr(client.time, "sleep", lambda s: pytest.fail("should not keep polling"))
        assert client.poll_batch_job("batches/1", poll_interval=1, max_polls=3) is fake_job


def _args(**kw):
    defaults = dict(channel=None, batch_size=10, poll_interval=1, job_name=None, loop=False)
    defaults.update(kw)
    return SimpleNamespace(**defaults)


class TestResumeGuard:
    def test_lookup_error_does_not_submit_new_job(self, monkeypatch):
        import src.batch_api as batch_api

        def boom(_type):
            raise ConnectionError("firestore unavailable")

        monkeypatch.setattr(submit, "find_blocking_job", boom)
        monkeypatch.setattr(batch_api, "prepare_batch_requests", lambda **kw: pytest.fail("must not prepare"))
        monkeypatch.setattr(batch_api, "submit_batch", lambda **kw: pytest.fail("must not submit"))
        with pytest.raises(ConnectionError):
            main._run_batch_phase_with_stats("thumbnail", _args())

    def test_poll_error_on_active_job_does_not_submit(self, monkeypatch):
        import src.batch_api as batch_api

        monkeypatch.setattr(
            submit, "find_blocking_job", lambda _t: ("active", {"jobName": "batches/1", "state": "JOB_STATE_RUNNING"})
        )

        def poll_fails(**kw):
            raise ConnectionError("network down")

        monkeypatch.setattr(batch_api, "poll_and_update", poll_fails)
        monkeypatch.setattr(batch_api, "submit_batch", lambda **kw: pytest.fail("must not submit"))
        with pytest.raises(ConnectionError):
            main._run_batch_phase_with_stats("thumbnail", _args())

    def test_failed_job_raises(self, monkeypatch):
        import src.batch_api as batch_api

        monkeypatch.setattr(
            submit, "find_blocking_job", lambda _t: ("active", {"jobName": "batches/1", "state": "JOB_STATE_RUNNING"})
        )
        monkeypatch.setattr(batch_api, "poll_and_update", lambda **kw: {"state": "JOB_STATE_EXPIRED"})
        with pytest.raises(main.BatchRunError):
            main._run_batch_phase_with_stats("thumbnail", _args())

    def test_prepare_phase_refuses_with_blocking_job(self, monkeypatch):
        import src.batch_api as batch_api

        monkeypatch.setattr(
            submit, "find_blocking_job", lambda _t: ("unimported", {"jobName": "batches/1", "state": "X"})
        )
        monkeypatch.setattr(batch_api, "prepare_batch_requests", lambda **kw: pytest.fail("must not prepare"))
        with pytest.raises(main.BatchRunError):
            main._run_batch_phase("prepare", "thumbnail", _args())

    def test_loop_stops_when_nothing_imported(self, monkeypatch):
        calls = []

        def one_batch(_type, _args):
            calls.append(1)
            if len(calls) > 2:
                pytest.fail("loop did not stop")
            return {"success": True, "imported": 0}  # what the old code returned for a failed import

        monkeypatch.setattr(main, "_run_batch_phase_with_stats", one_batch)
        main._run_batch_loop("all", "thumbnail", _args(loop=True))
        assert len(calls) == 1


def _result_line(video_id, payload):
    response = {"candidates": [{"content": {"parts": [{"text": payload}]}}]} if payload else {}
    return json.dumps({"key": f"{CHANNEL}_{video_id}_title_description", "response": response})


class TestImport:
    @pytest.fixture
    def saved(self, monkeypatch):
        saved = {}
        monkeypatch.setattr(import_results, "save_analysis", lambda ch, vid, t, data: saved.__setitem__(vid, data))
        monkeypatch.setattr(
            import_results,
            "get_channel_video_texts",
            lambda ch: {VIDEO_OK: {"title": "Biryani | Recipe", "description": ""}},
        )
        return saved

    def test_all_lines_processed_despite_failures(self, tmp_path, saved):
        # 10 bad lines then a good one: the old >20% threshold aborted before the good line
        lines = [_result_line(VIDEO_BAD, None)] * 10 + [_result_line(VIDEO_OK, '{"x": 1}')]
        path = tmp_path / "results.jsonl"
        path.write_text("\n".join(lines) + "\n")

        stats, failed = import_results._process_result_file(str(path), "title_description", frozenset({CHANNEL}))

        assert stats["imported"] == 1
        assert stats["failed"] == 10
        assert "aborted" not in stats
        assert failed == [(CHANNEL, VIDEO_BAD)] * 10
        assert saved[VIDEO_OK]["structure"]["separator"] == "|"
        assert saved[VIDEO_OK]["rawTitle"] == "Biryani | Recipe"

    def test_cache_miss_fetches_video_doc(self, tmp_path, saved, monkeypatch):
        other = "vid_other01"
        monkeypatch.setattr(
            import_results, "get_video", lambda ch, vid: {"title": "Tea: Masala Chai", "description": "x"}
        )
        path = tmp_path / "results.jsonl"
        path.write_text(_result_line(other, '{"x": 1}') + "\n")

        stats, _ = import_results._process_result_file(str(path), "title_description", frozenset({CHANNEL}))

        assert stats["localFeaturesMerged"] == 1
        assert saved[other]["structure"]["separator"] == ":"

    def test_missing_video_doc_counts_as_failure(self, tmp_path, saved, monkeypatch):
        monkeypatch.setattr(import_results, "get_video", lambda ch, vid: None)
        path = tmp_path / "results.jsonl"
        path.write_text(_result_line("vid_gone_01", '{"x": 1}') + "\n")

        stats, failed = import_results._process_result_file(str(path), "title_description", frozenset({CHANNEL}))

        assert stats["imported"] == 0
        assert failed == [(CHANNEL, "vid_gone_01")]
        assert saved == {}

    def test_job_name_with_other_type_is_skipped(self, monkeypatch):
        monkeypatch.setattr(
            import_results,
            "get_batch_job_record",
            lambda job_id: {"id": job_id, "jobName": "batches/1", "analysisType": "thumbnail"},
        )
        monkeypatch.setattr(import_results, "get_batch_job_status", lambda name: pytest.fail("must not import"))
        monkeypatch.setattr(import_results, "update_batch_job", lambda *a: pytest.fail("must not mark imported"))

        stats = import_results.import_batch_results("title_description", job_name="batches/1")

        assert stats["imported"] == 0
        assert stats["skipped"]

    def test_download_failure_raises_without_marking_imported(self, monkeypatch):
        monkeypatch.setattr(
            import_results,
            "get_batch_job_record",
            lambda job_id: {"id": job_id, "jobName": "batches/1", "analysisType": "thumbnail"},
        )
        monkeypatch.setattr(
            import_results,
            "get_batch_job_status",
            lambda name: SimpleNamespace(state=SimpleNamespace(value="JOB_STATE_SUCCEEDED"), dest=None),
        )
        monkeypatch.setattr(import_results, "_download_results", lambda job, record, atype: None)
        monkeypatch.setattr(import_results, "update_batch_job", lambda *a: pytest.fail("must not mark imported"))

        with pytest.raises(import_results.BatchImportError):
            import_results.import_batch_results("thumbnail", job_name="batches/1")
