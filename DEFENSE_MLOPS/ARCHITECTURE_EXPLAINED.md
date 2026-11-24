# Архитектура простыми словами

## От данных до ответа пользователю

1. **Jigsaw Dataset.** `scripts/download_data.py` получает исходные CSV через
   KaggleHub. CSV не публикуются в Git из-за размера и условий Kaggle.
2. **DVC.** `dvc.yaml` задаёт повторяемую последовательность команд, а
   `dvc.lock` фиксирует checksums входов, кода и выходов. Поэтому понятно, из
   чего получен каждый artifact.
3. **Preprocessing.** Точные дубликаты текста удаляются, затем данные один раз
   стратифицированно делятся на train/validation/test с seed 42. Minimal и
   standard дают две версии с отдельными content ID.
4. **MLflow.** Три эксперимента записывают параметры, версию данных, Git SHA,
   метрики и model artifacts. Модель выбирается только по validation F1.
5. **Модель.** Победила связка standard preprocessing → TF-IDF 1–2-грамм →
   Logistic Regression. Test использован один раз после выбора.
6. **Docker.** Artifact, metadata, код и hash-locked зависимости упакованы в
   воспроизводимый non-root image.
7. **FastAPI.** При старте API сверяет SHA-256 модели и metadata, затем один раз
   загружает sklearn Pipeline. `/predict` возвращает класс, вероятность, порог,
   latency и версии.
8. **Streamlit.** UI отправляет текст в FastAPI по HTTP. Отдельной копии модели
   в UI нет, поэтому пользователь и API получают одну и ту же версию.

## Почему preprocessing входит в sklearn Pipeline

Одинаковые преобразования выполняются при обучении и инференсе. HTTP-слой не
может случайно применить другой tokenizer или vectorizer. Это защищает от
training-serving skew.

## GitHub Actions

При Pull Request и push в `main` GitHub создаёт чистую Ubuntu-машину, ставит
зависимости по lock-файлу, запускает Ruff и pytest с порогом coverage 80%,
сохраняет отчёты, собирает API+UI и проверяет полный Compose stack. Это
независимое доказательство, что проект не держится на состоянии локального Mac.

## Registry и tags

Git tag `v1.2.0` неизменяемо обозначает проверенный release исходников. На tag
CI дополнительно публикует два image в GitHub Container Registry (GHCR): API и
UI с version tag и полным commit SHA. Версия release и версия model artifact
разделены: код — `v1.2.0`, модель — `toxicity-tfidf-logreg-v1.0.0`.
