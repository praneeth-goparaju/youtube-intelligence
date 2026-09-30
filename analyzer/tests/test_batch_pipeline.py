"""Tests for batch job state handling, resume guards and result import.

Firestore / Gemini collaborators are replaced with in-memory fakes; the code under
test is the real orchestration and import logic.
"""

import json
from types import SimpleNamespace

import pytest

from google.api_core import exceptions as google_exceptions
from google.genai import errors as genai_errors

from src import gemini_client, main
from src.batch_api import client, import_results, submit
from src.processors import batch as sync_batch

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


def _api_error(code):
    cls = genai_errors.ClientError if code < 500 else genai_errors.ServerError
    return cls(code, {"error": {"code": code, "message": "boom", "status": "X"}})


class FakeJobStore:
    """In-memory batch_jobs collection patched into submit / import_results."""

    def __init__(self, monkeypatch, jobs):
        self.jobs = {j["id"]: dict(j) for j in jobs}
        self.updates = []
        monkeypatch.setattr(submit, "get_batch_jobs_in_states", self.in_states)
        monkeypatch.setattr(submit, "update_batch_job", self.update)
        monkeypatch.setattr(submit, "get_batch_job", self.jobs.get)
        monkeypatch.setattr(import_results, "update_batch_job", self.update)
        monkeypatch.setattr(import_results, "get_batch_job_record", self.jobs.get)

    def in_states(self, analysis_type, states):
        return [j for j in self.jobs.values() if j["analysisType"] == analysis_type and j["state"] in states]

    def update(self, job_id, updates):
        self.updates.append((job_id, updates))
        self.jobs[job_id].update(updates)


def _job(job_id="batches_1", state="JOB_STATE_SUCCEEDED", **kw):
    return {
        "id": job_id,
        "jobName": job_id.replace("_", "/"),
        "analysisType": "thumbnail",
        "state": state,
        "importedAt": None,
        **kw,
    }


