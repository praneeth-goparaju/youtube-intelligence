"""Tests for insights Config wiring to the shared base config.

These verify that insights' Config inherits from the shared BaseFirebaseConfig
(rather than re-declaring credential fields) and that initialize() still
populates every field with the expected values.
"""

from shared.config import BaseFirebaseConfig
from insights.src.config import Config, config


class TestInsightsConfigInheritance:
    def test_inherits_shared_base_config(self):
        assert issubclass(Config, BaseFirebaseConfig)

    def test_credential_fields_provided_by_base(self):
        # The credential fields are declared on the shared base class.
        assert "FIREBASE_PROJECT_ID" in BaseFirebaseConfig.__dict__
        assert "FIREBASE_PRIVATE_KEY" in BaseFirebaseConfig.__dict__


class TestInsightsConfigInitialize:
    def test_initialize_populates_credentials(self, monkeypatch):
        monkeypatch.setenv("FIREBASE_PROJECT_ID", "test-project")
        monkeypatch.setenv("FIREBASE_CLIENT_EMAIL", "test@test.iam.gserviceaccount.com")
        monkeypatch.setenv("FIREBASE_PRIVATE_KEY", "line1\\nline2")
        monkeypatch.setenv("FIREBASE_STORAGE_BUCKET", "test-bucket.appspot.com")

        config.initialize()

        assert config.FIREBASE_PROJECT_ID == "test-project"
        assert config.FIREBASE_CLIENT_EMAIL == "test@test.iam.gserviceaccount.com"
        assert config.FIREBASE_PRIVATE_KEY == "line1\nline2"  # newlines normalized
        assert config.FIREBASE_STORAGE_BUCKET == "test-bucket.appspot.com"
