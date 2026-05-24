# Разработка бэкенда и REST API «Торнус Склад»

## 1. Цель и контекст

Бэкенд — это ядро системы: он хранит все данные, реализует бизнес-логику и предоставляет API для административной панели. В будущем этот же API будет использоваться мобильным приложением для складских работников.

Основные требования к бэкенду:
- надёжное хранение данных о товарах и движениях в реляционной СУБД;
- REST API с автодокументацией для простоты интеграции;
- корректный пересчёт остатков при каждом движении товара;
- возможность аналитических запросов (агрегация, группировка по дате);
- массовый импорт товаров из внешних файлов.

Для реализации выбран стек **FastAPI + SQLAlchemy + PostgreSQL**.

---

## 2. Выбор технологий и обоснование

### FastAPI
FastAPI — современный Python-фреймворк для построения REST API. Ключевые преимущества для данного проекта:

- **Автоматическая документация** — на основе аннотаций типов Pydantic автоматически генерируется Swagger UI (`/docs`) и ReDoc (`/redoc`). Это критически важно для учебного проекта и для будущей мобильной команды.
- **Валидация входных данных** — все входящие JSON-запросы автоматически проверяются по схемам Pydantic. Некорректные данные возвращают структурированную ошибку без лишнего кода.
- **Asynchronous-ready** — поддерживает `async def` эндпоинты, что важно для эндпоинта загрузки файлов.

### SQLAlchemy (синхронный режим)
Использован синхронный режим SQLAlchemy с `psycopg2` как драйвером PostgreSQL. Синхронный режим выбран сознательно: он проще в отладке и достаточен для нагрузки малого бизнеса. Все запросы выполняются через ORM-сессии с паттерном `get_db` (dependency injection).

### PostgreSQL 16
Выбран как надёжная, проверенная СУБД с поддержкой сложных аналитических запросов (GROUP BY, функции агрегации, работа с датами). Разворачивается в Docker-контейнере `postgres:16-alpine`.

---

## 3. Структура проекта

```
app/
  main.py         — инициализация FastAPI, lifespan, подключение роутеров
  database.py     — создание engine, SessionLocal, Base, функция get_db
  models.py       — ORM-модели: Product, StockMovement
  schemas.py      — Pydantic-схемы: входные и выходные модели
  crud.py         — все операции с базой данных
  routers/
    products.py   — /products/* эндпоинты
    movements.py  — /movements/* эндпоинты
    analytics.py  — /analytics/* эндпоинты
```

Такое разделение — классическая многослойная архитектура:
- **Роутеры** — только HTTP-логика: принять запрос, вызвать CRUD, вернуть ответ.
- **CRUD** — только работа с базой данных, без знания о HTTP.
- **Схемы** — только определение форматов данных.
- **Модели** — только структура таблиц.

Это упрощает тестирование: CRUD-функции можно проверять без запуска HTTP-сервера.

---

## 4. Модели данных

### Таблица `products`

```python
class Product(Base):
    __tablename__ = "products"

    id            = Column(Integer, primary_key=True)
    name          = Column(String(255), nullable=False)
    sku           = Column(String(100), unique=True, nullable=False, index=True)
    category      = Column(String(100))
    unit          = Column(String(50), default="шт")
    price         = Column(Numeric(12, 2), default=0)
    description   = Column(Text)
    min_stock     = Column(Numeric(12, 3), default=0)
    current_stock = Column(Numeric(12, 3), default=0)
    created_at    = Column(DateTime, default=datetime.utcnow)
    updated_at    = Column(DateTime, default=datetime.utcnow)
```

Поле `sku` имеет уникальный индекс — это ключ для идентификации товара при импорте и при поиске. Остатки хранятся как `Numeric(12, 3)` для точного учёта дробных единиц (например, 0.5 кг).

### Таблица `stock_movements`

```python
class StockMovement(Base):
    __tablename__ = "stock_movements"

    id              = Column(Integer, primary_key=True)
    product_id      = Column(Integer, ForeignKey("products.id"), nullable=False)
    movement_type   = Column(String(20), nullable=False)  # IN/OUT/TRANSFER/INVENTORY
    quantity        = Column(Numeric(12, 3), nullable=False)
    quantity_before = Column(Numeric(12, 3), nullable=False)
    quantity_after  = Column(Numeric(12, 3), nullable=False)
    comment         = Column(Text)
    created_at      = Column(DateTime, default=datetime.utcnow)
```

Хранятся значения остатка **до и после** каждого движения. Это обеспечивает полный аудит: можно восстановить историю изменений любого товара на любую дату.

---

## 5. Бизнес-логика движений