class TestAbandonedJobs:
    def test_abandoned_unimported_job_does_not_block(self, monkeypatch):
        FakeJobStore(monkeypatch, [_job(abandonedAt="2026-01-01", abandonReason="gone")])
        assert submit.find_blocking_job("thumbnail") == (None, None)
        assert submit.find_unimported_job("thumbnail") is None

    def test_abandoned_active_job_does_not_block(self, monkeypatch):
        FakeJobStore(monkeypatch, [_job(state="JOB_STATE_RUNNING", abandonedAt="2026-01-01")])
        assert submit.find_blocking_job("thumbnail") == (None, None)

    def test_live_job_still_blocks(self, monkeypatch):
        FakeJobStore(monkeypatch, [_job("batches_old", abandonedAt="x"), _job("batches_new")])
        kind, job = submit.find_blocking_job("thumbnail")
        assert (kind, job["id"]) == ("unimported", "batches_new")

    def test_poll_404_marks_abandoned(self, monkeypatch):
        store = FakeJobStore(monkeypatch, [_job(state="JOB_STATE_RUNNING")])

        def gone(name, poll_interval):
            raise _api_error(404)

        monkeypatch.setattr(submit, "poll_batch_job", gone)
        result = submit.poll_and_update("thumbnail", poll_interval=1)

        assert result["abandoned"] and result["state"] == submit.STATE_NOT_FOUND
        assert store.jobs["batches_1"]["abandonedAt"]
        assert submit.find_blocking_job("thumbnail") == (None, None)

    def test_poll_404_raises_run_error_so_loop_can_move_on(self, monkeypatch):
        FakeJobStore(monkeypatch, [_job(state="JOB_STATE_RUNNING")])
        monkeypatch.setattr(
            submit, "poll_batch_job", lambda name, poll_interval: (_ for _ in ()).throw(_api_error(404))
        )
        import src.batch_api as batch_api

        monkeypatch.setattr(batch_api, "import_batch_results", lambda **kw: pytest.fail("must not import"))
        with pytest.raises(main.BatchRunError, match="abandoned"):
            main._poll_and_import("thumbnail", "batches/1", _args())

    @pytest.mark.parametrize("error", [_api_error(503), ConnectionError("net down")])
    def test_poll_transient_error_propagates_without_abandoning(self, monkeypatch, error):
        store = FakeJobStore(monkeypatch, [_job(state="JOB_STATE_RUNNING")])

        def fails(name, poll_interval):
            raise error

        monkeypatch.setattr(submit, "poll_batch_job", fails)
        with pytest.raises(type(error)):
            submit.poll_and_update("thumbnail", poll_interval=1)
        assert store.updates == []

    def test_poll_loop_does_not_retry_404(self, monkeypatch):
        calls = []
        running = SimpleNamespace(state=SimpleNamespace(value="JOB_STATE_RUNNING"))

        def get(name):
            calls.append(name)
            if len(calls) > 1:
                raise _api_error(404)
            return running

        monkeypatch.setattr(client, "get_client", lambda: SimpleNamespace(batches=SimpleNamespace(get=get)))
        monkeypatch.setattr(client.time, "sleep", lambda s: None)
        with pytest.raises(genai_errors.ClientError):
            client.poll_batch_job("batches/1", poll_interval=1, max_polls=10, max_retries=5)
        assert len(calls) == 2

    def test_import_404_marks_abandoned(self, monkeypatch):
        store = FakeJobStore(monkeypatch, [_job()])

        def gone(name):
            raise _api_error(404)

        monkeypatch.setattr(import_results, "get_batch_job_status", gone)
        with pytest.raises(import_results.BatchImportError, match="abandoned"):
            import_results.import_batch_results("thumbnail")
        job = store.jobs["batches_1"]
        assert job["abandonedAt"] and not job["importedAt"]
        assert submit.find_blocking_job("thumbnail") == (None, None)

    def test_import_transient_error_propagates_without_abandoning(self, monkeypatch):
        store = FakeJobStore(monkeypatch, [_job()])

        def unavailable(name):
            raise _api_error(500)

        monkeypatch.setattr(import_results, "get_batch_job_status", unavailable)
        with pytest.raises(genai_errors.ServerError):
            import_results.import_batch_results("thumbnail")
        assert store.updates == []
        assert submit.find_blocking_job("thumbnail")[0] == "unimported"

    def test_gcs_results_mark_abandoned(self, monkeypatch):
        store = FakeJobStore(monkeypatch, [_job()])
        dest = SimpleNamespace(file_name=None, gcs_uri="gs://bucket/out", inlined_responses=None)
        monkeypatch.setattr(
            import_results,
            "get_batch_job_status",
            lambda name: SimpleNamespace(state=SimpleNamespace(value="JOB_STATE_SUCCEEDED"), dest=dest),
        )
        monkeypatch.setattr(import_results.config, "PROJECT_ROOT", "/nonexistent-should-not-matter", raising=False)
        monkeypatch.setattr(import_results.os, "makedirs", lambda *a, **kw: None)
        with pytest.raises(import_results.BatchImportError):
            import_results.import_batch_results("thumbnail")
        assert "gs://bucket/out" in store.jobs["batches_1"]["abandonReason"]
        assert not store.jobs["batches_1"]["importedAt"]

    def test_deleted_result_file_marks_abandoned(self, monkeypatch):
        store = FakeJobStore(monkeypatch, [_job()])
        monkeypatch.setattr(
            import_results,
            "get_batch_job_status",
            lambda name: SimpleNamespace(state=SimpleNamespace(value="JOB_STATE_SUCCEEDED"), dest=None),
        )

        def gone(job, record, atype):
            raise _api_error(404)

        monkeypatch.setattr(import_results, "_download_results", gone)
        with pytest.raises(import_results.BatchImportError):
            import_results.import_batch_results("thumbnail")
        assert store.jobs["batches_1"]["abandonedAt"]

    def test_abandon_job_cli_helper(self, monkeypatch):
        store = FakeJobStore(monkeypatch, [_job()])
        main._abandon_job("batches/1")
        assert store.jobs["batches_1"]["abandonReason"]
        assert submit.find_blocking_job("thumbnail") == (None, None)

    def test_abandon_unknown_job_exits(self, monkeypatch):
        FakeJobStore(monkeypatch, [])
        with pytest.raises(SystemExit):
            main._abandon_job("batches/nope")

    def test_blocking_error_mentions_abandon_job(self, monkeypatch):
        FakeJobStore(monkeypatch, [_job()])
        with pytest.raises(main.BatchRunError, match="--abandon-job batches/1"):
            main._ensure_no_blocking_job("thumbnail")


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

    def test_missing_video_doc_is_not_a_strike(self, tmp_path, saved, monkeypatch):
        monkeypatch.setattr(import_results, "get_video", lambda ch, vid: None)
        path = tmp_path / "results.jsonl"
        path.write_text(_result_line("vid_gone_01", '{"x": 1}') + "\n")

        stats, failed = import_results._process_result_file(str(path), "title_description", frozenset({CHANNEL}))

        assert stats["imported"] == 0
        assert stats["missingVideos"] == 1
        assert failed == []
        assert saved == {}

    def test_firestore_errors_are_not_strikes(self, tmp_path, saved, monkeypatch):
        def save_fails(ch, vid, t, data):
            raise google_exceptions.ServiceUnavailable("firestore down")

        def read_fails(ch, vid):
            raise google_exceptions.DeadlineExceeded("slow")

        monkeypatch.setattr(import_results, "save_analysis", save_fails)
        monkeypatch.setattr(import_results, "get_video", read_fails)
        path = tmp_path / "results.jsonl"
        path.write_text(_result_line(VIDEO_OK, '{"x": 1}') + "\n" + _result_line("vid_other01", '{"x": 1}') + "\n")

        stats, failed = import_results._process_result_file(str(path), "title_description", frozenset({CHANNEL}))

        assert stats["storeErrors"] == 2
        assert failed == []

    def test_content_failures_are_strikes(self, tmp_path, saved):
        blocked = json.dumps(
            {
                "key": f"{CHANNEL}_{VIDEO_BAD}_title_description",
                "response": {"candidates": [{"finishReason": "SAFETY"}]},
            }
        )
        lines = [blocked, _result_line("vid_json_01", "{not json"), _result_line("vid_list_01", "[1, 2]")]
        path = tmp_path / "results.jsonl"
        path.write_text("\n".join(lines) + "\n")

        stats, failed = import_results._process_result_file(str(path), "title_description", frozenset({CHANNEL}))

        assert stats["contentFailures"] == 3
        assert failed == [(CHANNEL, VIDEO_BAD), (CHANNEL, "vid_json_01"), (CHANNEL, "vid_list_01")]

    def test_save_failure_leaves_job_unimported_without_strikes(self, tmp_path, monkeypatch):
        store = FakeJobStore(monkeypatch, [_job(analysisType="title_description")])
        monkeypatch.setattr(
            import_results,
            "get_batch_job_status",
            lambda name: SimpleNamespace(state=SimpleNamespace(value="JOB_STATE_SUCCEEDED"), dest=None),
        )
        path = tmp_path / "results.jsonl"
        path.write_text(_result_line(VIDEO_OK, '{"x": 1}') + "\n" + _result_line(VIDEO_BAD, None) + "\n")
        monkeypatch.setattr(import_results, "_download_results", lambda job, record, atype: str(path))
        monkeypatch.setattr(import_results, "get_all_channels_unfiltered", lambda: [{"id": CHANNEL}])
        monkeypatch.setattr(
            import_results,
            "get_channel_video_texts",
            lambda ch: {VIDEO_OK: {"title": "t", "description": ""}, VIDEO_BAD: {"title": "t", "description": ""}},
        )

        def save_fails(*a):
            raise google_exceptions.ServiceUnavailable("firestore down")

        monkeypatch.setattr(import_results, "save_analysis", save_fails)
        monkeypatch.setattr(import_results, "record_batch_failures", lambda *a: pytest.fail("no strikes on retry path"))

        with pytest.raises(import_results.BatchImportError):
            import_results.import_batch_results("title_description")
        job = store.jobs["batches_1"]
        assert not job["importedAt"] and not job.get("abandonedAt")
        assert job["importStats"]["storeErrors"] == 1
        assert submit.find_blocking_job("title_description")[0] == "unimported"

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
        updates = []
        monkeypatch.setattr(import_results, "update_batch_job", lambda job_id, u: updates.append(u))
        monkeypatch.setattr(submit, "update_batch_job", lambda job_id, u: updates.append(u))

        with pytest.raises(import_results.BatchImportError):
            import_results.import_batch_results("thumbnail", job_name="batches/1")
        assert updates and all("importedAt" not in u for u in updates)
        assert updates[-1]["abandonedAt"]


