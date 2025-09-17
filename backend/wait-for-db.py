#!/usr/bin/env python3
"""Simple DB wait script using psycopg2 to attempt connections.
Reads DB host/port from env or DATABASE_URL and retries until timeout.
"""
import os
import time
import sys
from urllib.parse import urlparse

timeout = int(os.environ.get("WAIT_FOR_DB_TIMEOUT", "60"))
start = time.time()

database_url = os.environ.get("DATABASE_URL")
if database_url:
    parsed = urlparse(database_url)
    host = parsed.hostname or os.environ.get("DB_HOST", "db")
    port = parsed.port or int(os.environ.get("DB_PORT", "5432"))
    user = parsed.username
    password = parsed.password
    dbname = parsed.path.lstrip("/")
else:
    host = os.environ.get("DB_HOST", "db")
    port = int(os.environ.get("DB_PORT", "5432"))
    user = os.environ.get("POSTGRES_USER", "postgres")
    password = os.environ.get("POSTGRES_PASSWORD", "postgres")
    dbname = os.environ.get("POSTGRES_DB", "sista")

print(f"Waiting for database at {host}:{port} (timeout {timeout}s)")

while True:
    try:
        import psycopg2
        conn = psycopg2.connect(host=host, port=port, user=user, password=password, dbname=dbname, connect_timeout=3)
        conn.close()
        print("Database is available")
        break
    except Exception as e:
        elapsed = int(time.time() - start)
        if elapsed >= timeout:
            print(f"Timed out after {elapsed}s waiting for DB: {e}")
            sys.exit(1)
        if elapsed % 5 == 0:
            print(f"Still waiting for DB... ({elapsed}s)")
        time.sleep(1)

sys.exit(0)
