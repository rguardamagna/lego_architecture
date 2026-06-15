"""Test configuration for gateway tests."""
import sys
from pathlib import Path

# Ensure gateway package is importable
_gateway_dir = Path(__file__).resolve().parent.parent
if str(_gateway_dir) not in sys.path:
    sys.path.insert(0, str(_gateway_dir))
