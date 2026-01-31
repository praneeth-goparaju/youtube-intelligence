"""Test configuration for insights tests."""

import sys
from pathlib import Path

# Add project root to path so imports work
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
