# Деплой проекта на сервер

## Сервер
- IP: `213.21.252.154`
- Пользователь: `utka`
- Директория проекта: `/home/utka/pro_sklad`

## Что было сделано

### Первый деплой
Проект клонирован с GitHub через HTTPS (SSH-ключ сервера не был добавлен в GitHub):
```bash
git clone https://github.com/utka0047/pro_sklad.git /home/utka/pro_sklad
```

Создан `.env` файл вручную (в репозитории его нет):
```
POSTGRES_DB=tornus_sklad
POSTGRES_USER=tornus
POSTGRES_PASSWORD=tornus_pass_prod
DATABASE_URL=postgresql://tornus:tornus_pass_prod@db:5432/tornus_sklad
API_URL=http://api:8000
DASHBOARD_PASSWORD=admin123
```

Запуск контейнеров:
```bash
docker compose up -d --build
```

### Повторный деплой (обновление)
```bash
cd /home/utka/pro_sklad
git pull origin main
docker compose down
docker compose up -d --build
```

## Проблемы и решения

**`git pull` падал** — папки `.git/objects/` были созданы от `root` (из-за предыдущего деплоя через `sudo`). Без `sudo` поменять права нельзя. Решение: удалить директорию и склонировать заново.

**`docker-compose` не найден** — на сервере установлен Docker Compose v2, команда `docker-compose` не работает. Нужно использовать `docker compose` (через пробел).

## Запущенные сервисы

| Сервис | Порт | URL |
|--------|------|-----|
| FastAPI | 8000 | http://213.21.252.154:8000 |
| Streamlit | 8501 | http://213.21.252.154:8501 |
| pgAdmin | 5050 | http://213.21.252.154:5050 |
| PostgreSQL | — | внутри Docker-сети, снаружи недоступен |
