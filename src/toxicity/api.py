from __future__ import annotations

import time
from contextlib import asynccontextmanager
from typing import Annotated, Literal

from fastapi import FastAPI, HTTPException, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from pydantic import BaseModel, Field, StringConstraints, field_validator

from .inference import ToxicityPredictor
from .settings import InferenceSettings

REQUESTS = Counter(
    "toxicity_api_requests_total",
    "Number of API requests",
    labelnames=("endpoint", "status"),
)
LATENCY = Histogram(
    "toxicity_prediction_latency_seconds",
    "Prediction latency in seconds",
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0),
)


class HealthResponse(BaseModel):
    status: Literal["ready"]
    model_version: str
    model_sha256: str
    data_version: str


class PredictRequest(BaseModel):
    text: Annotated[str, StringConstraints(min_length=1, max_length=5000)] = Field(
        examples=["Thank you for the clear explanation!"]
    )

    @field_validator("text")
    @classmethod
    def reject_blank_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("text must contain at least one non-whitespace character")
        return value


class PredictResponse(BaseModel):
    toxic: bool
    label: Literal["toxic", "non_toxic"]
    probability: float = Field(ge=0.0, le=1.0)
    threshold: float = Field(ge=0.0, le=1.0)
    model_version: str
    data_version: str
    latency_ms: float = Field(ge=0.0)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = InferenceSettings.load()
    app.state.predictor = ToxicityPredictor(settings)
    app.state.settings = settings
    yield


app = FastAPI(
    title="Toxic Comment Classifier",
    version="1.0.0",
    description="Versioned inference API for binary toxic-comment classification.",
    lifespan=lifespan,
)


def _predictor(request: Request) -> ToxicityPredictor:
    predictor = getattr(request.app.state, "predictor", None)
    if predictor is None:
        raise HTTPException(status_code=503, detail="Model is not ready")
    return predictor


@app.get("/health", response_model=HealthResponse, tags=["operations"])
def health(request: Request) -> HealthResponse:
    predictor = _predictor(request)
    REQUESTS.labels(endpoint="health", status="200").inc()
    return HealthResponse(
        status="ready",
        model_version=predictor.model_version,
        model_sha256=predictor.model_sha256,
        data_version=predictor.data_version,
    )


@app.post("/predict", response_model=PredictResponse, tags=["inference"])
def predict(payload: PredictRequest, request: Request) -> PredictResponse:
    predictor = _predictor(request)
    started = time.perf_counter()
    with LATENCY.time():
        result = predictor.predict(payload.text)
    elapsed_ms = (time.perf_counter() - started) * 1000.0
    REQUESTS.labels(endpoint="predict", status="200").inc()
    return PredictResponse(
        toxic=result.toxic,
        label=result.label,
        probability=result.probability,
        threshold=result.threshold,
        model_version=predictor.model_version,
        data_version=predictor.data_version,
        latency_ms=elapsed_ms,
    )


@app.get("/metrics", include_in_schema=False, tags=["operations"])
def metrics() -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
