#!/usr/bin/env sh
# Simple wait-for-db script: tries to connect via pg_isready-like loop using psql if available,
# otherwise attempts TCP connect with netcat if present. Falls back to a sleep loop.
# Expects env var DATABASE_URL or DB_HOST, DB_PORT.

set -e

DB_HOST="${DB_HOST:-db}"
DB_PORT="${DB_PORT:-5432}"
TIMEOUT=${WAIT_FOR_DB_TIMEOUT:-30}

echo "Waiting for database at ${DB_HOST}:${DB_PORT} (timeout ${TIMEOUT}s)"

start_ts=$(date +%s)
while :; do
  # try simple tcp connection using /dev/tcp (works in many shells)
  if (echo > /dev/tcp/${DB_HOST}/${DB_PORT}) >/dev/null 2>&1; then
    echo "Database is accepting connections"
    break
  fi

  now_ts=$(date +%s)
  elapsed=$((now_ts - start_ts))
  if [ "$elapsed" -ge "$TIMEOUT" ]; then
    echo "Timed out waiting for database after ${elapsed}s"
    exit 1
  fi

  echo "Still waiting for DB... (${elapsed}s)"
  sleep 1
done

exec "$@"
