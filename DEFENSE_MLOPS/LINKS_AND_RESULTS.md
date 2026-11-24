# Ссылки и подтверждённые результаты

## GitHub и CI

- Репозиторий: <https://github.com/Agur-sama/mlops-toxic-comments> — исходники,
  документация, модель и MLflow metadata.
- Основная ветка: <https://github.com/Agur-sama/mlops-toxic-comments/tree/main>.
- Pull Request №1: <https://github.com/Agur-sama/mlops-toxic-comments/pull/1> —
  история аудита, diff и проверки.
- GitHub Actions: <https://github.com/Agur-sama/mlops-toxic-comments/actions/workflows/ci.yml>.
- Checks PR: <https://github.com/Agur-sama/mlops-toxic-comments/pull/1/checks>.
- Итоговый tag: `v1.2.0`; страница release-кода:
  <https://github.com/Agur-sama/mlops-toxic-comments/tree/v1.2.0>.
- Full commit SHA: получить командой
  `git rev-parse 'v1.2.0^{commit}'`; фактическое значение приводится вместе со
  ссылкой на успешный tag workflow при сдаче.

## Docker

- локальные images: `toxic-comment-api:1.2.0`, `toxic-comment-ui:1.2.0`;
- GHCR API: `ghcr.io/agur-sama/mlops-toxic-comments/toxic-comment-api:v1.2.0`;
- GHCR UI: `ghcr.io/agur-sama/mlops-toxic-comments/toxic-comment-ui:v1.2.0`.

```bash
docker compose up --build --detach --wait --wait-timeout 120
sh scripts/smoke_test.sh http://localhost:8000
```

- API: <http://localhost:8000>;
- health: <http://localhost:8000/health>;
- Swagger: <http://localhost:8000/docs>;
- Streamlit: <http://localhost:8501>;
- MLflow UI после локального запуска: <http://localhost:5000>.

## MLflow

- experiment name: `toxic-comment-classification`;
- experiment ID: `396315106755929062`;
- BoW + NB: `27aaa276eb7c4baeaecb902dfadc584e`;
- TF-IDF + LR minimal: `3cc60fc3fe104fe4af1bee4d48229dd1`;
- выбранный TF-IDF + LR standard: `def221719ed64c44a6949ebf9e8b5fb4`;
- model artifact:
  `artifacts/models/tfidf_logreg_preprocess_standard.joblib`;
- model version: `toxicity-tfidf-logreg-v1.0.0`;
- SHA-256: `3e98dd65c5f46c103585450f577657f8e7cde97eaa5117894225005112716b3d`.

```bash
mlflow ui --backend-store-uri ./mlruns --host 127.0.0.1 --port 5000
```

## DVC и версии данных

- `jigsaw-minimal-v1`, content ID
  `44802a8b587e73532e767cbd225d1acdccd4154d1a9665ee9ee6871b57453a48`;
- `jigsaw-standard-v2`, content ID
  `9358cad3ec371c8a7e098dfb7e73a9f6a1990d2c8c31bb8f6519cea6380926a3`;
- source SHA-256
  `bd4084611bd27c939ba98e5e63bc3e5a2c1a4e99477dcba46c829e4c986c429d`;
- split SHA-256
  `32ce6541f1b0318c31f7b7d18e7f84da7bb7e52259a71d0fa9dc0430dc33a47e`.

```bash
dvc dag
dvc status
dvc repro
```

## Итоговые test-метрики

- accuracy `0,9605614973`;
- precision `0,8130797774`;
- recall `0,7641673932`;
- F1 `0,7878651685`;
- PR-AUC `0,8725905622`;
- ROC-AUC `0,9728975300`;
- confusion matrix: TN `21239`, FP `403`, FN `541`, TP `1753`;
- threshold `0.664350614731206`.

## Тесты

- `13 passed`;
- operational-code coverage `90,82%`;
- required coverage gate `80%`;
- Ruff, pytest, DVC, no-cache Docker build, API/UI health, 422, browser
  Streamlit→FastAPI, non-root и read-only checks прошли локально.

Демо-видео не считается готовым до личной записи. Проверенный сценарий и
инструкция QuickTime находятся в `docs/demo-script.md` и `DEFENSE_MLOPS/DEMO.md`.
