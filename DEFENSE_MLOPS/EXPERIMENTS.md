# Проверенные эксперименты

MLflow experiment ID: `396315106755929062`.

Метрики ниже прочитаны из файлов `mlruns/.../metrics` и относятся к test split.
Выбор сделан по validation F1, а не по test.

| Run | Модель и параметры | Данные | Code SHA | Precision | Recall | F1 | PR-AUC | ROC-AUC |
|---|---|---|---|---:|---:|---:|---:|---:|
| `27aaa276eb7c4baeaecb902dfadc584e` | CountVectorizer, 1–2 gram, max_features=120000, min_df=2; MultinomialNB alpha=0.5 | `jigsaw-minimal-v1` | `1fe86b49b85f242e7fd0635b888059c1389384df` | 0,7330 | 0,6691 | 0,6996 | 0,6978 | 0,9188 |
| `3cc60fc3fe104fe4af1bee4d48229dd1` | TF-IDF, 1–2 gram, max_features=120000, min_df=2, sublinear_tf; LogisticRegression C=4.0 | `jigsaw-minimal-v1` | `1fe86b49b85f242e7fd0635b888059c1389384df` | 0,7782 | 0,7724 | 0,7753 | 0,8610 | 0,9698 |
| `def221719ed64c44a6949ebf9e8b5fb4` | standard preprocessing; TF-IDF, 1–2 gram, max_features=120000, min_df=2, sublinear_tf; LogisticRegression C=4.0 | `jigsaw-standard-v2` | `1fe86b49b85f242e7fd0635b888059c1389384df` | **0,8131** | 0,7642 | **0,7879** | **0,8726** | **0,9729** |

Validation F1 по тем же runs: `0,6927`, `0,7728`, `0,7900`. Третий run выбран,
потому что у него максимальный validation F1. Порог `0.664350614731206` также
подобран на validation.

## Итоговый artifact

- путь API: `artifacts/models/tfidf_logreg_preprocess_standard.joblib`;
- artifact выбранного run:
  `mlruns/396315106755929062/def221719ed64c44a6949ebf9e8b5fb4/artifacts/model/tfidf_logreg_preprocess_standard.joblib`;
- SHA-256 обоих файлов:
  `3e98dd65c5f46c103585450f577657f8e7cde97eaa5117894225005112716b3d`;
- model version: `toxicity-tfidf-logreg-v1.0.0`.

Файлы побайтово совпадают. Небольшое отличие последнего разряда threshold в
историческом MLflow metric связано с сериализацией float; authority для
инференса — checksumed `model_metadata.json` и фактический artifact.
