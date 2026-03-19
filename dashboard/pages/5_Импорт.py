import streamlit as st
import pandas as pd
import csv
from io import StringIO

st.set_page_config(page_title="Импорт товаров | Торнус Склад", page_icon="📥", layout="wide")

if not st.session_state.get("authenticated"):
    st.warning("Необходима авторизация")
    st.stop()

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import api_client as api
from barcode_utils import generate_barcodes_pdf

with st.sidebar:
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

    **Требуемые колонки:** `name`, `sku`

    **Опциональные:** `category`, `unit`, `price`, `description`, `min_stock`, `current_stock`
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

            # ── Штрих-коды из загруженного файла ─────────────────────────────
            st.divider()
            st.subheader("🔖 Штрих-коды из этого файла")

            has_sku = "sku" in df.columns
            has_name = "name" in df.columns

            if not has_sku:
                st.warning("В файле нет колонки `sku` — штрих-коды недоступны.")
            else:
                items_from_csv = []
                for _, row in df.iterrows():
                    sku = str(row.get("sku", "")).strip()
                    name = str(row.get("name", "")).strip() if has_name else sku
                    if sku:
                        items_from_csv.append({"sku": sku, "name": name})

                st.write(f"Найдено товаров с SKU: **{len(items_from_csv)}**")

                if items_from_csv and st.button("🔖 Скачать штрих-коды из CSV", use_container_width=True):
                    with st.spinner("Генерация PDF..."):
                        try:
                            pdf_bytes = generate_barcodes_pdf(items_from_csv)
                            st.download_button(
                                label="⬇️ Скачать PDF со штрих-кодами",
                                data=pdf_bytes,
                                file_name="barcodes_from_csv.pdf",
                                mime="application/pdf",
                                use_container_width=True,
                            )
                        except Exception as e:
                            st.error(f"Ошибка генерации: {e}")

        except Exception as e:
            st.error(f"Ошибка при чтении файла: {e}")

# ── Шаблон ────────────────────────────────────────────────────────────────────
with tab_template:
    st.subheader("Скачать шаблон CSV")
    st.write("Используйте этот шаблон для подготовки файла импорта.")

    example_data = {
        "name": ["Картофель", "Вода (0.5л)", "Молоко (1л)", "Сахар (1кг)"],
        "sku": ["POTATO-001", "WATER-500", "MILK-1000", "SUGAR-1000"],
        "category": ["Овощи", "Напитки", "Молочные", "Бакалея"],
        "unit": ["кг", "шт", "л", "кг"],
        "price": [50.00, 30.00, 85.50, 120.00],
        "description": ["Картофель сорт Беллароза", None, "Молоко коровье 3.6%", "Сахар белый кристаллический"],
        "min_stock": [100, 50, 30, 20],
        "current_stock": [250, 100, 45, 60],
    }

    df_example = pd.DataFrame(example_data)
    st.dataframe(df_example, use_container_width=True, hide_index=True)

    csv_buffer = StringIO()
    df_example.to_csv(csv_buffer, index=False, encoding='utf-8')

    st.download_button(
        label="⬇️ Скачать шаблон (tornus_template.csv)",
        data=csv_buffer.getvalue(),
        file_name="tornus_template.csv",
        mime="text/csv",
        use_container_width=True,
    )

    st.divider()
    st.subheader("📋 Правила заполнения")
    st.markdown("""
1. **name** (обязательно): Название товара, 1–255 символов
2. **sku** (обязательно): Артикул, уникальный в базе, 1–100 символов
3. **category** (опционально): Категория товара
4. **unit** (опционально): Единица измерения (кг, л, шт). По умолчанию: `шт`
5. **price** (опционально): Цена в рублях, число с **точкой**: `150.50`
6. **description** (опционально): Описание товара
7. **min_stock** (опционально): Минимальный остаток для заказа. По умолчанию: `0`
8. **current_stock** (опционально): Текущий остаток на складе. По умолчанию: `0`

**Важно:**
- Кодировка **UTF-8** (без BOM)
- Разделитель: запятая `,`
- Десятичный разделитель: точка `.`
    """)
