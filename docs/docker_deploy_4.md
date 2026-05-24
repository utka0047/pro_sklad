# Контейнеризация и развёртывание «Торнус Склад»

## 1. Цель и мотивация

Система «Торнус Склад» состоит из четырёх сервисов с разными зависимостями: PostgreSQL требует отдельного системного пользователя и файлов данных, FastAPI — Python 3.12 и набора библиотек, Streamlit — другого набора библиотек, pgAdmin — Java-окружения. Устанавливать всё это вручную на одной машине означает неизбежные конфликты версий и сложную воспроизводимость.

**Docker** решает эти проблемы:

| Проблема без Docker | Решение с Docker |
|--------------------|-----------------|
| «У меня работает, у коллеги — нет» | Одинаковая среда в любом месте |
| Конфликты версий Python / PostgreSQL | Каждый сервис в изолированном контейнере |
| Сложный первый запуск (5+ шагов) | `docker-compose up --build` — одна команда |
| Потеря данных при переустановке | Данные в именованном Volume вне контейнера |
| Ручное управление запуском сервисов | `restart: unless-stopped` — автозапуск |

---

## 2. Архитектура контейнеров

```
docker-compose.yml
│
├── db           (postgres:16-alpine)        ← официальный образ, без сборки
├── api          (python:3.12-slim + build)  ← собирается из Dockerfile
├── dashboard    (python:3.12-slim + build)  ← собирается из Dockerfile.dashboard
└── pgadmin      (dpage/pgadmin4:latest)     ← официальный образ, без сборки
```

Сервисы `db` и `pgadmin` используют готовые образы с Docker Hub — их не нужно собирать. Сервисы `api` и `dashboard` требуют сборки: нужно скопировать код проекта и установить зависимости.

---

## 3. Dockerfile для FastAPI (`Dockerfile`)

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY ../requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ../app ./app/

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Разбор каждой строки:**

**`FROM python:3.12-slim`** — базовый образ. Вариант `-slim` содержит минимальный Debian без лишних инструментов (компиляторов, утилит). Это уменьшает размер итогового образа с ~900 МБ (полный Python) до ~150 МБ.

**`WORKDIR /app`** — все последующие команды выполняются в этой директории внутри контейнера. Если директория не существует, Docker создаёт её.

**`COPY requirements.txt .` → `RUN pip install`** — ключевой паттерн оптимизации сборки. Docker кэширует каждый слой образа. Если скопировать `requirements.txt` **отдельно** перед кодом, то при изменении только кода Python слой с установленными библиотеками берётся из кэша и не пересчитывается. Установка зависимостей — самый долгий шаг (30–120 секунд), и благодаря этому паттерну он выполняется только при изменении `requirements.txt`.

**`COPY app/ ./app/`** — копируется только директория с кодом приложения, а не весь корень проекта. Это важно: `node_modules`, `dashboard/`, `.env` и другие файлы не попадают в образ API.

**`--no-cache-dir`** — pip не сохраняет загруженные пакеты в кэш внутри образа, что экономит место.

**`CMD ["uvicorn", ...]`** — команда запуска приложения. `--host 0.0.0.0` критически важен: без него uvicorn слушает только `127.0.0.1` (localhost внутри контейнера) и становится недоступен снаружи.

---

## 4. Dockerfile для Streamlit (`Dockerfile.dashboard`)

```dockerfile
FROM python:3.12-slim

WORKDIR /dashboard

COPY requirements.dashboard.txt .
RUN pip install --no-cache-dir -r requirements.dashboard.txt

COPY dashboard/ .

CMD ["streamlit", "run", "app.py",
     "--server.port=8501",
     "--server.address=0.0.0.0",
     "--server.headless=true"]
```

Структура аналогична Dockerfile для API. Отличия:

**Отдельный `requirements.dashboard.txt`** — зависимости дашборда (Streamlit, Plotly, Pillow, ReportLab и др.) не нужны в образе API. Разделение requirements уменьшает каждый образ и ускоряет сборку.

**`--server.headless=true`** — отключает попытку Streamlit открыть браузер при запуске. В контейнере нет GUI, поэтому без этого флага Streamlit выбрасывает ошибку или зависает.

