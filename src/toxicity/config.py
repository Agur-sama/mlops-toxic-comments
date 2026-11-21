from __future__ import annotations

import json
import os
import platform
import random
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class ProjectPaths:
    root: Path
    raw_dir: Path
    processed_dir: Path
    figures_dir: Path
    results_dir: Path
    models_dir: Path
    predictions_dir: Path
    report_dir: Path

    def ensure(self) -> None:
        for path in (
            self.raw_dir,
            self.processed_dir,
            self.figures_dir,
            self.results_dir,
            self.models_dir,
            self.predictions_dir,
            self.report_dir,
        ):
            path.mkdir(parents=True, exist_ok=True)


def load_config(path: str | Path = ROOT / "config/default.yaml") -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as fh:
        config = yaml.safe_load(fh)
    config["_config_path"] = str(Path(path).resolve())
    return config


def get_paths(config: dict[str, Any]) -> ProjectPaths:
    values = {name: ROOT / rel for name, rel in config["paths"].items()}
    paths = ProjectPaths(root=ROOT, **values)
    paths.ensure()
    return paths


def set_global_seed(seed: int = 42) -> None:
    os.environ["PYTHONHASHSEED"] = str(seed)
    random.seed(seed)
    np.random.seed(seed)
    try:
        import torch

        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            torch.mps.manual_seed(seed)
    except ImportError:
        pass


def save_environment(path: Path) -> None:
    packages: dict[str, str] = {}
    for module_name in (
        "pandas",
        "numpy",
        "scipy",
        "sklearn",
        "matplotlib",
        "seaborn",
        "nltk",
        "torch",
        "transformers",
        "datasets",
        "accelerate",
    ):
        try:
            module = __import__(module_name)
            packages[module_name] = getattr(module, "__version__", "unknown")
        except ImportError:
            packages[module_name] = "not installed"
    payload = {
        "python": sys.version,
        "platform": platform.platform(),
        "processor": platform.processor(),
        "packages": packages,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

