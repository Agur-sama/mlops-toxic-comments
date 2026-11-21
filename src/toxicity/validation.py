from __future__ import annotations

import ast
import json
from pathlib import Path

REQUIRED = [
    "main.py",
    "README.md",
    "requirements.txt",
    "config/default.yaml",
    "src/toxicity/data.py",
    "src/toxicity/preprocessing.py",
    "src/toxicity/classical.py",
    "src/toxicity/bert.py",
    "src/toxicity/eda.py",
    "src/toxicity/report.py",
]


def validate_project(root: Path) -> None:
    missing = [item for item in REQUIRED if not (root / item).exists()]
    if missing:
        raise FileNotFoundError(f"Missing required project files: {missing}")
    parsed = []
    for path in sorted(root.rglob("*.py")):
        if ".venv" in path.parts:
            continue
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        parsed.append(str(path.relative_to(root)))
    report = {"status": "ok", "python_files_parsed": parsed, "count": len(parsed)}
    out = root / "artifacts/results/validation.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Validated {len(parsed)} Python files")

