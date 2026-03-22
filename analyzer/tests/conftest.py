"""Pytest configuration and fixtures."""

import pytest


@pytest.fixture(autouse=True)
def mock_env(monkeypatch):
    """Set up mock environment variables for testing."""
    monkeypatch.setenv("GOOGLE_API_KEY", "test-api-key")
    monkeypatch.setenv("FIREBASE_PROJECT_ID", "test-project")
    monkeypatch.setenv("FIREBASE_CLIENT_EMAIL", "test@test.iam.gserviceaccount.com")
    monkeypatch.setenv("FIREBASE_PRIVATE_KEY", "-----BEGIN PRIVATE KEY-----\nTEST\n-----END PRIVATE KEY-----")
    monkeypatch.setenv("FIREBASE_STORAGE_BUCKET", "test-bucket.appspot.com")
