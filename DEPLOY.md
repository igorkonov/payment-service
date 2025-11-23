# Deployment Guide

Руководство по деплою Payment Service на production сервер.

## Требования

- Docker и docker-compose
- Доменное имя (опционально)
- SSL сертификаты (рекомендуется)

## Подготовка сервера

### 1. Установка Docker

```bash
# Ubuntu/Debian
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Установка docker-compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

### 2. Клонирование репозитория

```bash
git clone https://github.com/yourusername/payment-service.git
cd payment-service
```

### 3. Настройка переменных окружения

```bash
cp .env.sample .env
nano .env
```

Обязательно измените:

```env
SECRET_KEY=your-strong-secret-key-here
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
DB_PASSWORD=strong-database-password
```

Сгенерировать SECRET_KEY:

```bash
python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
```

## Деплой

### Production с nginx

```bash
docker-compose -f docker-compose.prod.yml up -d --build
```

### Создание суперпользователя

```bash
docker-compose -f docker-compose.prod.yml exec web python manage.py createsuperuser
```

### Проверка логов

```bash
docker-compose -f docker-compose.prod.yml logs -f
```

## SSL сертификаты (Let's Encrypt)

### 1. Установка certbot

```bash
sudo apt-get update
sudo apt-get install certbot
```

### 2. Получение сертификата

```bash
sudo certbot certonly --standalone -d yourdomain.com -d www.yourdomain.com
```

### 3. Копирование сертификатов

```bash
mkdir -p docker/ssl
sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem docker/ssl/cert.pem
sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem docker/ssl/key.pem
sudo chown $USER:$USER docker/ssl/*
```

### 4. Раскомментировать HTTPS блок в nginx.conf

Откройте `docker/nginx.conf` и раскомментируйте секцию HTTPS server.

### 5. Перезапуск

```bash
docker-compose -f docker-compose.prod.yml restart nginx
```

## Обновление приложения

```bash
git pull origin main
docker-compose -f docker-compose.prod.yml up -d --build
docker-compose -f docker-compose.prod.yml exec web python manage.py migrate
docker-compose -f docker-compose.prod.yml exec web python manage.py collectstatic --noinput
```

## Бэкап базы данных

### Создание бэкапа

```bash
docker-compose -f docker-compose.prod.yml exec db pg_dump -U postgres stripe_payment > backup_$(date +%Y%m%d_%H%M%S).sql
```

### Восстановление из бэкапа

```bash
docker-compose -f docker-compose.prod.yml exec -T db psql -U postgres stripe_payment < backup_20231122_120000.sql
```

## Мониторинг

### Проверка статуса контейнеров

```bash
docker-compose -f docker-compose.prod.yml ps
```

### Использование ресурсов

```bash
docker stats
```

### Health check

```bash
curl http://localhost/health
```

## Безопасность

### Firewall (UFW)

```bash
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

**ВАЖНО:** Порт 5432 (PostgreSQL) НЕ открывайте! БД доступна только внутри Docker сети.

### Безопасность базы данных

PostgreSQL настроен безопасно по умолчанию:
- Нет проброса портов наружу
- Доступ только из Docker сети
- Сильная аутентификация (scram-sha-256)

Для удаленного доступа используйте SSH туннель:

```bash
ssh -L 5433:localhost:5432 user@your-server.com
psql -h localhost -p 5433 -U postgres -d stripe_payment
```

Подробнее: [docker/postgres/README.md](docker/postgres/README.md)

### Автоматическое обновление SSL

Добавьте в crontab:

```bash
0 0 1 * * certbot renew --quiet && cp /etc/letsencrypt/live/yourdomain.com/*.pem /path/to/docker/ssl/ && docker-compose -f /path/to/docker-compose.prod.yml restart nginx
```

## Troubleshooting

### Контейнер не запускается

```bash
docker-compose -f docker-compose.prod.yml logs web
```

### База данных недоступна

```bash
docker-compose -f docker-compose.prod.yml exec db psql -U postgres -c "SELECT 1"
```

### Проблемы с правами

```bash
docker-compose -f docker-compose.prod.yml exec web ls -la /app
```

## Полезные команды

```bash
# Остановить все контейнеры
docker-compose -f docker-compose.prod.yml down

# Удалить все данные (включая volumes)
docker-compose -f docker-compose.prod.yml down -v

# Пересобрать образы
docker-compose -f docker-compose.prod.yml build --no-cache

# Войти в контейнер
docker-compose -f docker-compose.prod.yml exec web bash
```
