#!/usr/bin/env sh
set -eu

base_url="${1:-http://127.0.0.1:8000}"
curl --fail --silent --show-error "${base_url}/health"
curl --fail --silent --show-error \
  -H 'Content-Type: application/json' \
  -d '{"text":"You are a disgusting idiot"}' \
  "${base_url}/predict"
status="$(curl --silent --output /tmp/toxicity-invalid.json --write-out '%{http_code}' \
  -H 'Content-Type: application/json' -d '{"text":"   "}' "${base_url}/predict")"
test "$status" = "422"
echo "Smoke test passed"
