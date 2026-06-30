"""Tests for analyzer Config wiring to the shared base config.

These verify that analyzer's Config actually inherits from the shared
BaseGeminiConfig (rather than re-declaring credential fields) and that loading
still populates every field with the expected values.
"""

# Import src.config first: importing it inserts the project root onto sys.path,
# which makes the top-level `shared` package importable below.
from src.config import Config
from shared.config import BaseGeminiConfig, BaseFirebaseConfig


def _fresh_load():
    """Force a reload under the current (mocked) environment."""
    Config._loaded = False
    Config.load()


class TestAnalyzerConfigInheritance:
    def test_inherits_shared_base_config(self):
        assert issubclass(Config, BaseGeminiConfig)
        assert issubclass(Config, BaseFirebaseConfig)

    def test_credential_fields_provided_by_base(self):
        # The credential fields are declared on the shared base classes, so the
        # single source of truth lives there rather than in each phase.
        assert "GOOGLE_API_KEY" in BaseGeminiConfig.__dict__
        assert "FIREBASE_PROJECT_ID" in BaseFirebaseConfig.__dict__


class TestAnalyzerConfigLoad:
    def test_load_populates_inherited_credentials(self):
        _fresh_load()
        assert Config.GOOGLE_API_KEY == "test-api-key"
        assert Config.FIREBASE_PROJECT_ID == "test-project"
        assert Config.FIREBASE_CLIENT_EMAIL == "test@test.iam.gserviceaccount.com"
        assert Config.FIREBASE_STORAGE_BUCKET == "test-bucket.appspot.com"

    def test_load_sets_analyzer_specific_fields(self):
        _fresh_load()
        assert Config.GCS_BUCKET_URI == "gs://test-bucket.appspot.com"
        assert Config.GEMINI_MODEL  # populated from the shared constant
        assert Config.BATCH_POLL_INTERVAL == 60

    def test_private_key_newlines_are_normalized(self, monkeypatch):
        monkeypatch.setenv("FIREBASE_PRIVATE_KEY", "line1\\nline2")
        _fresh_load()
        assert Config.FIREBASE_PRIVATE_KEY == "line1\nline2"

    def test_load_is_idempotent(self, monkeypatch):
        _fresh_load()
        # Once loaded, a later env change is ignored until _loaded is reset.
        monkeypatch.setenv("FIREBASE_PROJECT_ID", "changed-project")
        Config.load()
        assert Config.FIREBASE_PROJECT_ID == "test-project"