Самая критичная функция системы — `create_movement()` в `crud.py`. Она реализует четыре типа движений с разной логикой пересчёта остатка:

```python
def create_movement(db, data):
    product = get_product(db, data.product_id)
    qty = Decimal(str(data.quantity))
    qty_before = Decimal(str(product.current_stock))

    if data.movement_type == "IN":
        qty_after = qty_before + qty

    elif data.movement_type == "OUT":
        if qty_before < qty:
            return None, f"Недостаточно товара. Остаток: {qty_before}"
        qty_after = qty_before - qty

    elif data.movement_type == "TRANSFER":
        qty_after = qty_before      # остаток не меняется, только запись факта

    elif data.movement_type == "INVENTORY":
        qty_after = qty             # quantity = фактическое количество при пересчёте

    # Обновляем остаток товара атомарно с созданием записи движения
    movement = StockMovement(...)
    db.add(movement)
    product.current_stock = qty_after
    product.updated_at = datetime.utcnow()
    db.commit()
```

Важно: и запись движения, и обновление остатка происходят в **одной транзакции** (`db.commit()` вызывается один раз). Это гарантирует консистентность: не может быть ситуации, когда движение записалось, но остаток не обновился.

---

## 6. Аналитические запросы

Эндпоинты в `analytics.py` реализуют сложные SQL-запросы через SQLAlchemy ORM.

### График движений по дням

```python
rows = db.query(
    cast(StockMovement.created_at, Date).label("day"),
    StockMovement.movement_type,
    func.sum(StockMovement.quantity).label("total_qty"),
).filter(
    StockMovement.created_at >= date_from,
    StockMovement.movement_type.in_(["IN", "OUT"]),
).group_by(
    cast(StockMovement.created_at, Date),
    StockMovement.movement_type,
).order_by("day").all()
```

Запрос возвращает агрегированные данные по дням — это гораздо эффективнее, чем передавать все записи на сторону клиента и считать там.

### Топ товаров по оборачиваемости

Использован `func.case()` для условной агрегации — подсчёт суммы приходов и расходов в одном запросе:

```python
func.sum(
    func.case((StockMovement.movement_type == "OUT", StockMovement.quantity), else_=0)
).label("total_out")
```

---

## 7. Импорт товаров из CSV

### Задача
Пользователь загружает CSV-файл с произвольным числом товаров. API должен создать новые записи, обработать дубликаты и вернуть детальный отчёт об ошибках.

### Эндпоинт

```python
@router.post("/import/csv", status_code=200)
async def import_csv(
    file: UploadFile = File(...),
    on_duplicate: str = Query("skip", regex="^(skip|update|error)$"),
    db: Session = Depends(get_db),
):
```

Параметр `on_duplicate` управляет поведением при дублировании SKU:
- `skip` — пропустить, оставить существующий товар;
- `update` — обновить поля существующего товара;
- `error` — добавить в список ошибок.

### CRUD-функция `bulk_import_products()`

Обрабатывает список словарей и возвращает статистику:
```python
{
    "created": 35,
    "updated": 3,
    "skipped": 2,
    "errors": [
        {"row": 7, "sku": "BAD-SKU", "error": "SKU не может быть пусто"}
    ]
}
```

При ошибке в конкретной строке вызывается `db.rollback()` только для этой строки — остальные товары успешно импортируются. Импорт не прерывается при первой ошибке.

---

## 8. Схемы Pydantic (валидация)

Pydantic v2 используется для:
- **валидации входящих данных** — автоматическая проверка типов, длин строк, диапазонов чисел;
- **сериализации ответов** — преобразование ORM-объектов в JSON.

Пример схемы создания товара:
```python
class ProductCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    sku: str = Field(..., min_length=1, max_length=100)
    unit: str = Field(default="шт", max_length=50)
    price: Decimal = Field(default=Decimal("0"), ge=0)
    min_stock: Decimal = Field(default=Decimal("0"), ge=0)
    category: Optional[str] = None
    description: Optional[str] = None
```

Если клиент отправит `price: -100` или `name: ""` — FastAPI автоматически вернёт `422 Unprocessable Entity` с описанием всех нарушений.

---

## 9. Docker-инфраструктура

Вся система запускается через `docker-compose` одной командой:

```yaml
services:
  db:        # PostgreSQL 16
  api:       # FastAPI (Dockerfile)
  dashboard: # Streamlit (Dockerfile.dashboard)
  pgadmin:   # pgAdmin 4 для управления БД
```

Зависимости между сервисами:
- `api` ждёт готовности `db` через `healthcheck` (`pg_isready`);
- `dashboard` ждёт готовности `api`.

