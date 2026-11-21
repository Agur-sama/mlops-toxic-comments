from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

import joblib

from .settings import InferenceSettings


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


@dataclass(frozen=True)
class Prediction:
    toxic: bool
    label: str
    probability: float
    threshold: float


class ToxicityPredictor:
    """Immutable inference wrapper shared by all requests."""

    def __init__(self, settings: InferenceSettings):
        if not settings.model_path.is_file():
            raise RuntimeError(f"Model artifact not found: {settings.model_path}")
        if not settings.metadata_path.is_file():
            raise RuntimeError(f"Model metadata not found: {settings.metadata_path}")
        metadata = json.loads(settings.metadata_path.read_text(encoding="utf-8"))
        actual_checksum = sha256_file(settings.model_path)
        expected_checksum = str(metadata.get("artifact_sha256", ""))
        if actual_checksum != expected_checksum:
            raise RuntimeError(
                "Model checksum mismatch: "
                f"expected {expected_checksum}, got {actual_checksum}"
            )
        if metadata.get("model_version") != settings.model_version:
            raise RuntimeError("Configured model version does not match artifact metadata")
        self._model = joblib.load(settings.model_path)
        self.model_version = settings.model_version
        self.model_sha256 = actual_checksum
        self.data_version = str(metadata["data_version"])
        self.threshold = float(settings.threshold)

    def predict(self, text: str) -> Prediction:
        probability = float(self._model.predict_proba([text])[0, 1])
        toxic = probability >= self.threshold
        return Prediction(
            toxic=toxic,
            label="toxic" if toxic else "non_toxic",
            probability=probability,
            threshold=self.threshold,
        )
