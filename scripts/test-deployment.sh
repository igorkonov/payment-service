#!/bin/bash
set -e

echo "==================================="
echo "Payment Service - Deployment Test"
echo "==================================="
echo ""

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}✓${NC} $1"
}

log_error() {
    echo -e "${RED}✗${NC} $1"
}

log_test() {
    echo -e "${YELLOW}→${NC} $1"
}

# Проверка наличия docker-compose.prod.yml
if [ ! -f "docker-compose.prod.yml" ]; then
    log_error "docker-compose.prod.yml не найден!"
    exit 1
fi

log_test "Остановка существующих контейнеров..."
docker compose -f docker-compose.prod.yml down 2>/dev/null || true

log_test "Сборка образа..."
docker compose -f docker-compose.prod.yml build

log_test "Запуск контейнеров..."
docker compose -f docker-compose.prod.yml up -d

log_test "Ожидание запуска сервисов (30 секунд)..."
sleep 30

log_test "Проверка статуса контейнеров..."
docker compose -f docker-compose.prod.yml ps

echo ""
echo "==================================="
echo "Тестирование endpoints"
echo "==================================="
echo ""

# Проверка health endpoint
log_test "Проверка /health..."
HEALTH=$(curl -s http://localhost:8080/health)
if [ "$HEALTH" = "healthy" ]; then
    log_info "Health check: OK"
else
    log_error "Health check: FAILED"
    docker compose -f docker-compose.prod.yml logs nginx
    exit 1
fi

# Проверка главной страницы
log_test "Проверка главной страницы..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/)
if [ "$HTTP_CODE" = "200" ]; then
    log_info "Главная страница: OK (HTTP $HTTP_CODE)"
else
    log_error "Главная страница: FAILED (HTTP $HTTP_CODE)"
    exit 1
fi

# Проверка админки
log_test "Проверка админки..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/admin/)
if [ "$HTTP_CODE" = "302" ] || [ "$HTTP_CODE" = "200" ]; then
    log_info "Админка: OK (HTTP $HTTP_CODE)"
else
    log_error "Админка: FAILED (HTTP $HTTP_CODE)"
    exit 1
fi

# Проверка статики
log_test "Проверка статики..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/static/admin/css/base.css)
if [ "$HTTP_CODE" = "200" ]; then
    log_info "Статика: OK (HTTP $HTTP_CODE)"
else
    log_error "Статика: FAILED (HTTP $HTTP_CODE)"
    exit 1
fi

# Проверка БД
log_test "Проверка подключения к БД..."
DB_STATUS=$(docker compose -f docker-compose.prod.yml exec -T db pg_isready -U postgres)
if echo "$DB_STATUS" | grep -q "accepting connections"; then
    log_info "База данных: OK"
else
    log_error "База данных: FAILED"
    exit 1
fi

# Проверка Gunicorn workers
log_test "Проверка Gunicorn workers..."
WORKERS=$(docker compose -f docker-compose.prod.yml logs web | grep "Booting worker" | wc -l)
if [ "$WORKERS" -ge 4 ]; then
    log_info "Gunicorn workers: OK ($WORKERS workers)"
else
    log_error "Gunicorn workers: FAILED (expected 4, got $WORKERS)"
fi

echo ""
echo "==================================="
log_info "Все тесты пройдены успешно!"
echo "==================================="
echo ""
echo "Приложение доступно по адресу: http://localhost:8080"
echo ""
echo "Для остановки: docker compose -f docker-compose.prod.yml down"
