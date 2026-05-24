# Инструкция по деплою на VPS

## Требования к серверу
- Ubuntu 22.04 / Debian 12
- Docker + Docker Compose v2
- Открытые порты: `8000`, `8501`, `5050`

## 1. Установка Docker

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
# Перелогиниться или выполнить:
newgrp docker
```

## 2. Клонирование проекта

```bash
git clone https://github.com/utka0047/pro_sklad.git
cd pro_sklad
```

## 3. Настройка переменных окружения

```bash
cp .env.example .env
nano .env
```

Заполнить `.env`:
```
POSTGRES_DB=tornus_sklad
POSTGRES_USER=tornus
POSTGRES_PASSWORD=YOUR_STRONG_PASSWORD
DATABASE_URL=postgresql://tornus:YOUR_STRONG_PASSWORD@db:5432/tornus_sklad
API_URL=http://api:8000
DASHBOARD_PASSWORD=YOUR_DASHBOARD_PASSWORD
```

> Смените пароли на надёжные — сервисы будут открыты в интернет.

## 4. Запуск

```bash
docker compose up -d --build
```

Первый запуск занимает 2–5 минут (скачивание образов, установка зависимостей).

## 5. Проверка

```bash
docker compose ps
```

Все контейнеры должны быть в статусе `Up`:
- `tornus_db` — healthy
- `tornus_api`
- `tornus_dashboard`
- `tornus_pgadmin`

Сервисы доступны по адресам:

| Сервис | URL |
|--------|-----|
| API + Swagger | `http://YOUR_IP:8000/docs` |
| Dashboard | `http://YOUR_IP:8501` |
| pgAdmin | `http://YOUR_IP:5050` |

## 6. Обновление проекта

```bash
cd pro_sklad
git pull origin main
docker compose down
docker compose up -d --build
```

> `.env` файл не хранится в git — при пересоздании директории его нужно создать заново.

## 7. Полезные команды

```bash
# Логи сервиса
docker compose logs -f api
docker compose logs -f dashboard

# Перезапуск одного сервиса
docker compose restart api

# Сброс базы данных (удалит все данные!)
docker compose down
docker volume rm pro_sklad_postgres_data
docker compose up -d --build
```

## Важные замечания

- **PostgreSQL** не проброшен наружу — доступен только внутри Docker-сети. Это намеренно.
- **FastAPI** не имеет авторизации — API открыт для всех. Если нужна защита, поставьте nginx с Basic Auth перед портом 8000.
- **Streamlit** защищён паролем из `DASHBOARD_PASSWORD`.
- **pgAdmin** — логин `admin@example.com`, пароль из `PGADMIN_DEFAULT_PASSWORD` (по умолчанию `admin`). Смените в `docker-compose.yml` перед деплоем.
