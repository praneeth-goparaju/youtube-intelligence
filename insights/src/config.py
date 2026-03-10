"""Configuration for insights module."""

import sys
from pathlib import Path

# Add shared module to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.config import load_env_file, get_env

# Load .env from project root
PROJECT_ROOT = load_env_file(__file__)


class Config:
    """Application configuration. Firebase credentials are loaded lazily."""

    # Paths (always available)
    PROJECT_ROOT: Path = PROJECT_ROOT
    OUTPUTS_DIR: Path = Path(__file__).parent.parent / 'outputs'

    # Firebase (populated by initialize())
    FIREBASE_PROJECT_ID: str = ''
    FIREBASE_CLIENT_EMAIL: str = ''
    FIREBASE_PRIVATE_KEY: str = ''
    FIREBASE_STORAGE_BUCKET: str = ''

    def initialize(self) -> None:
        """Load Firebase credentials from environment. Call before using Firebase."""
        self.FIREBASE_PROJECT_ID = get_env('FIREBASE_PROJECT_ID')
        self.FIREBASE_CLIENT_EMAIL = get_env('FIREBASE_CLIENT_EMAIL')
        self.FIREBASE_PRIVATE_KEY = get_env('FIREBASE_PRIVATE_KEY').replace('\\n', '\n')
        self.FIREBASE_STORAGE_BUCKET = get_env('FIREBASE_STORAGE_BUCKET')


config = Config()

# Ensure outputs directory exists
config.OUTPUTS_DIR.mkdir(exist_ok=True)
