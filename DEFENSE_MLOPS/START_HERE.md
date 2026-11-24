# С чего начать защиту

## Где находится проект

Локально: `/Users/maksim/Documents/ChatGPT/курсовая по nlp`.

В VS Code откройте именно корень этого каталога. Не открывайте
`mlops_submission/`: там лежат отдельные лабораторные, они не относятся к этой
курсовой.

## Самый быстрый запуск

В терминале из корня проекта:

```bash
git checkout v1.2.1
docker compose up --build --detach --wait --wait-timeout 120
docker compose ps
```

Откройте:

- Streamlit: <http://localhost:8501>;
- Swagger: <http://localhost:8000/docs>;
- health: <http://localhost:8000/health>;
- Prometheus-метрики: <http://localhost:8000/metrics>.

Проверка API одной командой:

```bash
sh scripts/smoke_test.sh http://localhost:8000
```

Остановка:

```bash
docker compose down
```

## MLflow и DVC

Для MLflow сначала установите training-зависимости, затем запустите UI:

```bash
python -m pip install --require-hashes -r requirements-train.lock
mlflow ui --backend-store-uri ./mlruns --host 127.0.0.1 --port 5000
```

Откройте <http://localhost:5000>, experiment
`toxic-comment-classification`, run
`def221719ed64c44a6949ebf9e8b5fb4`.

```bash
dvc dag
dvc status
```

`dvc dag` показывает зависимости pipeline, а `dvc status` — соответствует ли
рабочее дерево зафиксированному `dvc.lock`.

## Что показать преподавателю

1. GitHub: адрес находится в `LINKS_AND_RESULTS.md`.
2. Tag `v1.2.1` и полный SHA: `git show --no-patch v1.2.1`.
3. Зелёный GitHub Actions workflow по ссылке из `LINKS_AND_RESULTS.md`.
4. Три MLflow run и выбранный лучший run.
5. `dvc dag`, два manifest в `data/versions/` и их content ID.
6. Swagger `/docs`, успешный и ошибочный `/predict`.
7. Streamlit-предсказание: UI действительно обращается к FastAPI; техническую
   model version при необходимости покажите в `/health`, а не в UI.
8. `pytest`: 13 тестов, покрытие operational code 90,82%.

Подробный 10–15-минутный порядок находится в `DEMO.md`.
