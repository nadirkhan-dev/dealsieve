import os
import sys
from pathlib import Path

os.environ["DATABASE_URL"] = "sqlite:///./test_dealsieve.db"
os.environ["DEMO_MODE"] = "true"
os.environ.pop("ANTHROPIC_API_KEY", None)
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
