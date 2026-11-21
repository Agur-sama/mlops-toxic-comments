# Model Card: Toxicity TF-IDF Logistic Regression

## Описание и назначение

`toxicity-tfidf-logreg-v1.0.0` — бинарный классификатор токсичных англоязычных комментариев. Он предназначен для учебной демонстрации MLOps-цикла и предварительной модерации, а не для автономного удаления контента или санкций в отношении людей.

## Версия и происхождение

- Model version: `toxicity-tfidf-logreg-v1.0.0`.
- Artifact: `artifacts/models/tfidf_logreg_preprocess_standard.joblib`.
- SHA-256: `3e98dd65c5f46c103585450f577657f8e7cde97eaa5117894225005112716b3d`.
- Metadata: `artifacts/models/model_metadata.json`.
- Selected MLflow run: `def221719ed64c44a6949ebf9e8b5fb4`.
- Training code commit: `1fe86b49b85f242e7fd0635b888059c1389384df`.
- Data version: `jigsaw-standard-v2`.
- Seed: `42`.

API до deserialization сравнивает checksum и version с metadata, что исключает тихую подмену артефакта.

## Архитектура и preprocessing

Standard preprocessing декодирует HTML entities, удаляет HTML tags, заменяет URL токеном `URL`, приводит текст к lower case и токенизирует. Эта же функция сериализована в sklearn Pipeline, поэтому training-serving skew исключён.

Признаки — TF-IDF по 1–2-граммам, `min_df=2`, `max_features=120000`, `sublinear_tf=true`. Классификатор — Logistic Regression (`C=4.0`, `class_weight=balanced`, `solver=liblinear`, `max_iter=1000`).

## Данные и метрики

Использован `train.csv` Jigsaw Toxic Comment Classification Challenge. После exact-text deduplication выполнен стратифицированный split 70/15/15. Validation использовался для выбора модели и порога; test — только для однократной финальной оценки.

На test из 23 936 примеров: accuracy `0,9606`, precision `0,8131`, recall `0,7642`, F1 `0,7879`, ROC-AUC `0,9729`, PR-AUC `0,8726`. Confusion matrix: TN `21239`, FP `403`, FN `541`, TP `1753`. Выбранный на validation порог — `0.664350614731206`.

## Ограничения и риски

Модель можно использовать как один из сигналов для ранжирования очереди модерации. Она не предназначена для санкций без human review, неанглийских текстов, оценки истинности/намерения или high-stakes решений.

Данные отражают Wikipedia и конкретный период. Identity terms могут коррелировать с toxic-меткой, создавая риск несоразмерных false positive для упоминаний защищённых групп. Сарказм, цитаты, обфускации и новый сленг могут давать ошибки. Перед production нужны subgroup evaluation, калибровка на целевом домене, appeal process и drift/false-positive monitoring.

## Эксплуатация

API принимает один текст до 5000 символов. Ответ содержит model/data version. `/metrics` экспортирует request counters и latency в Prometheus format. После startup Pipeline не изменяется между запросами.
