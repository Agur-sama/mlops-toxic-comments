# Отчёт о готовности к сдаче

## Идентификаторы

- Итоговый tag: `v1.2.1`.
- Full release commit SHA: `0f3646657d7225b7e41449f8e3f2bc66daf28f55`.
- Model version: `toxicity-tfidf-logreg-v1.0.0`.
- Model SHA-256: `3e98dd65c5f46c103585450f577657f8e7cde97eaa5117894225005112716b3d`.
- Selected MLflow run: `def221719ed64c44a6949ebf9e8b5fb4`.
- Data version: `jigsaw-standard-v2`.
- Data content ID: `9358cad3ec371c8a7e098dfb7e73a9f6a1990d2c8c31bb8f6519cea6380926a3`.
- Repository URL: <https://github.com/Agur-sama/mlops-toxic-comments>.
- Pull Request: <https://github.com/Agur-sama/mlops-toxic-comments/pull/1>.
- GHCR hotfix Pull Request: <https://github.com/Agur-sama/mlops-toxic-comments/pull/2>.
- CI workflow: <https://github.com/Agur-sama/mlops-toxic-comments/actions/workflows/ci.yml>.
- Successful PR CI: <https://github.com/Agur-sama/mlops-toxic-comments/actions/runs/45493243912>
  (`quality` и `image` успешно; `publish` ожидаемо пропущен для PR).
- Successful release CI: <https://github.com/Agur-sama/mlops-toxic-comments/actions/runs/45495465408>
  (`quality`, `image` и `publish` успешно; API и UI отправлены в GHCR).
- Demo video: не записано; проверенный сценарий находится в
  `docs/demo-script.md`. Не следует указывать вымышленную ссылку.
- Submission ZIP: `submission/mlops-toxic-comments-v1.2.1.zip`, SHA-256
  `9e289ab4928d938bef1d7eb670a2674eca883c2ce9dc8bd7cf8b1f7074cf5cbb`.

## Обязательная часть, 80 баллов

### Git и окружение

Основная ветка — `main`; изменения сервиса и документации создаются в `codex/*` ветках и сливаются с `--no-ff`. Итог отмечает annotated tag. `.gitignore` исключает dataset, caches, env и secrets. `pyproject.toml` и четыре hash-locked requirements фиксируют Python и все dependencies. Чистая установка описана в README.

### Docker

`Dockerfile` и `Dockerfile.ui` используют `python:3.12.7-slim-bookworm`, hash-locked install и UID 10001. `.dockerignore` не пускает в image данные, env, caches и ненужные artifacts. Compose запускает `/health`, `/predict`, `/docs` одной командой и включает read-only filesystem, dropped capabilities и `no-new-privileges`. `scripts/smoke_test.sh` проверяет health, valid predict и controlled 422.

### Данные и эксперименты

`dvc.yaml` и `dvc.lock` фиксируют split и две версии preprocessing. `data/versions/*.json` содержат source, checksums и content ID. В переносимом `mlruns/` есть три сопоставимых run с params, metrics, code SHA, data version и artifacts. Лучший run выбран по validation F1; test не участвует в подборе. Модель хранится в Git и MLflow artifact и проверяется по SHA-256.

### Инференс и тесты

Pydantic описывает request/response схемы и example. `/health` возвращает readiness, model/data version и checksum. `/predict` возвращает probability, threshold, class, latency и versions. Невалидный ввод даёт 422. Preprocessing входит в sklearn Pipeline. 13 тестов проходят с coverage 90,82%.

### Конфигурация и секреты

`config/default.yaml` имеет секции `train` и `inference`, все пути относительные. Environment overrides описаны в `.env.example`; `.env` игнорируется. Обязательные поля, paths, threshold, version и checksum проверяются до приёма traffic. Training params записаны в MLflow.

### Документация и материалы

README покрывает clean install, data, tests, training, DVC/MLflow, Docker, API examples, UI, CI и repository structure. `MODEL_CARD.md` и `DATASET_CARD.md` описывают provenance, metrics, risks, условия доступа, split и versions. `docs/architecture.md` содержит две схемы. `docs/demo-script.md` покрывает все пять шагов видео.

## Бонусы, 20 баллов

### Continuous Integration

GitHub Actions включает lint, tests, 80% coverage gate, JUnit/coverage artifacts, Docker build только после quality, container smoke с cleanup, branch/PR/tag triggers, concurrency и SHA/version image tags. Для tag image публикуется в GHCR стандартным `GITHUB_TOKEN`, который не записывается в логи.

### Пользовательский интерфейс

Streamlit UI запускается в отдельном non-root image, обращается к `/predict` по
HTTP, не имеет своей модели, показывает probability, data version и latency,
понятно обрабатывает 4xx/network errors. Model version доступна через API, но
скрыта из пользовательского интерфейса. Compose ждёт API health до старта UI.

## Проверено локально

- `ruff check src tests scripts ui` — passed;
- `pytest --junitxml=junit.xml` — 13 passed, coverage 90,82%;
- `dvc repro prepare_split data_v1 data_v2 experiments` — passed;
- model checksum и runtime prediction — passed;
- локальный API smoke (`/health`, valid `/predict`, invalid `422`) — passed;
- чистая Docker-сборка API и UI с hash-locked dependencies — passed;
- `docker compose up --detach --wait`, healthchecks обоих контейнеров, связь UI→API и browser UI prediction — passed.
- отдельный чистый clone tag `v1.2.1`: locked install, 13 тестов,
  coverage 90,82%, no-cache Docker build, API/UI/security smoke и browser
  prediction — passed;
- получение исходного Jigsaw CSV в чистом clone требует личной Kaggle
  аутентификации и принятия правил соревнования; `dvc repro experiments` и
  `dvc dag` без raw CSV проверены.

## Финальный чек-лист

- [x] Добавить действительные URL репозитория, PR и workflow.
- [x] Проверить зелёный GitHub Actions для PR commit.
- [x] Проверить зелёный GitHub Actions и публикацию GHCR на итоговом tag SHA.
- [x] Проверить публичные ссылки репозитория, PR, tag и workflow.
- [ ] Записать 1–3 минутное видео по `docs/demo-script.md`.
- [x] Проверить `git status --short` — вывод пуст для release checkout.
