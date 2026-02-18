# Руководство по развертыванию RSSTGLite без Docker

Это руководство описывает процесс установки и запуска RSSTGLite на Linux-сервере (например, Ubuntu/Debian) без использования Docker. Этот метод подходит для серверов с ограниченными ресурсами.

## Предварительные требования

*   Сервер с ОС Linux (Ubuntu 20.04+, Debian 10+).
*   Установленный Python 3.8 или выше.
*   Доступ к терминалу (SSH).

## Шаг 1: Подготовка системы

Убедитесь, что система обновлена и установлен Python с пакетным менеджером pip и утилитой для создания виртуальных окружений.

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install python3 python3-pip python3-venv git -y
```

## Шаг 2: Клонирование репозитория

Если вы еще не скачали код проекта, склонируйте его:

```bash
git clone <URL_ВАШЕГО_РЕПОЗИТОРИЯ> rsstglite
cd rsstglite
```
*Замените `<URL_ВАШЕГО_РЕПОЗИТОРИЯ>` на реальный адрес (или просто скопируйте файлы на сервер).*

## Шаг 3: Автоматическая установка (Рекомендуется)

Мы подготовили скрипт `setup.sh`, который автоматически создаст виртуальное окружение, установит зависимости и настроит автозапуск.

1.  Сделайте скрипт исполняемым:
    ```bash
    chmod +x setup.sh
    ```

2.  Запустите скрипт:
    ```bash
    ./setup.sh
    ```

3.  Следуйте инструкциям на экране. Скрипт проверит наличие `config.json` и предложит создать его из примера, если он отсутствует.

## Шаг 4: Ручная установка (Если скрипт не используется)

Если вы предпочитаете настраивать все вручную, выполните следующие шаги:

1.  **Создайте виртуальное окружение:**
    ```bash
    python3 -m venv venv
    ```

2.  **Активируйте окружение:**
    ```bash
    source venv/bin/activate
    ```

3.  **Установите зависимости:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Настройте конфигурацию:**
    Скопируйте пример конфига и отредактируйте его:
    ```bash
    cp sample_config.json config.json
    nano config.json
    ```
    *Вставьте ваш токен бота и настройте RSS-ленты.*

## Шаг 5: Настройка службы Systemd (Автозапуск)

Чтобы бот запускался автоматически при перезагрузке сервера и перезапускался при падении, настроим systemd.

1.  Отредактируйте файл службы (если не использовали `setup.sh`):
    Создайте файл `/etc/systemd/system/rsstglite.service` со следующим содержимым:

    ```ini
    [Unit]
    Description=RSSTGLite Telegram Bot
    After=network.target

    [Service]
    Type=simple
    User=root
    WorkingDirectory=/путь/к/папке/rsstglite
    ExecStart=/путь/к/папке/rsstglite/venv/bin/python3 feedbot.py
    Restart=always
    RestartSec=10

    [Install]
    WantedBy=multi-user.target
    ```
    *Замените `/путь/к/папке/rsstglite` на реальный путь (команда `pwd` покажет текущий путь).*
    *Если запускаете не от root, измените `User=root` на ваше имя пользователя.*

2.  **Активируйте и запустите службу:**
    ```bash
    sudo systemctl daemon-reload
    sudo systemctl enable rsstglite
    sudo systemctl start rsstglite
    ```

## Управление ботом

*   **Проверка статуса:**
    ```bash
    sudo systemctl status rsstglite
    ```

*   **Просмотр логов:**
    ```bash
    sudo journalctl -u rsstglite -f
    ```

*   **Остановка бота:**
    ```bash
    sudo systemctl stop rsstglite
    ```

*   **Перезапуск бота:**
    ```bash
    sudo systemctl restart rsstglite
    ```

## Обновление бота

Чтобы обновить код бота:

```bash
cd rsstglite
git pull
source venv/bin/activate
pip install -r requirements.txt # На случай, если обновились зависимости
sudo systemctl restart rsstglite
```
