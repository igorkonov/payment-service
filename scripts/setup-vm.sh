#!/bin/bash

# Скрипт для первоначальной настройки VM в Yandex Cloud
# Использование: ./scripts/setup-vm.sh <VM_IP>

set -e

if [ -z "$1" ]; then
    echo "Использование: $0 <VM_IP>"
    echo "Пример: $0 51.250.10.20"
    exit 1
fi

VM_IP=$1
VM_USER="ubuntu"
PROJECT_DIR="/opt/payment-service"

echo "🚀 Начинаем настройку VM: $VM_IP"

# Проверка SSH подключения
echo "📡 Проверка SSH подключения..."
if ! ssh -o ConnectTimeout=5 $VM_USER@$VM_IP "echo 'SSH OK'"; then
    echo "❌ Не удалось подключиться к VM"
    echo "Проверьте:"
    echo "  1. IP адрес правильный"
    echo "  2. SSH ключ добавлен в ssh-agent"
    echo "  3. VM запущена и доступна"
    exit 1
fi

echo "✅ SSH подключение установлено"

# Создание директории проекта
echo "� Созидание директории проекта..."
ssh $VM_USER@$VM_IP "sudo mkdir -p $PROJECT_DIR && sudo chown $VM_USER:$VM_USER $PROJECT_DIR"

# Копирование docker-compose.prod.yml
echo "📦 Копирование docker-compose.prod.yml..."
scp docker-compose.prod.yml $VM_USER@$VM_IP:$PROJECT_DIR/

# Копирование nginx конфигурации
echo "📦 Копирование nginx конфигурации..."
ssh $VM_USER@$VM_IP "mkdir -p $PROJECT_DIR/docker"
scp docker/nginx.conf $VM_USER@$VM_IP:$PROJECT_DIR/docker/

# Создание директории для SSL сертификатов
echo "🔐 Создание директории для SSL..."
ssh $VM_USER@$VM_IP "mkdir -p $PROJECT_DIR/docker/ssl"

# Проверка Docker
echo "🐳 Проверка Docker..."
if ! ssh $VM_USER@$VM_IP "docker --version"; then
    echo "❌ Docker не установлен"
    echo "Запустите: curl -fsSL https://get.docker.com | sh"
    exit 1
fi

echo "✅ Docker установлен"

# Проверка Docker Compose
echo "🐳 Проверка Docker Compose..."
if ! ssh $VM_USER@$VM_IP "docker compose version"; then
    echo "❌ Docker Compose не установлен"
    echo "Запустите: sudo apt-get install docker-compose-plugin"
    exit 1
fi

echo "✅ Docker Compose установлен"

# Создание .env файла (шаблон)
echo "📝 Создание шаблона .env файла..."
ssh $VM_USER@$VM_IP "cat > $PROJECT_DIR/.env.sample << 'EOF'
# Stripe Configuration
STRIPE_PUBLIC_KEY=pk_test_your_key_here
STRIPE_SECRET_KEY=sk_test_your_key_here


# Django Configuration
SECRET_KEY=your-secret-key-here-change-in-production
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1,$VM_IP

# Database Configuration
DB_NAME=payment_db
DB_USER=payment_user
DB_PASSWORD=change_this_password
DB_HOST=db
DB_PORT=5432
EOF
"

echo "⚠️  ВАЖНО: Отредактируйте файл .env на сервере!"
echo "   ssh $VM_USER@$VM_IP"
echo "   cd $PROJECT_DIR"
echo "   cp .env.sample .env"
echo "   nano .env"

# Проверка аутентификации в Container Registry
echo "🔑 Проверка аутентификации в Yandex Container Registry..."
echo "Выполните на VM:"
echo "   cat key.json | docker login cr.yandex -u json_key --password-stdin"

echo ""
echo "✅ Базовая настройка VM завершена!"
echo ""
echo "📋 Следующие шаги:"
echo "   1. Настройте переменные окружения в GitLab CI/CD"
echo "   2. Отредактируйте .env файл на сервере"
echo "   3. Запустите деплой через GitLab CI/CD"
echo ""
echo "🌐 После деплоя приложение будет доступно:"
echo "   http://$VM_IP:8080"
