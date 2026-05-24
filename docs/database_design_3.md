# Проектирование базы данных «Торнус Склад»

## 1. Цель и требования

База данных — это фундамент всей системы. От её структуры зависит корректность учёта, скорость аналитических запросов и возможность расширения функционала в будущем.

Требования, которые определяли принятые решения:

- точный учёт остатков без потерь из-за ошибок округления;
- полная история всех изменений остатков (аудит);
- быстрый поиск товара по артикулу (SKU);
- возможность агрегированных запросов по дате, типу движения, категории;
- целостность данных: нельзя удалить товар, у которого есть история движений.

---

## 2. Выбор СУБД

### PostgreSQL 16

Для проекта выбран **PostgreSQL** — реляционная СУБД с открытым исходным кодом.

**Обоснование выбора:**

| Критерий | PostgreSQL | SQLite | MySQL |
|---------|-----------|--------|-------|
| Точность чисел (`NUMERIC`) | ✅ Точный | ✅ Точный | ⚠️ Зависит от версии |
| Сложные аналитические запросы | ✅ Полная поддержка | ⚠️ Ограниченно | ✅ Да |
| Конкурентные записи | ✅ MVCC | ❌ Блокирует файл | ✅ Да |
| Внешние ключи с `ON DELETE` | ✅ Полная поддержка | ⚠️ Нужно включать | ✅ Да |
| Разворачивание в Docker | ✅ Официальный образ | — | ✅ Да |

SQLite не подходит, так как при одновременной работе нескольких пользователей блокирует весь файл базы данных. PostgreSQL использует MVCC (Multi-Version Concurrency Control) — читатели не блокируют писателей.

---

## 3. Схема базы данных

В системе две таблицы, связанные отношением **один-ко-многим**:

```
┌──────────────────────────┐        ┌───────────────────────────────┐
│         products          │        │        stock_movements         │
├──────────────────────────┤        ├───────────────────────────────┤
│ id            INTEGER PK │◄──┐    │ id              INTEGER PK    │
│ name          VARCHAR(255)│   └────│ product_id      INTEGER FK    │
│ sku           VARCHAR(100)│        │ movement_type   VARCHAR(20)   │
│ category      VARCHAR(100)│        │ quantity        NUMERIC(10,3) │
│ unit          VARCHAR(50) │        │ quantity_before NUMERIC(10,3) │
│ price         NUMERIC(10,2)│       │ quantity_after  NUMERIC(10,3) │
│ description   TEXT        │        │ comment         TEXT          │
│ min_stock     NUMERIC(10,3)│       │ created_at      TIMESTAMP     │
│ current_stock NUMERIC(10,3)│       └───────────────────────────────┘
│ created_at    TIMESTAMP   │
│ updated_at    TIMESTAMP   │
└──────────────────────────┘
```

Один товар (`products`) может иметь множество записей о движениях (`stock_movements`).

---

## 4. Таблица `products` — справочник товаров

### Структура и обоснование полей

```sql
CREATE TABLE products (
    id            SERIAL PRIMARY KEY,
    name          VARCHAR(255)    NOT NULL,
    sku           VARCHAR(100)    NOT NULL UNIQUE,
    category      VARCHAR(100),
    unit          VARCHAR(50)     DEFAULT 'шт',
    price         NUMERIC(10, 2)  DEFAULT 0,
    description   TEXT,
    min_stock     NUMERIC(10, 3)  DEFAULT 0,
    current_stock NUMERIC(10, 3)  DEFAULT 0,
    created_at    TIMESTAMP       DEFAULT NOW(),
    updated_at    TIMESTAMP       DEFAULT NOW()
);

CREATE INDEX ix_products_sku ON products(sku);
```

**Ключевые решения:**

**`sku` — уникальный артикул с индексом.** SKU (Stock Keeping Unit) — стандартный способ идентификации товара в торговле. Поле объявлено `UNIQUE` на уровне базы данных, а не только в приложении. Индекс ускоряет поиск при импорте: перед созданием каждого товара система ищет его по SKU, чтобы обработать дубликаты.

**`NUMERIC(10, 2)` для цены и `NUMERIC(10, 3)` для остатков.** Тип `NUMERIC` (он же `DECIMAL`) хранит числа с фиксированной точностью без ошибок двоичного представления, характерных для `FLOAT`. Для цены достаточно двух знаков после запятой (рубли и копейки), для остатков — три (например, 0.125 кг или 1.500 л). Использование `FLOAT` привело бы к накопительным ошибкам округления при многократных операциях с остатками.

**`min_stock` — минимальный остаток.** Поле используется для автоматического выявления позиций, требующих пополнения. Логика проверки: `current_stock < min_stock`. Если `min_stock = 0`, предупреждение не генерируется — это удобно для товаров, не требующих контроля минимума.

**`current_stock` — денормализованный остаток.** Строго говоря, текущий остаток можно вычислить из таблицы движений: `SUM(quantity) WHERE movement_type = 'IN' - SUM(quantity) WHERE movement_type = 'OUT'`. Однако это дорогой запрос при большой истории. Для мгновенного чтения остаток дублируется прямо в строке товара и синхронизируется приложением при каждом движении в рамках одной транзакции.

**`updated_at`** обновляется через параметр SQLAlchemy `onupdate=datetime.utcnow` — автоматически при любом изменении строки.

---

## 5. Таблица `stock_movements` — журнал движений

### Структура и обоснование полей

