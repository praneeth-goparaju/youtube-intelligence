"""Exercise the installed GenAI SDK through an offline HTTP transport."""

import json

import httpx
from google import genai
from google.genai import types

from analyzer.src.batch_api import client


def test_batch_file_lifecycle_uses_real_sdk_serialization(monkeypatch, tmp_path):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    source = b'{"key":"request-1","request":{"contents":[]}}\n'
    results = b'{"key":"request-1","response":{"candidates":[]}}\n'
    input_path = tmp_path / "requests.jsonl"
    input_path.write_bytes(source)
    output_path = tmp_path / "results.jsonl"
    requests = []
    completed_job = {
        "name": "batches/job-1",
        "metadata": {
            "state": "BATCH_STATE_SUCCEEDED",
            "model": "models/gemini-2.5-flash",
            "output": {"responsesFile": "files/results"},
        },
    }

    def handle(request):
        requests.append(request)
        path = request.url.path
        if request.method == "POST" and path == "/upload/v1beta/files":
            assert request.headers["x-goog-upload-header-content-type"] == "application/jsonl"
            file_metadata = json.loads(request.content)["file"]
            assert file_metadata.get("displayName", file_metadata.get("display_name")) == "Batch requests"
            return httpx.Response(200, json={}, headers={"x-goog-upload-url": "https://batch.invalid/upload-session"})
        if request.method == "POST" and path == "/upload-session":
            assert request.content == source
            assert request.headers["x-goog-upload-command"] == "upload, finalize"
            return httpx.Response(
                200,
                json={"file": {"name": "files/requests", "mimeType": "application/jsonl", "state": "ACTIVE"}},
                headers={"x-goog-upload-status": "final"},
            )
        if request.method == "POST" and path == "/v1beta/models/gemini-2.5-flash:batchGenerateContent":
            assert json.loads(request.content) == {"batch": {"inputConfig": {"fileName": "files/requests"}}}
            return httpx.Response(200, json={"name": "batches/job-1", "metadata": {"state": "BATCH_STATE_PENDING"}})
        if request.method == "GET" and path == "/v1beta/batches/job-1":
            return httpx.Response(200, json=completed_job)
        if request.method == "GET" and path == "/v1beta/batches":
            assert request.url.params["pageSize"] == "2"
            if request.url.params.get("pageToken") == "next-page":
                return httpx.Response(
                    200, json={"operations": [{"name": "batches/job-2", "metadata": {"state": "BATCH_STATE_FAILED"}}]}
                )
            return httpx.Response(200, json={"operations": [completed_job], "nextPageToken": "next-page"})
        if request.method == "GET" and path == "/v1beta/files/results:download":
            assert request.url.params["alt"] == "media"
            return httpx.Response(200, content=results)
        if request.method == "DELETE" and path == "/v1beta/batches/job-1":
            return httpx.Response(200, json={})
        raise AssertionError(f"Unexpected HTTP request: {request.method} {request.url}")

    with httpx.Client(transport=httpx.MockTransport(handle), trust_env=False) as http_client:
        with genai.Client(
            api_key="offline-test-key",
            vertexai=False,
            http_options=types.HttpOptions(
                base_url="https://batch.invalid",
                httpx_client=http_client,
                retry_options=types.HttpRetryOptions(attempts=1),
            ),
        ) as sdk:
            monkeypatch.setattr(client, "_client", sdk)
            uploaded = client.upload_jsonl_file(str(input_path), "Batch requests")
            assert uploaded == "files/requests"

            created = client.create_batch_job("gemini-2.5-flash", uploaded)
            assert client._state_str(created.state) == "JOB_STATE_PENDING"

            completed = client.get_batch_job(created.name)
            assert client._state_str(completed.state) == "JOB_STATE_SUCCEEDED"
            assert completed.dest.file_name == "files/results"

            jobs = client.list_batch_jobs(limit=2)
            assert [job.name for job in jobs] == ["batches/job-1", "batches/job-2"]
            assert [client._state_str(job.state) for job in jobs] == ["JOB_STATE_SUCCEEDED", "JOB_STATE_FAILED"]

            assert client.download_result_file(completed.dest.file_name, str(output_path)) == str(output_path)
            assert output_path.read_bytes() == results
            client.delete_batch_job(created.name)

    assert len(requests) == 8


def test_expired_batch_stops_polling_immediately(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    requests = []

    def handle(request):
        requests.append(request)
        assert request.method == "GET"
        assert request.url.path == "/v1beta/batches/expired"
        return httpx.Response(200, json={"name": "batches/expired", "metadata": {"state": "BATCH_STATE_EXPIRED"}})

    with httpx.Client(transport=httpx.MockTransport(handle), trust_env=False) as http_client:
        with genai.Client(
            api_key="offline-test-key",
            vertexai=False,
            http_options=types.HttpOptions(base_url="https://batch.invalid", httpx_client=http_client),
        ) as sdk:
            monkeypatch.setattr(client, "_client", sdk)
            job = client.poll_batch_job("batches/expired", poll_interval=0, max_polls=2)

    assert client._state_str(job.state) == "JOB_STATE_EXPIRED"
    assert len(requests) == 1
