# Используем конкретную версию Python (не latest)
FROM python:3.13-slim-bookworm AS builder

# Устанавливаем переменные окружения
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Устанавливаем системные зависимости для сборки
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Устанавливаем uv для управления зависимостями
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Копируем файлы зависимостей
WORKDIR /app
COPY pyproject.toml uv.lock ./

# Устанавливаем зависимости в виртуальное окружение
RUN uv sync --frozen

# Runtime stage
FROM python:3.13-slim-bookworm

# Устанавливаем переменные окружения
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH"

# Устанавливаем только runtime зависимости
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    netcat-openbsd \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Создаем непривилегированного пользователя
RUN groupadd -r django && useradd -r -g django django

# Создаем необходимые директории
WORKDIR /app
RUN mkdir -p /app/staticfiles /app/mediafiles && \
    chown -R django:django /app

# Копируем виртуальное окружение из builder
COPY --from=builder --chown=django:django /app/.venv /app/.venv

# Копируем код приложения
COPY --chown=django:django . .

# Копируем и настраиваем entrypoint
COPY --chown=django:django docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Переключаемся на непривилегированного пользователя
USER django

# Expose порт
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/admin/login/ || exit 1

# Entrypoint
ENTRYPOINT ["/entrypoint.sh"]

# Команда по умолчанию
CMD ["gunicorn", "stripe_payment.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4", "--timeout", "60"]