**`WORKDIR /dashboard` + `COPY dashboard/ .`** — код дашборда копируется в корень рабочей директории. Команда `streamlit run app.py` запускает `app.py` из этой директории, что соответствует структуре Streamlit multipage app (папка `pages/` должна быть рядом с `app.py`).

---

## 5. Docker Compose — оркестрация сервисов

`docker-compose.yml` описывает все четыре сервиса, их связи и конфигурацию.

### Сервис `db` (PostgreSQL)

```yaml
db:
  image: postgres:16-alpine
  container_name: tornus_db
  restart: unless-stopped
  environment:
    POSTGRES_DB: ${POSTGRES_DB:-tornus_sklad}
    POSTGRES_USER: ${POSTGRES_USER:-tornus}
    POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-tornus_pass}
  volumes:
    - postgres_data:/var/lib/postgresql/data
  healthcheck:
    test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-tornus} -d ${POSTGRES_DB:-tornus_sklad}"]
    interval: 5s
    timeout: 5s
    retries: 10
```

**`postgres:16-alpine`** — образ на базе Alpine Linux. Alpine значительно меньше Debian: образ PostgreSQL-alpine весит ~240 МБ против ~450 МБ у дебиановского варианта.

**`restart: unless-stopped`** — политика перезапуска. Контейнер перезапускается автоматически после сбоя или перезагрузки машины. Не перезапускается только если его остановили вручную (`docker stop`). Это обеспечивает автозапуск системы после перезагрузки сервера.

**`${POSTGRES_DB:-tornus_sklad}`** — синтаксис подстановки с дефолтным значением. Если переменная `POSTGRES_DB` не задана в `.env`, используется `tornus_sklad`. Это позволяет системе работать даже без файла `.env`.

**`volumes: postgres_data:/var/lib/postgresql/data`** — именованный Volume. PostgreSQL хранит файлы данных в `/var/lib/postgresql/data` внутри контейнера. Volume монтирует эту директорию в управляемое Docker хранилище вне контейнера. При пересоздании контейнера (`docker-compose down && up`) данные сохраняются. Уничтожаются только явно: `docker volume rm`.

### Healthcheck — ключевое решение

```yaml
healthcheck:
  test: ["CMD-SHELL", "pg_isready -U tornus -d tornus_sklad"]
  interval: 5s
  timeout: 5s
  retries: 10
```

`pg_isready` — утилита PostgreSQL, которая проверяет, готов ли сервер принимать соединения. Возвращает код 0 (успех) только когда PostgreSQL полностью инициализировался.

Без healthcheck Docker считает контейнер `db` готовым сразу после его **запуска**, но PostgreSQL при первом старте тратит 2–5 секунд на создание базы данных, пользователя и структуры файлов. Если FastAPI запустится в этот момент, он получит ошибку подключения.

### Сервис `api` (FastAPI)

```yaml
api:
  build:
    context: .
    dockerfile: Dockerfile
  container_name: tornus_api
  restart: unless-stopped
  env_file: .env
  environment:
    DATABASE_URL: postgresql://${POSTGRES_USER:-tornus}:${POSTGRES_PASSWORD:-tornus_pass}@db:5432/${POSTGRES_DB:-tornus_sklad}
  ports:
    - "8000:8000"
  depends_on:
    db:
      condition: service_healthy
```

**`depends_on: db: condition: service_healthy`** — API запускается только после того, как `db` прошёл healthcheck. Это решает проблему гонки при старте.

**`env_file: .env`** — загружает все переменные из файла `.env` в окружение контейнера.

**`environment: DATABASE_URL: ...`** — переменная `DATABASE_URL` задаётся явно здесь, потому что в ней используется имя хоста `db` (имя сервиса в Docker Compose), а не `localhost`. Если бы `DATABASE_URL` бралась только из `.env`, там было бы `localhost:5432`, что не работает внутри Docker-сети.

**`ports: "8000:8000"`** — проброс порта. `HOST_PORT:CONTAINER_PORT`. Запрос на `localhost:8000` с хост-машины попадает в контейнер на порт 8000.

### Сервис `dashboard` (Streamlit)

```yaml
dashboard:
  build:
    context: .
    dockerfile: Dockerfile.dashboard
  container_name: tornus_dashboard
  restart: unless-stopped
  env_file: .env
  environment:
    API_URL: http://api:8000
    DASHBOARD_PASSWORD: ${DASHBOARD_PASSWORD:-admin123}
  ports:
    - "8501:8501"
  depends_on:
    - api
```

