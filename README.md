# Определение токсичных комментариев

Воспроизводимый учебный проект по бинарной классификации комментариев из соревнования **Jigsaw Toxic Comment Classification Challenge**. Основной сценарий оформлен как выполненный Jupyter Notebook с Markdown-пояснениями и логически разделёнными Python-ячейками. Реализованы EDA, три варианта предобработки, Bag of Words + Naive Bayes, TF-IDF + Logistic Regression, TF-IDF + Linear SVM, fine-tuning DistilBERT, подбор порога по validation, единые метрики, графики, анализ ошибок и генерация Word-отчёта.

## Статус текущего запуска

Предоставленный архив содержит `train.csv`, `test.csv`, `test_labels.csv` и `sample_submission.csv`. Notebook выполнен без ошибок на полном `train.csv` из 159 571 строки. Проведены EDA и 16 классических прогонов; лучший результат показал TF-IDF + Logistic Regression со standard-предобработкой: F1 = 0,7879, PR-AUC = 0,8726. DistilBERT реализован, но не обучался: тяжёлые зависимости и веса модели в текущем окружении не устанавливались.

## Структура

```text
config/default.yaml           параметры и random seed 42
notebooks/coursework_toxicity.ipynb  основной выполненный сценарий
data/raw/                     официальные архивы Kaggle или train.csv
data/processed/               сохранённый split manifest 70/15/15
src/toxicity/                 загрузка, EDA, модели, метрики, отчёт
scripts/                      отдельные команды этапов
artifacts/figures/            PNG, не менее 220 DPI
artifacts/results/            JSON/CSV метрики, среда, анализ ошибок
artifacts/models/             joblib и fine-tuned DistilBERT
artifacts/predictions/        тестовые оценки и предсказания
report/coursework.docx        курсовая работа
```

## Установка

Рекомендуется Python 3.11; код также совместим с Python 3.12.

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python scripts/download_nltk.py
```

Для CPU можно не устанавливать CUDA-сборку PyTorch. Классические модели работают без GPU. Для DistilBERT на NVIDIA GPU установите совместимую сборку PyTorch по официальной инструкции PyTorch; код автоматически включает `fp16` на CUDA. На Apple Silicon используется MPS, если он доступен.

## Получение официальных данных

1. Откройте страницу соревнования и примите правила: <https://www.kaggle.com/competitions/jigsaw-toxic-comment-classification-challenge/data>.
2. Авторизуйте KaggleHub:

   ```bash
   kagglehub login
   ```

3. Скачайте и распакуйте архивы:

   ```bash
   python scripts/download_data.py
   ```

Альтернатива: вручную скачайте официальные архивы Kaggle и поместите их в `data/raw/`. Загрузчик рекурсивно распакует ZIP, включая вложенные архивы. Синтетические данные не используются как замена Jigsaw.

## Запуск

Основной вариант — открыть `notebooks/coursework_toxicity.ipynb` и выполнить **Run All**. Notebook самостоятельно ищет корень проекта среди родительских каталогов, поэтому работает и при запуске непосредственно из папки `notebooks/`. При нестандартном размещении можно задать переменную окружения `TOXICITY_PROJECT_ROOT`. В notebook есть отдельные разделы для источника данных, схемы, контроля качества, EDA, split, проверки утечки, предобработки, пяти экспериментов, порога решения, анализа ошибок, DistilBERT и пересборки отчёта.

Повторное выполнение из терминала:

```bash
python scripts/build_notebook.py
python scripts/execute_notebook.py
```

Для ручного запуска Jupyter можно использовать VS Code, JupyterLab или классический Jupyter Notebook, выбрав интерпретатор `.venv/bin/python`.

Командный интерфейс сохранён как дополнительный способ запуска.

Полный конвейер без автоматического BERT:

```bash
python main.py
```

Полный конвейер с DistilBERT:

```bash
python main.py all --bert
```

Отдельные этапы:

```bash
python scripts/run_eda.py
python scripts/train_classical.py
python scripts/train_bert.py
python scripts/generate_report.py
python scripts/validate_project.py
```

Попытка автоматического скачивания при запуске:

```bash
python main.py all --download
```

## Быстрая проверка

После размещения официального `train.csv` можно выполнить демонстрационный прогон на небольшой стратифицированной подвыборке:

```bash
python main.py classical --quick
```

Результаты пишутся в `classical_quick_results.*`, помечаются как демонстрационные и не включаются автоматически в финальные выводы или `all_results.csv`.

## Протокол экспериментов

- Точные дубликаты `comment_text` удаляются до разбиения.
- Единственный split создаётся с `random_state=42`: 70% train, 15% validation, 15% test.
- Стратификация выполняется по `toxic`.
- Пересечения одинаковых текстов между частями проверяются программно.
- Векторизатор обучается только внутри Pipeline на train.
- Гиперпараметры и порог выбираются по validation; test используется один раз для итоговой оценки.
- Для `LinearSVC` ROC-AUC и PR-AUC вычисляются по `decision_function`; значения не называются вероятностями.
- Порог выбирается по максимуму F1 на validation и затем фиксируется для test.

## DistilBERT

Базовая модель — `distilbert-base-uncased`. Исходный текст подвергается только технической очистке пробелов; токенизацию, специальные токены, усечение и attention masks формирует Hugging Face tokenizer. Параметры находятся в `config/default.yaml`. Для второго эксперимента измените `epochs`, `max_length` или `learning_rate` и задайте отдельное имя:

```bash
python main.py bert --bert-variant distilbert_len128
```

Если используется подвыборка, задайте `bert.max_train_samples` в YAML. Размер и принцип стратифицированного формирования сохраняются в конфигурации результата; такой прогон нельзя интерпретировать как полностью эквивалентный обучению классических моделей на полном train.

## Основные выходные файлы

- `data/processed/split_manifest.csv` — неизменяемые идентификаторы выборок;
- `artifacts/results/eda_summary.json` — размеры, пропуски, дубликаты, классы и длины;
- `artifacts/results/classical_results.csv` — все классические эксперименты;
- `artifacts/results/all_results.csv` — сводная таблица завершённых полных прогонов;
- `artifacts/predictions/*_test_predictions.csv` — оценки, метки и тексты;
- `artifacts/results/error_analysis_*.csv` — FP/FN и наблюдаемые признаки;
- `artifacts/figures/*.png` — EDA и сравнение моделей;
- `report/coursework.docx` — Word-документ.

## Примечания по воспроизводимости

Сохранение split manifest предотвращает случайное изменение теста между моделями. При замене исходного файла проект остановится, если ID не совпадают с существующим manifest. Флаг `--force-split` следует использовать только после осознанной проверки источника. Версии библиотек зафиксированы, сведения о фактическом окружении записываются в `artifacts/results/environment.json`.

## Этическое использование

Набор содержит грубую и оскорбительную лексику. Ошибки классификатора могут непропорционально затрагивать упоминания идентичностей. Модель следует использовать как вспомогательный сигнал модерации, с мониторингом качества и возможностью человеческого пересмотра, а не как единственный механизм санкций.
