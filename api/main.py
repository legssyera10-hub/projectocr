import os
import sys
from pathlib import Path

# Ensure project root is in the import path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from main import app  # FastAPI application
