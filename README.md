# Toxic Comment MLOps

Курсовой проект по дисциплине «Операционализация моделей машинного обучения». Проект определяет токсичность англоязычного комментария и показывает полный путь от версии данных и MLflow-эксперимента до версионированного HTTP-сервиса в Docker.

Итоговая модель — TF-IDF (1–2-граммы) + Logistic Regression со standard-предобработкой. На отложенном test получено: **F1 = 0,7879**, **PR-AUC = 0,8726**, **ROC-AUC = 0,9729**. Порог `0.664350614731206` выбран только по validation; test не использовался при подборе.

## Быстрая проверка

Нужен Docker Engine с Compose v2. Одна команда собирает и запускает API и UI:

```bash
docker compose up --build --detach --wait --wait-timeout 120
```

После готовности доступны <http://localhost:8000/health>, <http://localhost:8000/docs>, <http://localhost:8000/metrics> и Streamlit UI <http://localhost:8501>.

```bash
sh scripts/smoke_test.sh http://localhost:8000
curl --fail http://localhost:8501/_stcore/health
```

Команда запуска завершается успешно только после того, как оба контейнера стали
`healthy`. Оставьте их запущенными для демонстрации; остановка выполняется
командой `docker compose down`.

## Окружение и lock-файлы

Поддерживается Python `>=3.11,<3.13`; CI и Docker используют Python `3.12.7`. Прямые зависимости описаны в `pyproject.toml`, а транзитивные версии и SHA-256 зафиксированы в `requirements-runtime.lock`, `requirements-dev.lock`, `requirements-train.lock` и `requirements-ui.lock`.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install --require-hashes -r requirements-dev.lock
```

Для data/experiment pipeline:

```bash
python -m pip install --require-hashes -r requirements-train.lock
```

Разделение lock-файлов уменьшает runtime image и не заносит MLflow/DVC в контейнер инференса.

## Данные и DVC

Источник — Jigsaw Toxic Comment Classification Challenge. Из-за правил Kaggle датасет не хранится в Git. После принятия правил соревнования:

```bash
kagglehub login
python scripts/download_data.py
dvc repro prepare_split data_v1 data_v2
```

`prepare_split` удаляет точные дубликаты текста, затем делает стратифицированный split `70/15/15` с seed `42`. Пересечение текстов между train, validation и test проверяется кодом. `dvc.lock` фиксирует команды, зависимости и checksums.

Зафиксированы две версии:

- `jigsaw-minimal-v1`, content ID `44802a8b587e73532e767cbd225d1acdccd4154d1a9665ee9ee6871b57453a48`;
- `jigsaw-standard-v2`, content ID `9358cad3ec371c8a7e098dfb7e73a9f6a1990d2c8c31bb8f6519cea6380926a3`.

Оба manifest хранят source SHA-256, checksum preprocessing и split. Детали — в [DATASET_CARD.md](DATASET_CARD.md).

## Эксперименты и MLflow

В версионном `mlruns/` находятся params, metrics, data version, Git SHA и artifacts трёх сопоставимых запусков:

- Bag of Words + MultinomialNB: run `27aaa276eb7c4baeaecb902dfadc584e`, validation F1 `0,6927`;
- TF-IDF + Logistic Regression, minimal: run `3cc60fc3fe104fe4af1bee4d48229dd1`, validation F1 `0,7728`;
- TF-IDF + Logistic Regression, standard: run `def221719ed64c44a6949ebf9e8b5fb4`, validation F1 `0,7900` — выбран.

```bash
mlflow ui --backend-store-uri ./mlruns --host 127.0.0.1 --port 5000
```

Пересоздание экспериментов и artifacts:

```bash
python main.py classical
python scripts/train_final_model.py
dvc repro experiments
```

Критерий выбора — максимум validation F1. После выбора лучшая модель однократно оценена на test. Ограничения описаны в [MODEL_CARD.md](MODEL_CARD.md).

## Тесты и quality gate

```bash
ruff check src tests scripts ui
pytest --junitxml=junit.xml
```

13 тестов проверяют `/health`, успешный и ошибочный `/predict`, OpenAPI, схему ответа, preprocessing, stateless inference, checksum и fail-fast конфигурации. Порог coverage — `80%`, фактическое покрытие operational code — `90,82%`.

## Локальный API и контракт

```bash
PYTHONPATH=src uvicorn toxicity.api:app --host 0.0.0.0 --port 8000
```

```bash
curl -sS http://localhost:8000/health
curl -sS -X POST http://localhost:8000/predict \
  -H 'Content-Type: application/json' \
  -d '{"text":"You are a disgusting idiot"}'
