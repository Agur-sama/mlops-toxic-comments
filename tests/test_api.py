from __future__ import annotations

from fastapi.testclient import TestClient

from toxicity.api import app


def test_health_reports_loaded_model() -> None:
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body["model_version"] == "toxicity-tfidf-logreg-v1.0.0"
    assert len(body["model_sha256"]) == 64


def test_predict_has_stable_contract() -> None:
    with TestClient(app) as client:
        response = client.post("/predict", json={"text": "You are a disgusting idiot"})
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {
        "toxic",
        "label",
        "probability",
        "threshold",
        "model_version",
        "data_version",
        "latency_ms",
    }
    assert body["toxic"] is True
    assert body["label"] == "toxic"
    assert 0.0 <= body["probability"] <= 1.0


def test_predict_rejects_blank_text() -> None:
    with TestClient(app) as client:
        response = client.post("/predict", json={"text": "   "})
    assert response.status_code == 422
    assert "non-whitespace" in response.text


def test_predict_rejects_missing_field() -> None:
    with TestClient(app) as client:
        response = client.post("/predict", json={})
    assert response.status_code == 422


def test_openapi_exposes_required_routes() -> None:
    with TestClient(app) as client:
        schema = client.get("/openapi.json").json()
        docs = client.get("/docs")
    assert docs.status_code == 200
    assert "/health" in schema["paths"]
    assert "/predict" in schema["paths"]


def test_metrics_endpoint_is_machine_readable() -> None:
    with TestClient(app) as client:
        response = client.get("/metrics")
    assert response.status_code == 200
    assert "toxicity_api_requests_total" in response.text
