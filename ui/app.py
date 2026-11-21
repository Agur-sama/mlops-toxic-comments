from __future__ import annotations

import os

import requests
import streamlit as st

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")

st.set_page_config(page_title="Toxicity Classifier", page_icon="🛡️", layout="centered")
st.title("🛡️ Классификатор токсичных комментариев")
st.caption("Интерфейс обращается к версионированному FastAPI, а не загружает модель сам.")

text = st.text_area(
    "Англоязычный комментарий",
    placeholder="Type a comment...",
    height=160,
    max_chars=5000,
)

if st.button("Проверить", type="primary", use_container_width=True):
    if not text.strip():
        st.warning("Введите непустой текст.")
    else:
        try:
            response = requests.post(
                f"{API_BASE_URL}/predict",
                json={"text": text},
                timeout=10,
            )
            response.raise_for_status()
            result = response.json()
            if result["toxic"]:
                st.error(f"Токсичный комментарий: {result['probability']:.1%}")
            else:
                st.success(f"Нетоксичный комментарий: {1 - result['probability']:.1%}")
            st.progress(float(result["probability"]), text="Оценка токсичности")
            st.caption(
                f"Модель: {result['model_version']} · "
                f"Данные: {result['data_version']} · "
                f"Задержка: {result['latency_ms']:.1f} мс"
            )
        except requests.HTTPError as exc:
            detail = exc.response.json().get("detail", exc.response.text)
            st.error(f"Сервис отклонил запрос: {detail}")
        except requests.RequestException as exc:
            st.error(f"Сервис недоступен: {exc}")
