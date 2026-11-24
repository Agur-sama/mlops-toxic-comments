# Независимый аудит MLOps-курсовой

Дата начала аудита: 25 ноября 2026 года.

Официальный источник требований: `/Users/maksim/Downloads/rr.md`, файл
«Курсовой проект по дисциплине “Операционализация моделей машинного обучения”».
Оценивание: 80 обязательных баллов и не более 20 дополнительных.

Документ обновляется по мере финальной публикации. Пункт считается
подтверждённым только после реального запуска.

## Первичный результат

| Требование | Максимальные баллы | Реализовано | Проверено реальным запуском | Что необходимо исправить |
|---|---:|---|---|---|
| Git и воспроизводимое окружение | 10 | Да | Публичный repo, 2 merged PR, annotated `v1.2.1`, clean clone и locked install подтверждены | Нет |
| Docker | 15 | Да | No-cache API+UI build, health, predict, 422, Swagger, non-root/read-only и clean-clone run подтверждены | Нет |
| Данные и эксперименты | 15 | Да | DVC up to date; 3 MLflow runs, 2 data versions, checksums и совпадение model artifact подтверждены | Для нового скачивания нужен личный Kaggle login |
| Инференс-сервис и тесты | 15 | Да | Clean clone: 13 passed, coverage 90,82%; tag CI и container smoke успешны | Нет |
| Конфигурация и секреты | 10 | Да | Portable paths, env template, secret scan, fail-fast tests, minimal CI permissions и archive scope проверены | Нет |
| Документация | 10 | Да | README, cards, report, схемы, demo и 8 файлов `DEFENSE_MLOPS` сверены | Нет |
| Материалы для сдачи | 5 | 3 из 5 | Ссылки, результаты, сценарии и проверенный ZIP готовы | Студенту записать видео 1–3 минуты |
| GitHub Actions (бонус) | 10 | Да | Release run №9: `quality`, `image`, `publish` успешны; API+UI опубликованы в GHCR | Нет |
| Streamlit UI (бонус) | 10 | Да | Browser test из clean clone: Streamlit → FastAPI → model успешен; error handling есть | Нет |

## Обнаруженные недостатки

1. У локального репозитория отсутствовал Git remote; настоящих ссылок на
   GitHub, PR и GitHub Actions не было.
2. Tag `v1.1.0` содержал каталог `mlops_submission/` с лабораторными №4–7.
   Эти работы не относятся к отдельной MLOps-курсовой и не должны публиковаться
   в её новом репозитории.
3. Текущая локальная ветка `main` содержит более позднее изменение практики №4,
   поэтому не может напрямую стать `main` отдельного репозитория курсовой.
4. Чистый tag `v1.0.0` содержит только курсовой проект, но предшествует
   исправлению Linux-зависимости `watchdog` в UI lock-файле.
5. `REPORT.md` содержит placeholders внешних ссылок. Облачный CI и проверка
   чистого клона ранее не были выполнены.
6. Итогового каталога `DEFENSE_MLOPS/` и актуального независимого ZIP проекта
   нет.
7. Демо-видео не записано; его нельзя отмечать готовым.

## Подтверждённые факты до исправлений

- исходный SHA модели и SHA artifact выбранного MLflow run совпадают:
  `3e98dd65c5f46c103585450f577657f8e7cde97eaa5117894225005112716b3d`;
- выбранный run: `def221719ed64c44a6949ebf9e8b5fb4`;
- model version: `toxicity-tfidf-logreg-v1.0.0`;
- data version: `jigsaw-standard-v2`;
- test F1: `0.7878651685393259`;
- test precision: `0.8130797773654916`;
- test recall: `0.7641673931996512`;
- test PR-AUC: `0.8725905621703934`;
- test ROC-AUC: `0.9728975299651048`;
- зафиксированы три MLflow run и две версии preprocessing/data manifests;
- модель в `artifacts/models/` побайтово совпадает с artifact выбранного run.

Эти значения повторно проверены на опубликованном release commit
`0f3646657d7225b7e41449f8e3f2bc66daf28f55`.

## Подтверждение облачного CI

PR №1: <https://github.com/Agur-sama/mlops-toxic-comments/pull/1>.

Workflow run №3:
<https://github.com/Agur-sama/mlops-toxic-comments/actions/runs/45493243912>.
Jobs `quality` и `image` завершены со статусом success. Внутри подтверждены
locked install, Ruff, pytest/coverage gate, upload reports, сборка API+UI и
полный smoke Compose stack. Job `publish` корректно пропущен, потому что PR не
является version tag.

Итоговый tag workflow run №9:
<https://github.com/Agur-sama/mlops-toxic-comments/actions/runs/45495465408>.
Jobs `quality`, `image` и `publish` завершены успешно. API и UI images
опубликованы в GHCR с tag `v1.2.1` и полным commit SHA.

## Проверка из чистого клона

Tag `v1.2.1` клонирован в отдельный `/tmp`-каталог. Подтверждены detached HEAD
`0f3646657d7225b7e41449f8e3f2bc66daf28f55`, hash-locked установка, Ruff,
13 тестов, coverage 90,82%, `pip check`, no-cache build обоих Docker images,
Compose health, `/health`, valid/invalid `/predict`, Swagger, non-root,
read-only filesystem, UI→API и browser prediction.

KaggleHub download корректно потребовал личную аутентификацию. Это ожидаемое
внешнее ограничение Jigsaw: новый пользователь должен выполнить
`kagglehub login` и принять правила соревнования. Без raw CSV успешно проверены
`dvc repro experiments` и `dvc dag`; полный `dvc repro` ранее подтверждён в
исходном изолированном окружении.

## Подтверждённая оценка

- обязательная часть: 78/80 до записи видео, 80/80 после добавления видео;
- GitHub Actions: 10/10;
- Streamlit UI: 10/10;
- подтверждено сейчас: 98/100;
- возможный итог после личной записи видео: 100/100.

## План исправлений и проверки

1. Работать в отдельной ветке от чистого `v1.0.0`, не затрагивая
   `mlops_submission/`.
2. Повторно проверить тесты, coverage, DVC, MLflow и секреты.
3. Собрать API и UI без Docker cache, выполнить полный smoke и browser test.
4. Исправить документацию и создать `DEFENSE_MLOPS/`.
5. Создать отдельный публичный GitHub-репозиторий `mlops-toxic-comments` в
   аккаунте `Agur-sama`, опубликовать baseline и рабочую ветку, открыть PR.
6. Добиться зелёного GitHub Actions на PR и после merge; создать version tag.
7. Выполнить проверку из отдельного чистого клона итогового tag.
8. Создать ZIP без secrets, datasets, caches, virtualenv и лабораторных.
9. Обновить этот аудит фактическими доказательствами и итоговой оценкой.