```

Пример ответа:

```json
{
  "toxic": true,
  "label": "toxic",
  "probability": 0.997,
  "threshold": 0.664350614731206,
  "model_version": "toxicity-tfidf-logreg-v1.0.0",
  "data_version": "jigsaw-standard-v2",
  "latency_ms": 4.2
}
```

Пустая строка, отсутствующее поле или текст длиннее 5000 символов возвращают `422` с описанием, а не `500`.

## Docker

```bash
docker build \
  --build-arg APP_VERSION=1.2.0 \
  --build-arg VCS_REF="$(git rev-parse HEAD)" \
  -t toxic-comment-api:1.2.0 .
docker run --rm -d --name toxicity-api -p 8000:8000 toxic-comment-api:1.2.0
sh scripts/smoke_test.sh http://localhost:8000
docker stop toxicity-api
```

`Dockerfile` использует `python:3.12.7-slim-bookworm`, закреплённый по
manifest digest, ставит пакеты с `--require-hashes`, проверяет health и
запускается от UID `10001`, не root. Compose включает read-only filesystem,
`no-new-privileges` и dropped capabilities.

### Если `localhost:8501` не открывается

```bash
docker compose ps
docker compose logs --no-color --tail=100 api ui
docker compose up --build --detach --wait --wait-timeout 120
```

В `docker compose ps` должны присутствовать сервисы `api` и `ui` со статусом
`healthy` (точный префикс имён зависит от имени каталога). Если список пуст,
стек не запущен. Не запускайте старые
контейнеры из Docker Desktop: проект поднимается из корня репозитория командой
Compose выше.

## Конфигурация и секреты

`config/default.yaml` разделён на `train` и `inference`. Зависящие от среды значения переопределяются через `TOXICITY_CONFIG_PATH`, `TOXICITY_MODEL_PATH`, `TOXICITY_METADATA_PATH`, `TOXICITY_LOG_LEVEL`, `MLFLOW_TRACKING_URI`, `API_BASE_URL`. Безопасный шаблон есть в `.env.example`; `.env` игнорируется Git и Docker.

При старте проверяются config, model/metadata, threshold, model version и SHA-256 artifact. Несовпадение приводит к fail-fast error.

## CI и bonus UI

`.github/workflows/ci.yml` запускается для pull request, `main` и `v*` tag.
Pipeline выполняет locked install, ruff, pytest с coverage gate 80%, публикует
JUnit/coverage artifacts, после quality собирает оба Compose image и делает
полный container smoke с cleanup. Для version tag API и UI публикуются в GHCR
с tag и SHA. `concurrency` исключает дубли для одного PR/ref.

Streamlit UI из `ui/app.py` обращается только к HTTP API, показывает результат,
версию данных и понятно обрабатывает errors. Техническая версия модели остаётся
доступна в ответах `/health` и `/predict`, но не перегружает пользовательский UI.

## Структура

```text
.github/workflows/ci.yml    lint, tests, coverage, Docker smoke, GHCR
artifacts/models/           model artifact + checksumed metadata
artifacts/results/          metrics, experiment registry, error analysis
config/default.yaml         train/inference/data-version configuration
data/versions/              two content-addressed data manifests
docs/                       architecture and demo scenario
mlruns/                     portable MLflow store for 3 final runs
scripts/                    data, training, experiment and smoke commands
src/toxicity/api.py         FastAPI contract and metrics endpoint
src/toxicity/inference.py   immutable predictor + artifact verification
tests/                      positive, negative, schema and unit tests
ui/app.py                   Streamlit client of the HTTP API
Dockerfile                  non-root inference image
Dockerfile.ui               non-root UI image
dvc.yaml / dvc.lock         reproducible pipeline
MODEL_CARD.md               scope, metrics, risks and provenance
DATASET_CARD.md             source, split, versions and limitations
REPORT.md                   rubric evidence and final checklist
```

Схемы есть в [docs/architecture.md](docs/architecture.md), карта соответствия
рубрике — в [REPORT.md](REPORT.md), сценарий короткого видео — в
[docs/demo-script.md](docs/demo-script.md), а подробный комплект для защиты —
в каталоге `DEFENSE_MLOPS/`.

Важно: release проекта имеет tag `v1.2.0`, а неизменившийся ML artifact —
model version `toxicity-tfidf-logreg-v1.0.0`. Это разные уровни версионирования,
и совпадать они не обязаны.
