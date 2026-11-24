FROM python:3.12.7-slim-bookworm@sha256:60d9996b6a8a3689d36db740b49f4327be3be09a21122bd02fb8895abb38b50d

ARG APP_VERSION=dev
ARG VCS_REF=unknown
LABEL org.opencontainers.image.title="toxic-comment-api" \
      org.opencontainers.image.version="${APP_VERSION}" \
      org.opencontainers.image.revision="${VCS_REF}"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app/src \
    TOXICITY_CONFIG_PATH=/app/config/default.yaml \
    TOXICITY_MODEL_PATH=/app/artifacts/models/tfidf_logreg_preprocess_standard.joblib \
    TOXICITY_METADATA_PATH=/app/artifacts/models/model_metadata.json

RUN groupadd --gid 10001 app && \
    useradd --uid 10001 --gid app --create-home --shell /usr/sbin/nologin app

WORKDIR /app
COPY requirements-runtime.lock ./requirements-runtime.lock
RUN python -m pip install --no-cache-dir --require-hashes -r requirements-runtime.lock

COPY src ./src
COPY config ./config
COPY artifacts/models/tfidf_logreg_preprocess_standard.joblib ./artifacts/models/
COPY artifacts/models/model_metadata.json ./artifacts/models/

RUN chown -R app:app /app
USER 10001:10001

EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=3s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)"

CMD ["uvicorn", "toxicity.api:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
