#!/bin/sh
set -e

# Build command arguments from environment variables if no arguments provided
if [ $# -eq 0 ]; then
    exec python racknerd_exporter.py \
        --url "${RACKNERD_URL:-https://nerdvm.racknerd.com}" \
        --username "${RACKNERD_USERNAME}" \
        --password "${RACKNERD_PASSWORD}" \
        --port "${RACKNERD_PORT:-9100}" \
        --log-level "${LOG_LEVEL:-INFO}"
else
    # If arguments provided, use them directly
    exec python racknerd_exporter.py "$@"
fi