**`API_URL: http://api:8000`** — Streamlit обращается к FastAPI не через `localhost`, а через имя сервиса `api`. Внутри Docker-сети это разрешается в IP-адрес контейнера API. Значение переопределяет возможное `localhost` из `.env`.

**`depends_on: - api`** — без условия `service_healthy`. У FastAPI нет встроенного healthcheck в compose-файле, поэтому используется простая зависимость по запуску. На практике это означает небольшой риск: дашборд может запустится до того, как API полностью готов к работе, но Streamlit корректно обрабатывает ошибки соединения и покажет предупреждение пользователю.

### Сервис `pgadmin`

```yaml
pgadmin:
  image: dpage/pgadmin4:latest
  container_name: tornus_pgadmin
  restart: unless-stopped
  environment:
    PGADMIN_DEFAULT_EMAIL: admin@example.com
    PGADMIN_DEFAULT_PASSWORD: admin
  ports:
    - "5050:80"
  depends_on:
    - db
```

pgAdmin слушает HTTP на порту 80 внутри контейнера, проброшенном на порт 5050 хост-машины. Для подключения к PostgreSQL из pgAdmin используется:
- Hostname: `db` (имя сервиса в Docker Compose)
- Port: `5432`
- Username / Password: значения из `.env`

### Именованный Volume

```yaml
volumes:
  postgres_data:
```

Объявление именованного Volume на уровне compose-файла. Docker управляет его расположением (обычно `/var/lib/docker/volumes/pro_sklad_postgres_data`). Это отличается от bind mount (`./data:/var/lib/postgresql/data`), где путь фиксирован. Именованный Volume проще в управлении и переносимее.

---

## 6. Переменные окружения и `.env`

Файл `.env` содержит всю конфиденциальную конфигурацию:

```env
# PostgreSQL
POSTGRES_DB=tornus_sklad
POSTGRES_USER=tornus
POSTGRES_PASSWORD=tornus_pass

# FastAPI
DATABASE_URL=postgresql://tornus:tornus_pass@db:5432/tornus_sklad

# Streamlit Dashboard
API_URL=http://api:8000
DASHBOARD_PASSWORD=admin123
```

**`.env` исключён из git** через `.gitignore`. В репозитории хранится только `.env.example` с теми же ключами, но без реальных значений. Это стандартная практика: секреты не попадают в историю коммитов.

При развёртывании на новой машине:
```bash
cp .env.example .env
# отредактировать пароли
docker-compose up --build
```

---

## 7. Порядок запуска и зависимости

```
Время →
        0s          2-5s         6-8s         10s
        │            │            │             │
  db ───┼────────────┼──[ready]   │             │
        │            │    │       │             │
  api   │            │    └───────┼────────────►│  (ждёт healthcheck)
        │            │            │             │
  dash  │            │            │        ─────┼──────►
        │            │            │             │
  pgadm │            │            │  ──────────►│
```

`db` → `api` (service_healthy) → `dashboard` (depends_on)

`pgadmin` → `db` (depends_on, параллельно с `api`)

---

## 8. Основные команды

### Первый запуск

```bash
cp .env.example .env        # создать конфигурацию
docker-compose up --build   # собрать образы и запустить все сервисы
```

### Ежедневная работа

```bash
docker-compose up -d          # запустить в фоне (detached)
docker-compose down           # остановить и удалить контейнеры
docker-compose restart api    # перезапустить только API (после правок кода)
docker-compose restart dashboard  # перезапустить дашборд
```

### Просмотр логов

```bash
docker-compose logs -f              # все сервисы в реальном времени
docker-compose logs -f api          # только API
docker-compose logs -f db           # только PostgreSQL
docker-compose logs --tail=50 api   # последние 50 строк
```

### Состояние контейнеров

```bash
docker-compose ps           # список контейнеров и их статус
docker stats                # CPU, RAM, сеть в реальном времени
```

### Перезапуск после изменений кода

```bash
# Только Python-файлы изменились — rebuild не нужен:
docker-compose restart api

# requirements.txt изменился — нужен rebuild:
docker-compose up --build api
```

### Сброс базы данных

```bash
# Полный сброс (все данные удаляются!)
docker-compose down
docker volume rm pro_sklad_postgres_data
docker-compose up --build
```

