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