```sql
CREATE TABLE stock_movements (
    id              SERIAL PRIMARY KEY,
    product_id      INTEGER         NOT NULL REFERENCES products(id) ON DELETE RESTRICT,
    movement_type   VARCHAR(20)     NOT NULL,
    quantity        NUMERIC(10, 3)  NOT NULL,
    quantity_before NUMERIC(10, 3)  NOT NULL,
    quantity_after  NUMERIC(10, 3)  NOT NULL,
    comment         TEXT,
    created_at      TIMESTAMP       DEFAULT NOW(),

    CONSTRAINT ck_movement_type CHECK (
        movement_type IN ('IN', 'OUT', 'TRANSFER', 'INVENTORY')
    ),
    CONSTRAINT ck_quantity_positive CHECK (quantity > 0)
);

CREATE INDEX ix_stock_movements_product_id ON stock_movements(product_id);
CREATE INDEX ix_stock_movements_movement_type ON stock_movements(movement_type);
CREATE INDEX ix_stock_movements_created_at ON stock_movements(created_at);
```

**Ключевые решения:**

**`quantity_before` и `quantity_after` — снимки остатка.** Хранить только количество движения недостаточно. Если в истории записано «OUT 5 шт», невозможно понять, был ли это перед этим нулевой остаток или тысячный. Поля `quantity_before` и `quantity_after` фиксируют состояние на момент операции. Это полноценный **аудит**: можно восстановить остаток товара на любую дату, просто взяв `quantity_after` последнего движения до этой даты.

**`ON DELETE RESTRICT` на внешнем ключе.** PostgreSQL не позволит удалить товар из `products`, если у него есть хоть одна запись в `stock_movements`. Это защита от случайного уничтожения истории. В SQLAlchemy эта опция прописана явно: `ForeignKey("products.id", ondelete="RESTRICT")`.

**`CHECK` ограничения на уровне БД:**
- `movement_type IN ('IN', 'OUT', 'TRANSFER', 'INVENTORY')` — гарантирует, что в базу нельзя записать произвольную строку, даже если обойти API.
- `quantity > 0` — количество движения всегда положительное. Направление определяется `movement_type`, а не знаком числа.

**Три индекса на `stock_movements`:**
- `product_id` — для быстрой фильтрации истории конкретного товара;
- `movement_type` — для аналитики типа «суммарный приход»;
- `created_at` — для выборок по временным диапазонам (график за 30 дней).

---

## 6. Нормализация

Схема соответствует **Третьей нормальной форме (3NF)**:

- **1NF:** все атрибуты атомарны, нет повторяющихся групп.
- **2NF:** нет частичных зависимостей от составного ключа (ключи простые).
- **3NF:** нет транзитивных зависимостей — каждый неключевой атрибут зависит только от первичного ключа.

**Сознательное нарушение нормализации — `current_stock`:** поле является производным от `stock_movements`, то есть формально это денормализация. Решение принято намеренно для производительности — цена консистентности оплачена транзакционной логикой в `crud.create_movement()`.

---

## 7. Транзакционность

Критически важная операция — создание движения — выполняется как единая транзакция:

```python
# В crud.create_movement():
movement = StockMovement(
    product_id=data.product_id,
    quantity=qty,
    quantity_before=qty_before,
    quantity_after=qty_after,
    ...
)
db.add(movement)

product.current_stock = qty_after   # обновляем денормализованное поле
product.updated_at = datetime.utcnow()

db.commit()  # ← один коммит — оба изменения сохраняются вместе
```

Если `db.commit()` не произойдёт (исключение, обрыв соединения), ни запись о движении, ни изменение остатка не сохранятся. Невозможна ситуация, когда движение записалось, но остаток не обновился, или наоборот.

---

## 8. Инициализация без миграций

Таблицы создаются автоматически при первом запуске FastAPI через:

```python
# app/main.py — lifespan
Base.metadata.create_all(bind=engine)
```

SQLAlchemy сравнивает существующую схему с определениями моделей и создаёт отсутствующие таблицы. **Уже существующие таблицы не изменяются** — это не миграционная система. При изменении структуры (добавление колонки) необходимо вручную удалить тома Docker или использовать Alembic.

---

## 9. Соединение с базой данных

```python
# app/database.py
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
```

**`pool_pre_ping=True`** — перед отдачей соединения из пула SQLAlchemy отправляет `SELECT 1`. Если соединение «умерло» (PostgreSQL перезапустился), пул создаст новое. Без этого параметра приложение падало бы с ошибкой после перезапуска контейнера БД.

**`autocommit=False, autoflush=False`** — явное управление транзакциями. `db.commit()` вызывается вручную только после успешного завершения операции. Это стандартный безопасный режим для бизнес-логики.

Сессия передаётся в каждый эндпоинт через dependency injection FastAPI:

```python
def get_db():
    db = SessionLocal()
    try:
        yield db      # сессия живёт время запроса
    finally:
        db.close()    # закрывается всегда, даже при исключении
```

---

## 10. Итог

| Решение | Обоснование |
|---------|------------|
| PostgreSQL вместо SQLite | Конкурентный доступ, сложная аналитика |
| `NUMERIC` вместо `FLOAT` | Точный учёт без ошибок округления |
| `quantity_before` / `quantity_after` | Полный аудит изменений остатков |
| `ON DELETE RESTRICT` | Защита от удаления товаров с историей |
| `CHECK` ограничения | Целостность данных на уровне БД, независимо от приложения |
| Индексы на `sku`, `product_id`, `created_at` | Быстрая фильтрация и аналитика |
| Денормализованный `current_stock` | Мгновенное чтение остатка без агрегации |
| Транзакция в `create_movement()` | Атомарность: остаток и запись неразделимы |
