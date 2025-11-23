# PostgreSQL Security Configuration

## Базовая безопасность (по умолчанию)

По умолчанию PostgreSQL настроен безопасно:

- ✅ **Нет проброса портов** - БД доступна только внутри Docker сети
- ✅ **Сильная аутентификация** - scram-sha-256 вместо md5
- ✅ **Ограничение ресурсов** - CPU и memory limits
- ✅ **Минимальные привилегии** - dropped capabilities

## Удаленный доступ через SSH туннель

Для безопасного удаленного доступа используйте SSH туннель:

```bash
# На вашей локальной машине
ssh -L 5433:localhost:5432 user@your-server.com

# Теперь подключайтесь к localhost:5433
psql -h localhost -p 5433 -U postgres -d stripe_payment
```

## SSL/TLS шифрование (опционально)

### 1. Генерация сертификатов

```bash
cd docker/postgres
./generate-ssl-certs.sh
```

### 2. Включение SSL в postgresql.conf

Раскомментируйте строки SSL в `postgresql.conf`:

```conf
ssl = on
ssl_cert_file = '/var/lib/postgresql/certs/server.crt'
ssl_key_file = '/var/lib/postgresql/certs/server.key'
ssl_ca_file = '/var/lib/postgresql/certs/ca.crt'
```

### 3. Обновите docker-compose.prod.yml

Добавьте volume для сертификатов:

```yaml
volumes:
  - ./docker/postgres/certs:/var/lib/postgresql/certs:ro
```

### 4. Настройте Django для SSL

В `.env` добавьте:

```env
DB_SSLMODE=require
```

В `settings.py`:

```python
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("DB_NAME"),
        "USER": os.getenv("DB_USER"),
        "PASSWORD": os.getenv("DB_PASSWORD"),
        "HOST": os.getenv("DB_HOST"),
        "PORT": os.getenv("DB_PORT"),
        "OPTIONS": {
            "sslmode": os.getenv("DB_SSLMODE", "prefer"),
        },
    }
}
```

### 5. Перезапустите контейнеры

```bash
docker-compose -f docker-compose.prod.yml restart db
```

## Почему порт 5432 не пробрасывается?

1. **Уменьшение attack surface** - злоумышленники не могут сканировать порт
2. **Защита от brute-force** - нет прямого доступа к БД извне
3. **Compliance** - соответствие PCI DSS для платежных систем
4. **Defense in depth** - дополнительный уровень защиты

## Best Practices

- ✅ Используйте сильные пароли (20+ символов)
- ✅ Регулярно обновляйте PostgreSQL
- ✅ Делайте бэкапы
- ✅ Мониторьте логи на подозрительную активность
- ✅ Используйте SSL для production
- ✅ Ограничивайте доступ через pg_hba.conf
- ✅ Не храните пароли в коде - только в .env

## Проверка безопасности

```bash
# Проверить что порт не открыт наружу
nmap -p 5432 your-server.com

# Проверить SSL соединение
psql "sslmode=require host=db port=5432 user=postgres dbname=stripe_payment"

# Проверить текущие подключения
docker-compose -f docker-compose.prod.yml exec db psql -U postgres -c "SELECT * FROM pg_stat_activity;"
```