class _Blocked:
    """Mimics a google-generativeai response whose candidate was blocked (response.text raises)."""

    prompt_feedback = None
    candidates = [SimpleNamespace(finish_reason="SAFETY")]

    @property
    def text(self):
        raise ValueError("The `response.text` quick accessor requires the response to contain a valid `Part`")


class TestGeminiErrorMapping:
    @pytest.fixture(autouse=True)
    def no_sleep(self, monkeypatch):
        monkeypatch.setattr(gemini_client.time, "sleep", lambda s: None)

    def test_blocked_candidate_is_response_error_without_retry(self):
        calls = []

        def generate():
            calls.append(1)
            return _Blocked()

        with pytest.raises(gemini_client.GeminiResponseError, match="SAFETY"):
            gemini_client._execute_with_retry(generate)
        assert len(calls) == 1

    def test_invalid_argument_is_response_error(self):
        def generate():
            raise google_exceptions.InvalidArgument("Unable to process input image")

        with pytest.raises(gemini_client.GeminiResponseError):
            gemini_client._execute_with_retry(generate)

    def test_invalid_api_key_stays_api_error(self):
        def generate():
            raise google_exceptions.InvalidArgument("API key not valid. Please pass a valid API key.")

        with pytest.raises(gemini_client.GeminiAPIError) as exc:
            gemini_client._execute_with_retry(generate)
        assert not isinstance(exc.value, gemini_client.GeminiResponseError)

    def test_transient_api_error_is_api_error(self):
        def generate():
            raise google_exceptions.ServiceUnavailable("overloaded")

        with pytest.raises(gemini_client.GeminiAPIError) as exc:
            gemini_client._execute_with_retry(generate)
        assert not isinstance(exc.value, gemini_client.GeminiResponseError)

    def test_valid_response_parses(self):
        ok = SimpleNamespace(prompt_feedback=None, text='{"a": 1}')
        assert gemini_client._execute_with_retry(lambda: ok) == {"a": 1}


