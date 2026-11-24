# Сценарий демо-видео, 1–3 минуты

## Подготовка

```bash
git checkout v1.2.0
docker compose down --remove-orphans
```

Откройте terminal крупным шрифтом. Не показывайте tokens, `.env` и другие секреты.

## 0:00–0:20 — версия

```bash
git describe --tags --exact-match
git rev-parse HEAD
```

Скажите: «Это фиксированная версия. Модель, config, Dockerfile и lock-файлы относятся к одному commit».

## 0:20–0:55 — сборка и запуск

```bash
docker compose up --build --detach --wait --wait-timeout 120
docker compose ps
```

Скажите: «API-образ собирается из фиксированного Python image, зависимости проверяются по SHA-256, процесс работает не от root».

## 0:55–1:20 — health и docs

```bash
curl -sS http://localhost:8000/health
```

Покажите `status=ready`, model/data version и SHA-256. Откройте <http://localhost:8000/docs>.

## 1:20–1:45 — корректный predict

```bash
curl -sS -X POST http://localhost:8000/predict \
  -H 'Content-Type: application/json' \
  -d '{"text":"You are a disgusting idiot"}'
```

Покажите probability, threshold, model/data version и latency.

## 1:45–2:05 — контролируемая ошибка

```bash
curl -i -sS -X POST http://localhost:8000/predict \
  -H 'Content-Type: application/json' \
  -d '{"text":"   "}'
```

Покажите HTTP `422` и сообщение валидации.

## 2:05–2:30 — UI и завершение

Откройте <http://localhost:8501>, введите текст и покажите ответ с версией. Закончите:

```bash
docker compose down
```

Если сборка долгая, ускорьте её в монтаже, но оставьте видимыми начало и успешное завершение.
