from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]


def _resolve(path: str | Path) -> Path:
    value = Path(path)
    return value if value.is_absolute() else ROOT / value


@dataclass(frozen=True)
class InferenceSettings:
    model_path: Path
    metadata_path: Path
    model_version: str
    threshold: float
    max_text_length: int
    host: str
    port: int
    log_level: str

    @classmethod
    def load(cls, config_path: str | Path | None = None) -> InferenceSettings:
        selected = config_path or os.getenv("TOXICITY_CONFIG_PATH", "config/default.yaml")
        resolved_config = _resolve(selected)
        if not resolved_config.is_file():
            raise RuntimeError(f"Configuration file not found: {resolved_config}")
        with resolved_config.open("r", encoding="utf-8") as handle:
            raw: dict[str, Any] = yaml.safe_load(handle) or {}
        section = raw.get("inference")
        if not isinstance(section, dict):
            raise RuntimeError("Configuration must contain an 'inference' section")

        model_path = _resolve(os.getenv("TOXICITY_MODEL_PATH", section.get("model_path", "")))
        metadata_path = _resolve(
            os.getenv("TOXICITY_METADATA_PATH", section.get("metadata_path", ""))
        )
        version = str(section.get("model_version", "")).strip()
        if not version:
            raise RuntimeError("inference.model_version is required")
        threshold = float(section.get("threshold", 0.5))
        if not 0.0 <= threshold <= 1.0:
            raise RuntimeError("inference.threshold must be between 0 and 1")
        max_length = int(section.get("max_text_length", 5000))
        if max_length < 1:
            raise RuntimeError("inference.max_text_length must be positive")
        return cls(
            model_path=model_path,
            metadata_path=metadata_path,
            model_version=version,
            threshold=threshold,
            max_text_length=max_length,
            host=str(section.get("host", "0.0.0.0")),
            port=int(section.get("port", 8000)),
            log_level=os.getenv("TOXICITY_LOG_LEVEL", "INFO").upper(),
        )
