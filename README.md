# 📦 Торнус Склад

Система учёта склада для малого бизнеса. Курсовая работа.

## Стек

- **FastAPI** — REST API
- **Streamlit** — административная панель
- **PostgreSQL 16** — база данных
- **Docker Compose** — запуск всех сервисов

---

## 🖥️ Запуск на локальной машине

### Требования

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (включает Docker и Docker Compose)
- Git

### Шаги

**1. Клонировать репозиторий**

```bash
git clone <url>
cd pro_sklad
```

**2. Создать файл конфигурации**

```bash
cp .env.example .env
```

**3. Запустить**

```bash
docker-compose up --build
```

Первый запуск занимает 2–5 минут — скачиваются образы и устанавливаются зависимости.

**4. Открыть в браузере**

| Сервис | URL | Вход |
|--------|-----|------|
| Административная панель | http://localhost:8501 | пароль: `admin123` |
| API (Swagger) | http://localhost:8000/docs | — |
| pgAdmin | http://localhost:5050 | `admin@example.com` / `admin` |

---

## 🌐 Запуск на VPS (Ubuntu/Debian)

### Требования

- VPS с Ubuntu 22.04 / Debian 12
- Открытые порты: `8501`, `8000`, `5050` (в настройках firewall/облака)

### Шаги

**1. Подключиться к серверу**

```bash
ssh root@<IP_АДРЕС_СЕРВЕРА>
```

**2. Установить Docker**

```bash
apt update && apt upgrade -y
apt install -y curl git

# Установка Docker
curl -fsSL https://get.docker.com | sh

# Проверка
docker --version
docker compose version
```

**3. Клонировать репозиторий**

```bash
git clone <url>
cd pro_sklad
```

**4. Настроить конфигурацию**

```bash
cp .env.example .env
nano .env
```

Изменить пароли на надёжные:

```env
POSTGRES_PASSWORD=ВАШ_НАДЁЖНЫЙ_ПАРОЛЬ
DASHBOARD_PASSWORD=ВАШ_ПАРОЛЬ_ДЛЯ_ПАНЕЛИ
```

**5. Запустить в фоне**

```bash
docker compose up -d --build
```

Флаг `-d` запускает контейнеры в фоне — они продолжат работу после закрытия терминала.

**6. Открыть в браузере**

| Сервис | URL |
|--------|-----|
| Административная панель | `http://<IP_АДРЕС_СЕРВЕРА>:8501` |
| API (Swagger) | `http://<IP_АДРЕС_СЕРВЕРА>:8000/docs` |
| pgAdmin | `http://<IP_АДРЕС_СЕРВЕРА>:5050` |

**7. Автозапуск при перезагрузке сервера**

Контейнеры настроены с `restart: unless-stopped` — после перезагрузки VPS они запустятся автоматически. Убедитесь, что Docker запускается вместе с системой:

```bash
systemctl enable docker
```

---

## ⚙️ Управление

```bash
# Статус контейнеров
docker compose ps

# Логи в реальном времени
docker compose logs -f api
docker compose logs -f dashboard

# Перезапустить после изменений в коде
docker compose restart api
docker compose restart dashboard

# Остановить всё
docker compose down

# Полный сброс базы данных (все данные удалятся)
docker compose down && docker volume rm pro_sklad_postgres_data && docker compose up -d --build
```

---

## 🗄️ Подключение к БД в pgAdmin

После входа в pgAdmin → **Add New Server**:

- **Host:** `db`
- **Port:** `5432`
- **Database:** `tornus_sklad`
- **Username:** `tornus`
- **Password:** значение `POSTGRES_PASSWORD` из `.env`

---

## Функционал

- **Сводка** — остатки, стоимость склада, предупреждения о низком остатке
- **Товары** — добавление, редактирование, удаление позиций
- **Движения** — приход, расход, перемещение, инвентаризация
- **Аналитика** — графики, топ товаров, структура по категориям
- **Импорт** — загрузка товаров из CSV файла
- **Штрих-коды** — генерация PDF (5×6 на листе A4) по всем или выбранным товарам
