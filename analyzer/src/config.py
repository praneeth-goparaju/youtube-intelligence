"""Configuration management for the analyzer."""

import os
import sys
import logging
from pathlib import Path

# Add shared module to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.config import load_env_file, get_env
from shared.constants import GEMINI_MODEL


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    """Set up logging for the analyzer module.

    Args:
        level: Logging level (default: INFO)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger('analyzer')

    # Avoid adding handlers multiple times
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    logger.setLevel(level)
    return logger


# Initialize logger
logger = setup_logging()

# Load .env from project root
PROJECT_ROOT = load_env_file(__file__)


class Config:
    """Application configuration."""

    # Google Gemini API
    GOOGLE_API_KEY: str = get_env('GOOGLE_API_KEY')
    GEMINI_MODEL: str = GEMINI_MODEL  # Use shared constant

    # Firebase
    FIREBASE_PROJECT_ID: str = get_env('FIREBASE_PROJECT_ID')
    FIREBASE_CLIENT_EMAIL: str = get_env('FIREBASE_CLIENT_EMAIL')
    FIREBASE_PRIVATE_KEY: str = get_env('FIREBASE_PRIVATE_KEY').replace('\\n', '\n')
    FIREBASE_STORAGE_BUCKET: str = get_env('FIREBASE_STORAGE_BUCKET')

    # Processing settings
    BATCH_SIZE: int = int(get_env('BATCH_SIZE', False, '10'))
    MAX_RETRIES: int = 3
    RETRY_DELAY: float = 1.0
    REQUEST_DELAY: float = 0.5  # Delay between API requests

    # Batch API settings
    GCS_BUCKET_URI: str = f"gs://{get_env('FIREBASE_STORAGE_BUCKET')}"
    BATCH_POLL_INTERVAL: int = int(get_env('BATCH_POLL_INTERVAL', False, '60'))
    BATCH_MAX_REQUESTS: int = 50000  # Gemini Batch API limit per job

    # Paths
    PROJECT_ROOT: Path = PROJECT_ROOT


def validate_config() -> bool:
    """Validate all required configuration is present."""
    required = [
        'GOOGLE_API_KEY',
        'FIREBASE_PROJECT_ID',
        'FIREBASE_CLIENT_EMAIL',
        'FIREBASE_PRIVATE_KEY',
        'FIREBASE_STORAGE_BUCKET',
    ]

    missing = [var for var in required if not os.getenv(var)]

    if missing:
        logger.error("Missing required environment variables:")
        for var in missing:
            logger.error(f"  - {var}")
        return False

    return True


config = Config()
