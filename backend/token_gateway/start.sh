#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-/app/backend}"

HOST=${GATEWAY_HOST:-0.0.0.0}
PORT=${GATEWAY_PORT:-9099}

exec uvicorn token_gateway.app:app --host "${HOST}" --port "${PORT}"

