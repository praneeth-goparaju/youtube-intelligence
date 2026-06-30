"""Configuration management for the analyzer."""

import os
import sys
import logging
from pathlib import Path

# Add shared module to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.config import load_env_file, get_env, BaseGeminiConfig
from shared.constants import GEMINI_MODEL


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    """Set up logging for the analyzer module.

    Args:
        level: Logging level (default: INFO)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger("analyzer")

    # Avoid adding handlers multiple times
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    logger.setLevel(level)
    return logger


# Initialize logger
logger = setup_logging()

# Load .env from project root
PROJECT_ROOT = load_env_file(__file__)


class Config(BaseGeminiConfig):
    """Application configuration. Loaded lazily via load() to support test fixtures.

    The Firebase + Gemini credential fields (FIREBASE_*, GOOGLE_API_KEY) and the
    logic that loads them are inherited from shared.config.BaseGeminiConfig, so
    they are defined in exactly one place across all phases.
    """

    _loaded: bool = False

    # Gemini model selection (semantic config, not a credential)
    GEMINI_MODEL: str = GEMINI_MODEL  # Use shared constant

    # Processing settings
    BATCH_SIZE: int = 10
    MAX_RETRIES: int = 3
    RETRY_DELAY: float = 1.0
    REQUEST_DELAY: float = 0.5  # Delay between API requests

    # Batch API settings
    GCS_BUCKET_URI: str = ""
    BATCH_POLL_INTERVAL: int = 60
    BATCH_MAX_REQUESTS: int = 680  # Tier 1 enqueued token limit (~3M / ~4.4K tokens per request)

    # Paths
    PROJECT_ROOT: Path = PROJECT_ROOT

    @classmethod
    def load(cls) -> None:
        """Load configuration from environment variables."""
        if cls._loaded:
            return

        # Loads GOOGLE_API_KEY and all FIREBASE_* fields (private-key newlines
        # normalized) from the shared base config.
        cls.load_gemini_config()
        cls.BATCH_SIZE = int(get_env("BATCH_SIZE", False, "10"))
        cls.GCS_BUCKET_URI = f"gs://{cls.FIREBASE_STORAGE_BUCKET}"
        cls.BATCH_POLL_INTERVAL = int(get_env("BATCH_POLL_INTERVAL", False, "60"))
        cls._loaded = True


def validate_config() -> bool:
    """Validate all required configuration is present."""
    required = [
        "GOOGLE_API_KEY",
        "FIREBASE_PROJECT_ID",
        "FIREBASE_CLIENT_EMAIL",
        "FIREBASE_PRIVATE_KEY",
        "FIREBASE_STORAGE_BUCKET",
    ]

    missing = [var for var in required if not os.getenv(var)]

    if missing:
        logger.error("Missing required environment variables:")
        for var in missing:
            logger.error(f"  - {var}")
        return False

    return True


config = Config()
