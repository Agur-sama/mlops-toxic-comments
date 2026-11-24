# Защита на 10–15 минут

## Подготовка до начала

```bash
git checkout v1.2.1
docker compose up --build --detach --wait --wait-timeout 120
```

Откройте заранее GitHub, Actions, `http://localhost:5000`,
`http://localhost:8000/docs` и `http://localhost:8501`. Не показывайте `.env`,
Kaggle credentials или другие секреты.

## 0:00–1:30 — задача и результат

Откройте `README.md`. Скажите: «Проект классифицирует англоязычные комментарии
на toxic/non-toxic. Это полный MLOps-путь: versioned data, MLflow, model
artifact, API, Docker, UI и CI».

Покажите test-метрики лучшей модели: F1 `0,7879`, PR-AUC `0,8726`, ROC-AUC
`0,9729`. Объясните, что порог выбран на validation, а test не применялся при
подборе.

## 1:30–3:00 — Git и воспроизводимость

```bash
git describe --tags --exact-match
git rev-parse HEAD
git log --oneline --decorate -8
```

Должен появиться tag `v1.2.1`. Откройте Pull Request и зелёный Actions workflow
по ссылкам из `LINKS_AND_RESULTS.md`. Покажите четыре lock-файла.

## 3:00–5:00 — данные, DVC и MLflow

```bash
dvc dag
dvc status
```

Откройте `data/versions/` и объясните две версии preprocessing. Затем в MLflow
покажите три runs, их params/metrics/tags и выбранный run
`def221719ed64c44a6949ebf9e8b5fb4`.

Скажите: «Все runs используют один split. Модель выбрана по validation F1.
Artifact API побайтово совпадает с artifact этого run».

## 5:00–7:00 — Docker и API

```bash
docker compose ps
curl -sS http://localhost:8000/health
```

Оба сервиса должны быть `healthy`; health должен показать `ready`, model/data
version и SHA-256. В Swagger вызовите `/predict` с:

```json
{"text":"You are a disgusting idiot"}
```

Покажите `toxic=true`, вероятность, threshold, latency и версии. Затем отправьте
`{"text":"   "}` и покажите controlled `422`.

## 7:00–8:30 — Streamlit

Откройте <http://localhost:8501>, введите тот же английский текст и нажмите
кнопку анализа. Покажите класс, вероятность, data version и latency. Скажите: «Streamlit не
загружает joblib; он вызывает FastAPI по `API_BASE_URL`, поэтому model serving
централизован».

## 8:30–10:00 — тесты и CI

```bash
ruff check src tests scripts ui
pytest --junitxml=junit.xml
```

Ожидается `13 passed` и total coverage `90,82%`. В GitHub Actions покажите те же
quality gates, сборку обоих images и smoke UI→API.

## 10:00–12:00 — риски и вывод

Откройте `MODEL_CARD.md`: английский язык, dataset bias, отсутствие ручной
модерации и необходимость monitoring/retraining. Завершите: «Release можно
воспроизвести по tag, модель проверяется checksum, а clean CI и Docker smoke
отделяют доказательства от состояния моего ноутбука».

## Короткое видео 1–3 минуты

Используйте `docs/demo-script.md`. На macOS: QuickTime Player → «Файл» → «Новая
запись экрана» → область терминала и браузера → запись. Покажите tag/SHA,
`docker compose ps`, `/health`, Swagger predict+422 и Streamlit. После записи
просмотрите файл целиком и загрузите по доступной преподавателю ссылке.