class _FakeProgress:
    def __init__(self):
        self.failures = 0

    def start(self, n):
        pass

    def record_failure(self):
        self.failures += 1

    def record_success(self):
        pass

    def record_skip(self):
        pass

    def force_save(self):
        pass

    def get_stats(self):
        return {"processed": self.failures, "successful": 0, "failed": self.failures, "skipped": 0}


class TestSyncAbort:
    def _processor(self, monkeypatch, n_videos, error):
        monkeypatch.setattr(sync_batch.time, "sleep", lambda s: None)
        monkeypatch.setattr(
            sync_batch, "get_unanalyzed_videos_paginated", lambda ch, t, lim: [{"id": f"v{i}"} for i in range(n_videos)]
        )
        proc = object.__new__(sync_batch.BatchProcessor)
        proc.analysis_type = "thumbnail"
        proc.progress = _FakeProgress()

        def analyze(channel_id, video):
            raise error

        proc._analyze_video = analyze
        return proc

    def test_blocked_videos_do_not_abort_run(self, monkeypatch):
        def blocked():
            return _Blocked()

        monkeypatch.setattr(gemini_client.time, "sleep", lambda s: None)
        with pytest.raises(gemini_client.GeminiAPIError) as exc:
            gemini_client._execute_with_retry(blocked)
        proc = self._processor(monkeypatch, sync_batch.MAX_CONSECUTIVE_API_ERRORS * 2, exc.value)

        stats = proc.process_channel(CHANNEL)

        assert stats["failed"] == sync_batch.MAX_CONSECUTIVE_API_ERRORS * 2

    def test_consecutive_api_errors_still_abort(self, monkeypatch):
        proc = self._processor(monkeypatch, 10, gemini_client.GeminiAPIError("503 unavailable"))
        with pytest.raises(sync_batch.AnalysisAbortedError):
            proc.process_channel(CHANNEL)