### Подключение к базе данных напрямую

```bash
docker exec -it tornus_db psql -U tornus -d tornus_sklad

# Полезные команды psql:
\dt              # список таблиц
\d products      # структура таблицы
SELECT COUNT(*) FROM products;
SELECT * FROM stock_movements ORDER BY created_at DESC LIMIT 10;
\q               # выход
```

---

## 9. Проблемы при развёртывании и их решения

### Проблема 1: `role "tornus" does not exist`

**Симптом:**
```
tornus_api | FATAL: role "tornus" does not exist
```

**Причина:** FastAPI запустился до завершения инициализации PostgreSQL — до того, как создан пользователь и база данных.

**Решение:**
```bash
docker-compose down
docker volume rm pro_sklad_postgres_data  # очистить незавершённую инициализацию
docker-compose up --build
```

Healthcheck предотвращает эту проблему при правильном порядке запуска, но при первом создании volume возможна гонка.

### Проблема 2: `Cannot connect to the Docker daemon`

**Симптом:**
```
Cannot connect to the Docker daemon at unix:///var/run/docker.sock
```

**Причина:** Docker Desktop не запущен (на macOS/Windows).

**Решение:**
```bash
open /Applications/Docker.app   # macOS
# дождаться иконки Docker в строке меню
docker-compose up --build
```

### Проблема 3: Порт уже занят

**Симптом:**
```
Error: Bind for 0.0.0.0:8000 failed: port is already allocated
```

**Причина:** Другой процесс занял порт 8000, 8501 или 5432.

**Решение:**
```bash
# Найти процесс на порту:
lsof -i :8000       # macOS/Linux

# Или изменить порт в docker-compose.yml:
ports:
  - "8001:8000"    # хост-порт 8001 вместо 8000
```

### Проблема 4: Старый кэш образа после изменений

**Симптом:** изменения в коде не отражаются после `docker-compose up`.

**Причина:** Docker использует кэшированный слой образа.

**Решение:**
```bash
docker-compose up --build        # пересобрать изменившиеся образы
docker-compose build --no-cache  # пересобрать без кэша полностью
```

### Проблема 5: pgAdmin не видит базу данных

**Причина:** в поле «Host» pgAdmin введён `localhost` вместо `db`.

**Решение:** Внутри Docker-сети сервисы обращаются друг к другу по имени сервиса:
- Host: `db`
- Port: `5432`
- Database: `tornus_sklad`
- Username: `tornus`
- Password: `tornus_pass`

---

## 10. Выбор базового образа: почему `python:3.12-slim`

При разработке рассматривались три варианта:

| Образ | Размер | Особенности |
|-------|--------|------------|
| `python:3.12` | ~900 МБ | Полный Debian, все инструменты |
| `python:3.12-slim` | ~150 МБ | Минимальный Debian ✅ |
| `python:3.12-alpine` | ~50 МБ | Alpine Linux, musl libc |

**Alpine не выбран**, несмотря на минимальный размер. Причина: ряд Python-библиотек (`psycopg2`, `Pillow`, `ReportLab`) требует компиляции нативных расширений. В Alpine используется нестандартная libc (musl вместо glibc), из-за чего колёса (wheels) с PyPI не подходят — приходится компилировать из исходников, что значительно замедляет сборку и требует дополнительных build-зависимостей. В итоге образ на Alpine может оказаться **больше** образа на slim из-за компиляторов.

---

## 11. Итог

| Решение | Обоснование |
|---------|------------|
| Docker Compose вместо ручной установки | Воспроизводимость, изоляция, одна команда запуска |
| `postgres:16-alpine` | Официальный образ, минимальный размер |
| `python:3.12-slim` | Баланс между размером и совместимостью библиотек |
| `COPY requirements.txt` перед `COPY app/` | Кэширование слоя pip install |
| `healthcheck` на `db` | Предотвращение гонки при старте |
| `depends_on: condition: service_healthy` | API стартует только после готовности БД |
| `restart: unless-stopped` | Автозапуск после перезагрузки сервера |
| Именованный Volume `postgres_data` | Сохранение данных при пересоздании контейнеров |
| `.env` в `.gitignore` | Секреты не попадают в репозиторий |
| Имена сервисов вместо `localhost` | Корректная маршрутизация внутри Docker-сети |
