"""Configuration for recommender module."""

import sys
from pathlib import Path

# Add shared module to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.config import load_env_file, get_env
from shared.constants import GEMINI_MODEL

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

    # Paths
    PROJECT_ROOT: Path = PROJECT_ROOT


config = Config()
