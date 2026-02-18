#!/bin/bash

# Цвета для вывода
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Установка RSSTGLite (без Docker) ===${NC}"

# 1. Проверка Python
echo -e "\n${YELLOW}[1/5] Проверка Python...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Python 3 не найден! Пожалуйста, установите его:${NC}"
    echo "sudo apt update && sudo apt install python3 python3-venv python3-pip -y"
    exit 1
fi
echo "Python 3 найден: $(python3 --version)"

# 2. Создание виртуального окружения
echo -e "\n${YELLOW}[2/5] Настройка виртуального окружения...${NC}"
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "Виртуальное окружение создано."
else
    echo "Виртуальное окружение уже существует."
fi

# 3. Установка зависимостей
echo -e "\n${YELLOW}[3/5] Установка зависимостей...${NC}"
source venv/bin/activate
pip install --upgrade pip
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
    echo "Зависимости установлены."
else
    echo -e "${RED}Файл requirements.txt не найден!${NC}"
    exit 1
fi

# 4. Настройка конфигурации
echo -e "\n${YELLOW}[4/5] Проверка конфигурации...${NC}"
if [ ! -f "config.json" ]; then
    if [ -f "sample_config.json" ]; then
        cp sample_config.json config.json
        echo -e "${GREEN}Создан config.json из примера.${NC}"
        echo -e "${YELLOW}ВАЖНО: Пожалуйста, отредактируйте config.json и вставьте ваш токен перед запуском!${NC}"
        echo "Команда для редактирования: nano config.json"
        read -p "Нажмите Enter, чтобы продолжить..."
    else
        echo -e "${RED}Не найден ни config.json, ни sample_config.json!${NC}"
        exit 1
    fi
else
    echo "config.json уже существует."
fi

# 5. Создание службы Systemd
echo -e "\n${YELLOW}[5/5] Настройка автозапуска (Systemd)...${NC}"
read -p "Хотите настроить автозапуск через systemd? (y/n): " setup_service

if [[ "$setup_service" =~ ^[Yy]$ ]]; then
    SERVICE_NAME="rsstglite"
    CURRENT_DIR=$(pwd)
    USER_NAME=$(whoami)
    SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

    echo "Создание файла службы $SERVICE_FILE..."

    # Создаем временный файл службы
    cat <<EOF > ${SERVICE_NAME}.service
[Unit]
Description=RSSTGLite Telegram Bot
After=network.target

[Service]
Type=simple
User=${USER_NAME}
WorkingDirectory=${CURRENT_DIR}
ExecStart=${CURRENT_DIR}/venv/bin/python3 feedbot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

    echo "Требуются права sudo для копирования файла службы и активации..."
    sudo mv ${SERVICE_NAME}.service $SERVICE_FILE
    sudo systemctl daemon-reload
    sudo systemctl enable $SERVICE_NAME
    
    echo -e "${GREEN}Служба установлена и включена!${NC}"
    echo "Команды для управления:"
    echo "  Запуск: sudo systemctl start $SERVICE_NAME"
    echo "  Статус: sudo systemctl status $SERVICE_NAME"
    echo "  Логи:   sudo journalctl -u $SERVICE_NAME -f"
else
    echo "Пропуск настройки systemd."
fi

echo -e "\n${GREEN}=== Установка завершена! ===${NC}"
echo "Для ручного запуска используйте:"
echo "source venv/bin/activate"
echo "python3 feedbot.py"
