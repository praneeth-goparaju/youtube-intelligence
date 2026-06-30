"""Configuration for insights module."""

import sys
from pathlib import Path

# Add shared module to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.config import load_env_file, BaseFirebaseConfig

# Load .env from project root
PROJECT_ROOT = load_env_file(__file__)


class Config(BaseFirebaseConfig):
    """Application configuration. Firebase credentials are loaded lazily.

    The FIREBASE_* credential fields and the logic that loads them are inherited
    from shared.config.BaseFirebaseConfig, so they live in exactly one place
    across all phases.
    """

    # Paths (always available)
    PROJECT_ROOT: Path = PROJECT_ROOT
    OUTPUTS_DIR: Path = Path(__file__).parent.parent / "outputs"

    def initialize(self) -> None:
        """Load Firebase credentials from environment. Call before using Firebase."""
        self.load_firebase_config()


config = Config()

# Ensure outputs directory exists
config.OUTPUTS_DIR.mkdir(exist_ok=True)
