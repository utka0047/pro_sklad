import streamlit as st
import pandas as pd
import csv
from io import StringIO, BytesIO

st.set_page_config(page_title="Импорт товаров | Торнус Склад", page_icon="📥", layout="wide")

if not st.session_state.get("authenticated"):
    st.warning("Необходима авторизация")
    st.stop()

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import api_client as api

with st.sidebar:
    st.markdown("## 📦 Торнус Склад")
    st.caption("Система учёта склада")
    st.divider()
    st.page_link("app.py", label="Главная", icon="🏠")
    st.page_link("pages/1_Сводка.py", label="Сводка", icon="📊")
    st.page_link("pages/2_Товары.py", label="Товары", icon="📋")
    st.page_link("pages/3_Движения.py", label="Движения", icon="🔄")
    st.page_link("pages/4_Аналитика.py", label="Аналитика", icon="📈")
    st.page_link("pages/5_Импорт.py", label="Импорт", icon="📥")
    st.divider()
    if st.button("Выйти", use_container_width=True):
        st.session_state.authenticated = False
        st.rerun()

st.title("📥 Импорт товаров")

tab_upload, tab_template = st.tabs(["Загрузить файл", "Скачать шаблон"])

# ── Загрузить ────────────────────────────────────────────────────────────────
with tab_upload:
    st.subheader("Загрузить товары из CSV")

    st.info("""
    **Поддерживаемые форматы:** CSV (текстовый формат с разделителями).

    **Требуемые колонки:**
    - `name` — название товара
    - `sku` — артикул (уникальный идентификатор)

    **Опциональные колонки:**
    - `category` — категория товара
    - `unit` — единица измерения (по умолчанию: шт)
    - `price` — цена в рублях
    - `description` — описание товара
    - `min_stock` — минимальный остаток для заказа
    - `current_stock` — текущий остаток на складе
    """)

    uploaded_file = st.file_uploader("Выберите CSV файл", type="csv")

    if uploaded_file:
        st.subheader("Предпросмотр данных")
        try:
            content = uploaded_file.read()
            text = content.decode('utf-8')
            df = pd.read_csv(StringIO(text))

            st.dataframe(df.head(10), use_container_width=True)
            st.caption(f"Всего строк в файле: {len(df)}")

            col_dup, col_import = st.columns(2)
            with col_dup:
                on_duplicate = st.selectbox(
                    "Что делать с существующими товарами (по SKU)?",
                    ["skip", "update", "error"],
                    format_func=lambda x: {
                        "skip": "Пропустить (не переписывать)",
                        "update": "Обновить данные",
                        "error": "Ошибка (прерватить импорт)",
                    }[x]
                )

            with col_import:
                if st.button("📥 Импортировать", use_container_width=True, type="primary"):
                    with st.spinner("Импортирование товаров..."):
                        try:
                            result = api.import_products_csv(content, uploaded_file.name, on_duplicate)

                            st.success("✅ Импорт завершён!")

                            col1, col2, col3 = st.columns(3)
                            col1.metric("✨ Создано", result.get("created", 0))
                            col2.metric("🔄 Обновлено", result.get("updated", 0))
                            col3.metric("⏭️ Пропущено", result.get("skipped", 0))

                            if result.get("errors"):
                                st.subheader("⚠️ Ошибки при импорте")
                                error_df = pd.DataFrame(result["errors"])
                                st.dataframe(error_df, use_container_width=True, hide_index=True)
                        except Exception as e:
                            st.error(f"❌ Ошибка импорта: {e}")

        except Exception as e:
            st.error(f"Ошибка при чтении файла: {e}")

# ── Шаблон ────────────────────────────────────────────────────────────────────
with tab_template:
    st.subheader("Скачать шаблон CSV")

    st.write("Используйте этот шаблон для подготовки файла импорта.")

    # Создаём пример CSV
    example_data = {
        "name": ["Картофель", "Вода (0.5л)", "Молоко (1л)", "Сахар (1кг)"],
        "sku": ["POTATO-001", "WATER-500", "MILK-1000", "SUGAR-1000"],
        "category": ["Овощи", "Напитки", "Молочные", "Сухофрукты"],
        "unit": ["кг", "шт", "л", "кг"],
        "price": [50.00, 30.00, 85.50, 120.00],
        "description": ["Картофель сорт Беллароза", None, "Молоко коровье 3.6%", "Сахар белый кристаллический"],
        "min_stock": [100, 50, 30, 20],
        "current_stock": [250, 100, 45, 60],
    }

    df_example = pd.DataFrame(example_data)
    st.dataframe(df_example, use_container_width=True, hide_index=True)

    # Конвертируем в CSV
    csv_buffer = StringIO()
    df_example.to_csv(csv_buffer, index=False, encoding='utf-8')
    csv_content = csv_buffer.getvalue()

    st.download_button(
        label="⬇️ Скачать шаблон (template.csv)",
        data=csv_content,
        file_name="tornus_template.csv",
        mime="text/csv",
        use_container_width=True,
    )

    st.divider()
    st.subheader("📋 Правила заполнения")

    rules = """
    1. **name** (обязательно): Название товара, 1-255 символов
    2. **sku** (обязательно): Артикул, уникальный в базе, 1-100 символов
    3. **category** (опционально): Категория товара
    4. **unit** (опционально): Единица измерения (кг, л, шт, упак и т.д.). По умолчанию: `шт`
    5. **price** (опционально): Цена в рублях, число с точкой (не запятой). Например: `150.50`
    6. **description** (опционально): Описание товара
    7. **min_stock** (опционально): Минимальный остаток для заказа. По умолчанию: `0`
    8. **current_stock** (опционально): Текущий остаток на складе. По умолчанию: `0`

    **Важно:**
    - Используйте кодировку **UTF-8** (без BOM)
    - Разделитель полей: запятая (`,`)
    - Числовые значения используйте с точкой как разделитель (напр. `150.50`)
    - Пустые значения или отсутствующие колонки будут заполнены по умолчанию
    """

    st.markdown(rules)
