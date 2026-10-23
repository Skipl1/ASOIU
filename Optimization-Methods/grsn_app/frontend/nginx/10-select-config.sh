#!/bin/sh
# Выбор режима Nginx перед запуском: HTTP (по умолчанию) или HTTPS (ENABLE_HTTPS=true).
set -e
TARGET=/etc/nginx/conf.d/default.conf

if [ "${ENABLE_HTTPS:-false}" = "true" ]; then
    CERT_DIR=/etc/nginx/certs
    mkdir -p "$CERT_DIR"
    # Если сертификат не смонтирован, создаётся самоподписанный (для учебного стенда).
    # Для боевого сервера положите server.crt и server.key в каталог frontend/nginx/certs.
    if [ ! -f "$CERT_DIR/server.crt" ] || [ ! -f "$CERT_DIR/server.key" ]; then
        echo "Создание самоподписанного TLS-сертификата..."
        openssl req -x509 -nodes -newkey rsa:2048 -days 365 \
            -subj "/C=RU/O=AS GRSN/CN=${SERVER_NAME:-localhost}" \
            -keyout "$CERT_DIR/server.key" -out "$CERT_DIR/server.crt" >/dev/null 2>&1
    fi
    sed "s/__HTTPS_PUBLIC_PORT__/${HTTPS_PUBLIC_PORT:-443}/" /etc/nginx/grsn/https.conf > "$TARGET"
    echo "Режим HTTPS"
else
    cp /etc/nginx/grsn/http.conf "$TARGET"
    echo "Режим HTTP (HTTPS отключён)"
fi
