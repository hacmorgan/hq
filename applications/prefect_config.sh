#!/usr/bin/env bash


# Configure this server as a prefect server


[[ -n "$SERVER_IP" ]] || SERVER_IP="$(cut -d' ' -f3 <<< "$SSH_CONNECTION")"
[[ -n "$SERVER_IP" ]] || {
    echo "Could not get server IP from SSH_CONNECTION env variable" >&2
    exit 1
}


prefect config set \
    PREFECT_API_DATABASE_TIMEOUT=120 \
    PREFECT_API_DATABASE_CONNECTION_TIMEOUT=120 \
    PREFECT_API_REQUEST_TIMEOUT=120 \
    PREFECT_API_URL="http://${SERVER_IP}:42069/api" \
    PREFECT_API_DATABASE_CONNECTION_URL="postgresql+asyncpg://postgres:yourTopSecretPassword@localhost:42070/prefect" \
    PREFECT_SERVER_API_HOST="$SERVER_IP" \
    PREFECT_SERVER_API_PORT="42069" \
    PREFECT_LOGGING_EXTRA_LOGGERS=abyss


sudo docker run -d \
--name prefect-postgres-hamish \
-v DB_VOLUME_NAME:/var/lib/postgresql/data \
-p 42070:5432 \
-e POSTGRES_USER=postgres \
-e POSTGRES_PASSWORD=yourTopSecretPassword \
-e POSTGRES_DB=prefect postgres:latest
