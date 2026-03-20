# 📦 Торнус Склад

Система учёта склада для малого бизнеса. Курсовая работа.

## Стек

- **FastAPI** — REST API
- **Streamlit** — административная панель
- **PostgreSQL 16** — база данных
- **Docker Compose** — запуск всех сервисов

---

## Быстрый старт

### 1. Клонировать репозиторий

```bash
git clone <url>
cd pro_sklad
```

### 2. Создать файл конфигурации

```bash
cp .env.example .env
```

### 3. Запустить

```bash
docker-compose up --build
```

Первый запуск занимает 2–5 минут (скачивание образов, установка зависимостей).

---

## Доступ к сервисам

| Сервис | URL | Данные для входа |
|--------|-----|-----------------|
| Административная панель | http://localhost:8501 | пароль: `admin123` |
| API документация (Swagger) | http://localhost:8000/docs | — |
| pgAdmin (управление БД) | http://localhost:5050 | `admin@example.com` / `admin` |

### Подключение к БД в pgAdmin

После входа: **Add New Server**
- **Host:** `db`
- **Port:** `5432`
- **Database:** `tornus_sklad`
- **Username:** `tornus`
- **Password:** `tornus_pass`

---

## Управление

```bash
# Остановить
docker-compose down

# Перезапустить после изменений в коде
docker-compose restart api
docker-compose restart dashboard

# Посмотреть логи
docker-compose logs -f api
docker-compose logs -f dashboard

# Полный сброс базы данных (все данные удалятся)
docker-compose down && docker volume rm pro_sklad_postgres_data && docker-compose up --build
```

---

## Функционал

- **Сводка** — остатки, стоимость склада, предупреждения о низком остатке
- **Товары** — добавление, редактирование, удаление позиций
- **Движения** — приход, расход, перемещение, инвентаризация
- **Аналитика** — графики, топ товаров, структура по категориям
- **Импорт** — загрузка товаров из CSV файла
- **Штрих-коды** — генерация PDF (5×6 на листе A4) по всем или выбранным товарам
