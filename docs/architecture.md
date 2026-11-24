# Архитектура

## ML pipeline и inference

```mermaid
flowchart LR
    K[Kaggle Jigsaw] -->|download| R[data/raw]
    R -->|DVC prepare| S[Stratified split 70/15/15]
    S --> V1[jigsaw-minimal-v1]
    S --> V2[jigsaw-standard-v2]
    V1 --> E1[BoW + NB]
    V1 --> E2[TF-IDF + LR]
    V2 --> E3[TF-IDF + LR]
    E1 --> M[MLflow]
    E2 --> M
    E3 --> M
    M -->|max validation F1| A[Versioned joblib]
    A -->|SHA-256 + metadata| API[FastAPI]
    API --> H[GET /health]
    API --> P[POST /predict]
    API --> O[OpenAPI /docs]
    API --> PM[Prometheus /metrics]
    UI[Streamlit] -->|HTTP| P
```

DVC фиксирует source, split, preprocessing manifests и реестр MLflow runs. Модель загружается один раз при lifespan startup API. До deserialization проверяются metadata, SHA-256 и model version. Sklearn Pipeline включает preprocessing, vectorizer и classifier, поэтому HTTP-слой не дублирует преобразования.

## CI

```mermaid
flowchart LR
    G[Push / PR / v* tag] --> Q[Locked install]
    Q --> L[Ruff]
    L --> T[Pytest + coverage >= 80%]
    T --> AR[JUnit + coverage artifacts]
    T --> B[Build API + UI images]
    B --> C[Run Compose stack]
    C --> SM[API + UI + UI-to-API smoke]
    SM --> CL[Always cleanup]
    SM -->|v* only| GHCR[Publish API + UI: tag + SHA]
```

Jobs `image` и `publish` зависят от успешного `quality`. GitHub token выдаётся
CI и не хранится в репозитории. `concurrency` привязан к PR number или ref, что
исключает дубли.
