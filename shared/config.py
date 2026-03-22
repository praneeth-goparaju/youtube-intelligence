"""Shared configuration utilities for YouTube Intelligence System.

This module provides common configuration loading patterns used across all phases.
"""

import os
from pathlib import Path
from dotenv import load_dotenv


def load_env_file(module_path: str) -> Path:
    """Load .env file from project root.

    Args:
        module_path: __file__ from the calling module

    Returns:
        Path to the project root
    """
    # Navigate up to project root (assuming module is at phase/src/config.py)
    project_root = Path(module_path).parent.parent.parent
    env_path = project_root / ".env"
    load_dotenv(env_path)
    return project_root


def get_env(name: str, required: bool = True, default: str = "") -> str:
    """Get environment variable with optional requirement check.

    Args:
        name: Environment variable name
        required: Whether the variable is required
        default: Default value if not required and not set

    Returns:
        The environment variable value

    Raises:
        ValueError: If required variable is missing
    """
    value = os.getenv(name, default)
    if required and not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value


class BaseFirebaseConfig:
    """Base configuration with Firebase credentials.

    All phases that use Firebase should inherit from this.
    """

    FIREBASE_PROJECT_ID: str = ""
    FIREBASE_CLIENT_EMAIL: str = ""
    FIREBASE_PRIVATE_KEY: str = ""
    FIREBASE_STORAGE_BUCKET: str = ""

    @classmethod
    def load_firebase_config(cls) -> None:
        """Load Firebase configuration from environment."""
        cls.FIREBASE_PROJECT_ID = get_env("FIREBASE_PROJECT_ID")
        cls.FIREBASE_CLIENT_EMAIL = get_env("FIREBASE_CLIENT_EMAIL")
        cls.FIREBASE_PRIVATE_KEY = get_env("FIREBASE_PRIVATE_KEY").replace("\\n", "\n")
        cls.FIREBASE_STORAGE_BUCKET = get_env("FIREBASE_STORAGE_BUCKET")


class BaseGeminiConfig(BaseFirebaseConfig):
    """Base configuration with Firebase and Gemini credentials.

    Phases that use Gemini API should inherit from this.
    """

    GOOGLE_API_KEY: str = ""

    @classmethod
    def load_gemini_config(cls) -> None:
        """Load Gemini configuration from environment."""
        cls.load_firebase_config()
        cls.GOOGLE_API_KEY = get_env("GOOGLE_API_KEY")
