#!/bin/bash
set -e

# Скрипт для генерации SSL сертификатов для PostgreSQL

CERTS_DIR="./docker/postgres/certs"
mkdir -p "$CERTS_DIR"

echo "Генерация SSL сертификатов для PostgreSQL..."

# Генерация приватного ключа CA
openssl genrsa -out "$CERTS_DIR/ca.key" 4096

# Генерация самоподписанного CA сертификата
openssl req -new -x509 -days 3650 -key "$CERTS_DIR/ca.key" -out "$CERTS_DIR/ca.crt" \
    -subj "/C=RU/ST=Moscow/L=Moscow/O=Payment Service/OU=Database/CN=PostgreSQL CA"

# Генерация приватного ключа сервера
openssl genrsa -out "$CERTS_DIR/server.key" 4096

# Генерация запроса на подпись сертификата (CSR)
openssl req -new -key "$CERTS_DIR/server.key" -out "$CERTS_DIR/server.csr" \
    -subj "/C=RU/ST=Moscow/L=Moscow/O=Payment Service/OU=Database/CN=db"

# Подпись сертификата сервера с помощью CA
openssl x509 -req -days 3650 -in "$CERTS_DIR/server.csr" \
    -CA "$CERTS_DIR/ca.crt" -CAkey "$CERTS_DIR/ca.key" -CAcreateserial \
    -out "$CERTS_DIR/server.crt"

# Установка правильных прав доступа
chmod 600 "$CERTS_DIR/server.key"
chmod 644 "$CERTS_DIR/server.crt"
chmod 644 "$CERTS_DIR/ca.crt"

# Удаление временных файлов
rm -f "$CERTS_DIR/server.csr" "$CERTS_DIR/ca.srl"

echo "✓ SSL сертификаты успешно созданы в $CERTS_DIR"
echo ""
echo "Файлы:"
echo "  - ca.crt       (CA сертификат)"
echo "  - server.crt   (Сертификат сервера)"
echo "  - server.key   (Приватный ключ сервера)"
echo ""
echo "ВАЖНО: Добавьте docker/postgres/certs/ в .gitignore!"