Это решает проблему гонки при старте: FastAPI не пытается подключиться к PostgreSQL пока тот ещё инициализируется.

Инициализация таблиц происходит при старте приложения через lifespan:
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)  # создать таблицы если нет
    yield
```

---

## 10. Проблемы и их решения

### Проблема 1: Порядок роутов — конфликт `/categories` и `/{product_id}`

**Ситуация:** При запросе `GET /products/categories` FastAPI возвращал ошибку 404 или пытался найти товар с `product_id = "categories"`.

**Причина:** Роут `@router.get("/{product_id}")` перехватывал запрос раньше, чем `@router.get("/categories")`, потому что был зарегистрирован первым.

**Решение:** Специфичные маршруты (с конкретными строками) регистрируются **до** параметрических:
```python
@router.get("/categories")      # сначала конкретный
@router.get("/{product_id}")    # потом параметрический
```

### Проблема 2: Типы данных — `Decimal` vs `float`

**Ситуация:** При вычислении остатков возникали ошибки округления. Например, `0.1 + 0.2 = 0.30000000000000004`.

**Причина:** Нативные Python `float` используют двоичную арифметику с плавающей точкой, что неприемлемо для финансовых расчётов.

**Решение:** Все количества и цены хранятся как `Decimal`. При создании значений из строк используется `Decimal(str(value))`, а не `Decimal(float_value)` — иначе ошибки точности сохраняются:
```python
qty = Decimal(str(data.quantity))  # правильно
qty = Decimal(data.quantity)       # неправильно — ошибки float сохраняются
```

### Проблема 3: База данных не инициализировалась при первом запуске

**Ситуация:** При первом `docker-compose up` FastAPI запускался раньше, чем PostgreSQL успевал создать пользователя и базу данных. Приложение падало с `role "tornus" does not exist`.

**Причина:** Docker запускает контейнеры параллельно. Даже при `depends_on` контейнер `api` стартует сразу после **создания** контейнера `db`, не дожидаясь готовности PostgreSQL.

**Решение:** Добавлен `healthcheck` для сервиса `db`:
```yaml
healthcheck:
  test: ["CMD-SHELL", "pg_isready -U tornus -d tornus_sklad"]
  interval: 5s
  retries: 10
```
И условие для `api`:
```yaml
depends_on:
  db:
    condition: service_healthy
```
Теперь FastAPI стартует только после того, как PostgreSQL прошёл проверку готовности.

### Проблема 4: Гонка при импорте — частичный откат

**Ситуация:** При импорте 40 товаров, если один из них вызывал ошибку, `db.rollback()` откатывал **весь** импорт, включая успешно обработанные строки.

**Причина:** SQLAlchemy-сессия — единая транзакция. Первый `rollback()` отменял все предыдущие `commit()`-ы.

**Решение:** Каждый товар обрабатывается в отдельном блоке `try/except`. При ошибке одной строки откатывается только она. Остальные уже зафиксированы через `db.commit()` внутри цикла:

```python
for idx, data in enumerate(products_data, 1):
    try:
        db.add(product)
        db.commit()          # фиксируем каждый товар отдельно
        result['created'] += 1
    except Exception as e:
        db.rollback()        # откатываем только текущую строку
        result['errors'].append(...)
```

---

## 11. API — обзор эндпоинтов

| Метод | URL | Описание |
|-------|-----|---------|
| GET | `/products/` | Список товаров (фильтры: category, low_stock_only) |
| GET | `/products/categories` | Список уникальных категорий |
| GET | `/products/{id}` | Получить товар по ID |
| POST | `/products/` | Создать товар |
| PUT | `/products/{id}` | Обновить товар |
| DELETE | `/products/{id}` | Удалить товар |
| POST | `/products/import/csv` | Массовый импорт из CSV |
| GET | `/movements/` | Список движений (фильтры) |
| POST | `/movements/` | Создать движение |
| GET | `/analytics/summary` | Сводные показатели склада |
| GET | `/analytics/low-stock` | Товары с низким остатком |
| GET | `/analytics/movements-chart` | Данные для графика движений |
| GET | `/analytics/top-products` | Топ товаров по обороту |

Полная интерактивная документация доступна по адресу `http://localhost:8000/docs`.

---

## 12. Итог

Бэкенд реализует всю бизнес-логику системы учёта склада и предоставляет хорошо структурированный REST API. Архитектурные решения (разделение на слои, транзакционность, типы Decimal, healthcheck) обеспечивают надёжность и корректность данных. FastAPI с Pydantic-схемами даёт автодокументацию «из коробки» — это важно как для текущей административной панели, так и для будущего мобильного приложения.
