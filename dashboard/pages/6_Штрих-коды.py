import streamlit as st
import pandas as pd

st.set_page_config(page_title="Штрих-коды | Торнус Склад", page_icon="🔖", layout="wide")

if not st.session_state.get("authenticated"):
    st.warning("Необходима авторизация")
    st.stop()

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import api_client as api
from barcode_utils import generate_barcodes_pdf

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
    st.page_link("pages/6_Штрих-коды.py", label="Штрих-коды", icon="🔖")
    st.divider()
    if st.button("Выйти", use_container_width=True):
        st.session_state.authenticated = False
        st.rerun()

st.title("🔖 Генерация штрих-кодов")
st.caption("PDF-документ: 5 колонок × 6 строк = 30 штрих-кодов на листе A4")

# Загружаем все товары из API
try:
    all_products = api.get_products()
except Exception as e:
    st.error(f"Не удалось загрузить товары: {e}")
    st.stop()

if not all_products:
    st.info("В базе нет товаров. Сначала добавьте товары через страницу «Товары» или «Импорт».")
    st.stop()

tab_all, tab_select = st.tabs(["Все товары", "Выбрать товары"])

# ── Все товары ────────────────────────────────────────────────────────────────
with tab_all:
    st.subheader("Скачать штрих-коды для всех товаров")

    df_all = pd.DataFrame(all_products)[["name", "sku", "category", "unit", "current_stock"]]
    df_all.columns = ["Наименование", "Артикул", "Категория", "Ед.", "Остаток"]
    st.dataframe(df_all, use_container_width=True, hide_index=True)
    st.caption(f"Всего товаров: {len(all_products)}")

    st.divider()

    # Фильтр по категории
    categories = sorted({p.get("category") or "Без категории" for p in all_products})
    col_cat, col_btn = st.columns([2, 1])

    with col_cat:
        selected_cat = st.selectbox(
            "Фильтр по категории (опционально)",
            ["Все категории"] + categories,
            key="all_tab_cat",
        )

    filtered = all_products
    if selected_cat != "Все категории":
        filtered = [
            p for p in all_products
            if (p.get("category") or "Без категории") == selected_cat
        ]

    items = [{"sku": p["sku"], "name": p["name"]} for p in filtered]

    with col_btn:
        st.write("")  # выравнивание кнопки
        st.write("")
        gen_all = st.button(
            f"🔖 Сгенерировать PDF ({len(items)} шт.)",
            use_container_width=True,
            type="primary",
            key="gen_all",
        )

    if gen_all:
        if not items:
            st.warning("Нет товаров для генерации.")
        else:
            with st.spinner(f"Генерация PDF для {len(items)} штрих-кодов..."):
                try:
                    pdf_bytes = generate_barcodes_pdf(items)
                    fname = "barcodes_all.pdf" if selected_cat == "Все категории" \
                        else f"barcodes_{selected_cat}.pdf"
                    st.success(f"✅ PDF готов — {len(items)} штрих-кодов, {-(-len(items)//30)} стр.")
                    st.download_button(
                        label="⬇️ Скачать PDF",
                        data=pdf_bytes,
                        file_name=fname,
                        mime="application/pdf",
                        use_container_width=True,
                        key="dl_all",
                    )
                except Exception as e:
                    st.error(f"Ошибка генерации: {e}")

# ── Выбрать товары ────────────────────────────────────────────────────────────
with tab_select:
    st.subheader("Выбрать товары для штрих-кодов")

    # Фильтры
    col_f1, col_f2, col_f3 = st.columns(3)

    categories_sel = sorted({p.get("category") or "Без категории" for p in all_products})
    with col_f1:
        filter_cat = st.selectbox(
            "Категория",
            ["Все"] + categories_sel,
            key="sel_tab_cat",
        )
    with col_f2:
        search_name = st.text_input("Поиск по названию", placeholder="Введите часть названия...")
    with col_f3:
        search_sku = st.text_input("Поиск по артикулу", placeholder="SKU...")

    # Применяем фильтры
    visible = all_products
    if filter_cat != "Все":
        visible = [p for p in visible if (p.get("category") or "Без категории") == filter_cat]
    if search_name:
        visible = [p for p in visible if search_name.lower() in p["name"].lower()]
    if search_sku:
        visible = [p for p in visible if search_sku.lower() in p["sku"].lower()]

    if not visible:
        st.info("Нет товаров по заданным фильтрам.")
    else:
        # Таблица с чекбоксами через st.data_editor
        df_sel = pd.DataFrame([
            {
                "Выбрать": False,
                "Артикул": p["sku"],
                "Наименование": p["name"],
                "Категория": p.get("category") or "—",
                "Ед.": p.get("unit", "шт"),
                "Остаток": float(p.get("current_stock", 0)),
            }
            for p in visible
        ])

        edited = st.data_editor(
            df_sel,
            column_config={
                "Выбрать": st.column_config.CheckboxColumn("✅ Выбрать", default=False),
                "Остаток": st.column_config.NumberColumn("Остаток", format="%.1f"),
            },
            use_container_width=True,
            hide_index=True,
            key="barcode_selector",
        )

        selected_rows = edited[edited["Выбрать"] == True]
        n_selected = len(selected_rows)

        col_info, col_gen = st.columns([2, 1])
        with col_info:
            if n_selected:
                st.info(f"Выбрано товаров: **{n_selected}** → PDF займёт **{-(-n_selected//30)} стр.**")
            else:
                st.caption("Отметьте товары галочкой в таблице выше")

        with col_gen:
            gen_sel = st.button(
                f"🔖 Сгенерировать PDF",
                disabled=(n_selected == 0),
                use_container_width=True,
                type="primary",
                key="gen_sel",
            )

        if gen_sel and n_selected > 0:
            items_sel = [
                {"sku": row["Артикул"], "name": row["Наименование"]}
                for _, row in selected_rows.iterrows()
            ]
            with st.spinner(f"Генерация PDF для {n_selected} штрих-кодов..."):
                try:
                    pdf_bytes = generate_barcodes_pdf(items_sel)
                    st.success(f"✅ PDF готов — {n_selected} штрих-кодов, {-(-n_selected//30)} стр.")
                    st.download_button(
                        label="⬇️ Скачать PDF",
                        data=pdf_bytes,
                        file_name="barcodes_selected.pdf",
                        mime="application/pdf",
                        use_container_width=True,
                        key="dl_sel",
                    )
                except Exception as e:
                    st.error(f"Ошибка генерации: {e}")
