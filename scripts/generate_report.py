from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
raise SystemExit(subprocess.call([sys.executable, str(ROOT / "main.py"), "report", *sys.argv[1:]], cwd=ROOT))

