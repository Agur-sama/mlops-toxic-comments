# Dataset Card: Jigsaw Toxic Comment Classification

## Источник и права

Данные взяты из Kaggle-соревнования `jigsaw-toxic-comment-classification-challenge`, организованного Jigsaw/Conversation AI. Комментарии получены из Wikipedia talk pages и размечены по шести категориям. Доступ и использование регулируются Kaggle Competition Rules; поэтому CSV не перераспространяется через Git.

Получение требует Kaggle account, принятие правил и `kagglehub login`. Загрузка: `python scripts/download_data.py`.

## Состав и split

Training file содержит 159 571 строку. Поля: `id`, `comment_text`, а также бинарные метки `toxic`, `severe_toxic`, `obscene`, `threat`, `insult`, `identity_hate`. Target этого проекта — `toxic`; остальные метки нужны для EDA и анализа ошибок. Positive share — около 9,58%.

До split удаляются точные дубликаты `comment_text`. Затем `train_test_split` с `random_state=42` и stratification по `toxic` формирует train 111 699, validation 23 936 и test 23 936 строк. Код проверяет равенство ID и отсутствие пересечения текстов. Split SHA-256: `32ce6541f1b0318c31f7b7d18e7f84da7bb7e52259a71d0fa9dc0430dc33a47e`.

## Версии preprocessing

- `jigsaw-minimal-v1` заменяет null bytes, нормализует whitespace и обрезает края. Content ID: `44802a8b587e73532e767cbd225d1acdccd4154d1a9665ee9ee6871b57453a48`.
- `jigsaw-standard-v2` дополнительно декодирует HTML entities, удаляет tags, заменяет URL, приводит текст к lower case и токенизирует. Content ID: `9358cad3ec371c8a7e098dfb7e73a9f6a1990d2c8c31bb8f6519cea6380926a3`.

Каждый `data/versions/*.json` связывает source checksum `bd4084611bd27c939ba98e5e63bc3e5a2c1a4e99477dcba46c829e4c986c429d`, preprocessing checksum и split checksum. `dvc.lock` фиксирует deps/outs каждой стадии.

## Известные ограничения

Корпус отражает Wikipedia и конкретный исторический период, а не все современые платформы. Разметка субъективна, классы несбалансированы. Identity terms, цитаты, сарказм, обфускации и контекст могут приводить к systematic errors. Датасет содержит оскорбительный контент и требует осторожного доступа.

## Воспроизведение

```bash
kagglehub login
python scripts/download_data.py
dvc repro prepare_split data_v1 data_v2
dvc status
```
