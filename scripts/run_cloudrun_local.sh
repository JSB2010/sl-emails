#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IMAGE_NAME="${IMAGE_NAME:-sl-emails-local}"
HOST_PORT="${PORT:-8080}"
CONTAINER_PORT=8080
ENV_FILE="${ENV_FILE:-$ROOT_DIR/.env.local}"
ADC_SOURCE="${GOOGLE_APPLICATION_CREDENTIALS:-$HOME/.config/gcloud/application_default_credentials.json}"
ADC_TARGET="/var/run/google/application_default_credentials.json"

if ! command -v docker >/dev/null 2>&1; then
  echo "docker is required to run the Cloud Run container locally." >&2
  exit 1
fi

docker build -t "$IMAGE_NAME" "$ROOT_DIR"

run_args=(
  --rm
  -it
  -p "${HOST_PORT}:${CONTAINER_PORT}"
  -e "PORT=${CONTAINER_PORT}"
  -e "EMAILS_LOCAL_DEV=1"
)

if [[ -f "$ENV_FILE" ]]; then
  run_args+=(--env-file "$ENV_FILE")
else
  echo "warning: env file not found at $ENV_FILE; relying on current shell env." >&2
fi

if [[ -f "$ADC_SOURCE" ]]; then
  run_args+=(
    -e "GOOGLE_APPLICATION_CREDENTIALS=${ADC_TARGET}"
    -v "${ADC_SOURCE}:${ADC_TARGET}:ro"
  )
fi

env_file_has() {
  local key="$1"
  [[ -f "$ENV_FILE" ]] && grep -Eq "^${key}=" "$ENV_FILE"
}

if [[ -z "${GOOGLE_OAUTH_CALLBACK_URL:-}" ]] && ! env_file_has "GOOGLE_OAUTH_CALLBACK_URL"; then
  run_args+=(-e "GOOGLE_OAUTH_CALLBACK_URL=http://localhost:${HOST_PORT}/auth/google/callback")
fi

if [[ -z "${EMAILS_SESSION_SECRET:-}" ]] && ! env_file_has "EMAILS_SESSION_SECRET"; then
  run_args+=(-e "EMAILS_SESSION_SECRET=local-dev-session-secret")
fi

if [[ -z "${EMAILS_AUTOMATION_KEY:-}" ]] && ! env_file_has "EMAILS_AUTOMATION_KEY"; then
  run_args+=(-e "EMAILS_AUTOMATION_KEY=local-dev-automation-key")
fi

echo "Starting local Cloud Run container on http://localhost:${HOST_PORT}"
echo "Image: ${IMAGE_NAME}"
echo "Env file: ${ENV_FILE}"

if [[ ! -f "$ADC_SOURCE" ]]; then
  echo "warning: ADC credentials not found at $ADC_SOURCE." >&2
  echo "warning: provide FIREBASE_SERVICE_ACCOUNT_JSON, FIRESTORE_EMULATOR_HOST, or local ADC if you need Firestore access." >&2
fi

exec docker run "${run_args[@]}" "$IMAGE_NAME"
