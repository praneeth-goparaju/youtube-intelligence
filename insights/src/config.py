"""Configuration for insights module."""

import sys
from pathlib import Path

# Add shared module to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.config import load_env_file, get_env

# Load .env from project root
PROJECT_ROOT = load_env_file(__file__)


class Config:
    """Application configuration."""

    # Firebase
    FIREBASE_PROJECT_ID: str = get_env('FIREBASE_PROJECT_ID')
    FIREBASE_CLIENT_EMAIL: str = get_env('FIREBASE_CLIENT_EMAIL')
    FIREBASE_PRIVATE_KEY: str = get_env('FIREBASE_PRIVATE_KEY').replace('\\n', '\n')
    FIREBASE_STORAGE_BUCKET: str = get_env('FIREBASE_STORAGE_BUCKET')

    # Paths
    PROJECT_ROOT: Path = PROJECT_ROOT
    OUTPUTS_DIR: Path = Path(__file__).parent.parent / 'outputs'

    # Analysis settings
    MIN_VIDEOS_FOR_CORRELATION: int = 50
    PERCENTILE_THRESHOLDS: list = [10, 25, 50, 75, 90, 95]


config = Config()

# Ensure outputs directory exists
config.OUTPUTS_DIR.mkdir(exist_ok=True)
