#!/bin/bash

# Автоматизированный скрипт настройки Yandex Cloud инфраструктуры
# Использование: ./scripts/yc-setup.sh

set -e

echo "🚀 Настройка инфраструктуры в Yandex Cloud"
echo ""

# Проверка установки yc CLI
if ! command -v yc &> /dev/null; then
    echo "❌ Yandex Cloud CLI не установлен"
    echo "Установите: curl -sSL https://storage.yandexcloud.net/yandexcloud-yc/install.sh | bash"
    exit 1
fi

echo "✅ Yandex Cloud CLI установлен"

# Проверка аутентификации
if ! yc config list &> /dev/null; then
    echo "❌ Yandex Cloud CLI не настроен"
    echo "Запустите: yc init"
    exit 1
fi

echo "✅ Yandex Cloud CLI настроен"

# Получение текущего folder-id
FOLDER_ID=$(yc config get folder-id)
echo "📁 Используется folder: $FOLDER_ID"

# Создание Container Registry
echo ""
echo "📦 Создание Container Registry..."
REGISTRY_NAME="payment-service-registry"

if yc container registry get --name $REGISTRY_NAME &> /dev/null; then
    echo "⚠️  Registry '$REGISTRY_NAME' уже существует"
    REGISTRY_ID=$(yc container registry get --name $REGISTRY_NAME --format json | jq -r '.id')
else
    yc container registry create --name $REGISTRY_NAME
    REGISTRY_ID=$(yc container registry get --name $REGISTRY_NAME --format json | jq -r '.id')
    echo "✅ Registry создан: $REGISTRY_ID"
fi

# Создание Service Account
echo ""
echo "👤 Создание Service Account..."
SA_NAME="gitlab-ci-sa"

if yc iam service-account get --name $SA_NAME &> /dev/null; then
    echo "⚠️  Service Account '$SA_NAME' уже существует"
    SA_ID=$(yc iam service-account get --name $SA_NAME --format json | jq -r '.id')
else
    yc iam service-account create \
        --name $SA_NAME \
        --description "Service account for GitLab CI/CD"
    SA_ID=$(yc iam service-account get --name $SA_NAME --format json | jq -r '.id')
    echo "✅ Service Account создан: $SA_ID"
fi

# Назначение ролей
echo ""
echo "🔑 Назначение ролей..."

yc resource-manager folder add-access-binding $FOLDER_ID \
    --role container-registry.images.pusher \
    --subject serviceAccount:$SA_ID \
    2>/dev/null || echo "⚠️  Роль pusher уже назначена"

yc resource-manager folder add-access-binding $FOLDER_ID \
    --role container-registry.images.puller \
    --subject serviceAccount:$SA_ID \
    2>/dev/null || echo "⚠️  Роль puller уже назначена"

echo "✅ Роли назначены"

# Создание ключа
echo ""
echo "🔐 Создание ключа для Service Account..."
KEY_FILE="yc-sa-key.json"

if [ -f "$KEY_FILE" ]; then
    echo "⚠️  Файл ключа уже существует: $KEY_FILE"
    read -p "Пересоздать ключ? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm $KEY_FILE
        yc iam key create \
            --service-account-name $SA_NAME \
            --output $KEY_FILE
        echo "✅ Новый ключ создан: $KEY_FILE"
    fi
else
    yc iam key create \
        --service-account-name $SA_NAME \
        --output $KEY_FILE
    echo "✅ Ключ создан: $KEY_FILE"
fi

# Генерация SSH ключа
echo ""
echo "🔑 Генерация SSH ключа..."
SSH_KEY_FILE="$HOME/.ssh/yc_gitlab_ci"

if [ -f "$SSH_KEY_FILE" ]; then
    echo "⚠️  SSH ключ уже существует: $SSH_KEY_FILE"
else
    ssh-keygen -t ed25519 -C "gitlab-ci" -f $SSH_KEY_FILE -N ""
    echo "✅ SSH ключ создан: $SSH_KEY_FILE"
fi

# Создание VM
echo ""
echo "💻 Создание виртуальной машины..."
VM_NAME="payment-service-vm"

if yc compute instance get --name $VM_NAME &> /dev/null; then
    echo "⚠️  VM '$VM_NAME' уже существует"
    VM_IP=$(yc compute instance get --name $VM_NAME --format json | jq -r '.network_interfaces[0].primary_v4_address.one_to_one_nat.address')
else
    # Получение ID подсети по умолчанию
    SUBNET_ID=$(yc vpc subnet list --format json | jq -r '.[0].id')

    yc compute instance create \
        --name $VM_NAME \
        --zone ru-central1-a \
        --network-interface subnet-id=$SUBNET_ID,nat-ip-version=ipv4 \
        --create-boot-disk image-folder-id=standard-images,image-family=ubuntu-2204-lts,size=30 \
        --memory 4 \
        --cores 2 \
        --core-fraction 100 \
        --ssh-key $SSH_KEY_FILE.pub \
        --service-account-name $SA_NAME \
        --metadata-from-file user-data=scripts/cloud-init.yaml

    echo "⏳ Ожидание запуска VM..."
    sleep 30

    VM_IP=$(yc compute instance get --name $VM_NAME --format json | jq -r '.network_interfaces[0].primary_v4_address.one_to_one_nat.address')
    echo "✅ VM создана с IP: $VM_IP"
fi

# Итоговая информация
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Настройка завершена!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📋 Информация для GitLab CI/CD переменных:"
echo ""
echo "YC_REGISTRY_ID=$REGISTRY_ID"
echo "YC_VM_IP=$VM_IP"
echo ""
echo "YC_SA_KEY (содержимое файла):"
echo "cat $KEY_FILE"
echo ""
echo "YC_SSH_PRIVATE_KEY (содержимое файла):"
echo "cat $SSH_KEY_FILE"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📝 Следующие шаги:"
echo ""
echo "1. Добавьте переменные в GitLab CI/CD:"
echo "   Settings → CI/CD → Variables"
echo ""
echo "2. Настройте VM:"
echo "   ./scripts/setup-vm.sh $VM_IP"
echo ""
echo "3. Запустите деплой через GitLab CI/CD"
echo ""
echo "🌐 После деплоя приложение будет доступно:"
echo "   http://$VM_IP:8080"
echo ""
