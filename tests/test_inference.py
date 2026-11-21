from __future__ import annotations

import hashlib
import json

import pytest

from toxicity.inference import ToxicityPredictor, sha256_file
from toxicity.preprocessing import get_preprocessor, minimal_clean, standard_clean
from toxicity.settings import InferenceSettings


def test_standard_preprocessing_is_deterministic() -> None:
    raw = "<b>Hello</b>   WORLD! Visit https://example.org"
    assert standard_clean(raw) == "hello world ! visit url"
    assert standard_clean(raw) == standard_clean(raw)


def test_minimal_preprocessing_and_lookup() -> None:
    assert minimal_clean("  hello\x00   world  ") == "hello world"
    assert get_preprocessor("standard") is standard_clean
    with pytest.raises(ValueError, match="Unknown preprocessing"):
        get_preprocessor("does-not-exist")


def test_predictor_is_stateless() -> None:
    predictor = ToxicityPredictor(InferenceSettings.load())
    first = predictor.predict("Thank you for helping")
    predictor.predict("You are an idiot")
    repeated = predictor.predict("Thank you for helping")
    assert first == repeated


def test_bad_checksum_fails_fast(tmp_path) -> None:
    settings = InferenceSettings.load()
    fake_metadata = tmp_path / "metadata.json"
    payload = json.loads(settings.metadata_path.read_text(encoding="utf-8"))
    payload["artifact_sha256"] = hashlib.sha256(b"wrong").hexdigest()
    fake_metadata.write_text(json.dumps(payload), encoding="utf-8")
    broken = InferenceSettings(
        model_path=settings.model_path,
        metadata_path=fake_metadata,
        model_version=settings.model_version,
        threshold=settings.threshold,
        max_text_length=settings.max_text_length,
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level,
    )
    with pytest.raises(RuntimeError, match="checksum mismatch"):
        ToxicityPredictor(broken)


def test_model_checksum_matches_metadata() -> None:
    settings = InferenceSettings.load()
    metadata = json.loads(settings.metadata_path.read_text(encoding="utf-8"))
    assert sha256_file(settings.model_path) == metadata["artifact_sha256"]


def test_missing_model_and_metadata_fail_fast(tmp_path) -> None:
    settings = InferenceSettings.load()
    missing_model = InferenceSettings(
        **{**settings.__dict__, "model_path": tmp_path / "missing.joblib"}
    )
    with pytest.raises(RuntimeError, match="Model artifact not found"):
        ToxicityPredictor(missing_model)
    missing_metadata = InferenceSettings(
        **{**settings.__dict__, "metadata_path": tmp_path / "missing.json"}
    )
    with pytest.raises(RuntimeError, match="Model metadata not found"):
        ToxicityPredictor(missing_metadata)


def test_settings_validation_errors(tmp_path, monkeypatch) -> None:
    missing = tmp_path / "absent.yaml"
    with pytest.raises(RuntimeError, match="Configuration file not found"):
        InferenceSettings.load(missing)

    invalid = tmp_path / "invalid.yaml"
    invalid.write_text("project: {}\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="inference.*section"):
        InferenceSettings.load(invalid)

    invalid.write_text("inference:\n  threshold: 2\n  model_version: v1\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="threshold"):
        InferenceSettings.load(invalid)

    invalid.write_text(
        "inference:\n  threshold: 0.5\n  model_version: v1\n  max_text_length: 0\n",
        encoding="utf-8",
    )
    with pytest.raises(RuntimeError, match="max_text_length"):
        InferenceSettings.load(invalid)
