# Структура проекта

## Корневые файлы

- `README.md` — установка, запуск, данные, эксперименты, API, Docker и CI.
- `pyproject.toml` — поддерживаемый Python, настройки pytest, coverage и Ruff.
- `requirements-*.lock` — точные версии и SHA-256 зависимостей для runtime,
  разработки, обучения и UI.
- `config/default.yaml` — train/inference-конфигурация, split и параметры модели.
- `dvc.yaml`, `dvc.lock` — команды, зависимости и checksums DVC pipeline.
- `Dockerfile` — non-root FastAPI image.
- `Dockerfile.ui` — non-root Streamlit image.
- `docker-compose.yml` — совместный запуск API и UI с healthchecks.
- `.github/workflows/ci.yml` — lint, tests, coverage, Docker smoke и GHCR.
- `MODEL_CARD.md`, `DATASET_CARD.md` — назначение, метрики, происхождение и
  ограничения.
- `REPORT.md`, `AUDIT_MLOPS.md` — соответствие рубрике и независимый аудит.

## Код

- `src/toxicity/config.py` — чтение YAML, env overrides и fail-fast validation.
- `src/toxicity/preprocessing.py` — минимальный и standard preprocessing.
- `src/toxicity/data.py` — чтение Jigsaw и стратифицированный split 70/15/15.
- `src/toxicity/training.py` — sklearn Pipeline, обучение и метрики.
- `src/toxicity/tracking.py` — запись params, metrics, tags и artifacts в MLflow.
- `src/toxicity/inference.py` — проверка SHA модели и неизменяемый predictor.
- `src/toxicity/api.py` — FastAPI lifespan, `/health`, `/predict`, `/metrics`.
- `ui/app.py` — Streamlit-клиент; вызывает FastAPI по HTTP и не загружает модель.

## Данные и обучение

- `scripts/download_data.py` — официальная загрузка Jigsaw через KaggleHub.
- `scripts/prepare_data.py` — очистка дубликатов и единый split.
- `scripts/build_data_versions.py` — два preprocessing manifest и content ID.
- `scripts/register_experiments.py` — три сопоставимых MLflow run.
- `scripts/train_final_model.py` — финальный artifact и metadata.
- `data/versions/` — manifest `jigsaw-minimal-v1` и `jigsaw-standard-v2`.
- `data/raw/`, `data/processed/` — локальные данные; не публикуются в Git.

## Результаты

- `mlruns/396315106755929062/` — переносимое MLflow-хранилище трёх runs.
- `artifacts/models/tfidf_logreg_preprocess_standard.joblib` — модель API.
- `artifacts/models/model_metadata.json` — threshold, versions, checksum, metrics.
- `artifacts/results/final_model_metrics.json` — validation/test metrics.
- `artifacts/results/mlflow_runs.json` — компактный реестр run IDs.
- `tests/` — контракт API, preprocessing, checksum, стабильность и ошибки config.

## Демонстрация и сдача

- `scripts/smoke_test.sh` — health, valid predict и controlled 422.
- `docs/architecture.md` — Mermaid-схемы pipeline и CI.
- `docs/demo-script.md` — сценарий видео 1–3 минуты.
- `DEFENSE_MLOPS/` — понятный студенту комплект для защиты.
- `submission/` — локальный итоговый ZIP; каталог игнорируется Git.
