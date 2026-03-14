import streamlit as st
import pandas as pd

st.set_page_config(page_title="Товары | Торнус Склад", page_icon="📋", layout="wide")

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
    st.divider()
    if st.button("Выйти", use_container_width=True):
        st.session_state.authenticated = False
        st.rerun()

st.title("📋 Справочник товаров")

tab_list, tab_add, tab_edit = st.tabs(["Список товаров", "Добавить товар", "Редактировать / Удалить"])

# ── Список ────────────────────────────────────────────────────────────────────
with tab_list:
    col_f1, col_f2 = st.columns([2, 1])
    with col_f1:
        try:
            cats = ["Все"] + api.get_categories()
        except Exception:
            cats = ["Все"]
        selected_cat = st.selectbox("Категория", cats)
    with col_f2:
        low_only = st.checkbox("Только низкий остаток")

    try:
        products = api.get_products(
            category=selected_cat if selected_cat != "Все" else None,
            low_stock_only=low_only,
        )
    except Exception as e:
        st.error(f"Ошибка: {e}")
        st.stop()

    if products:
        df = pd.DataFrame(products)
        df["price"] = df["price"].apply(lambda x: float(x))
        df["current_stock"] = df["current_stock"].apply(lambda x: float(x))
        df["min_stock"] = df["min_stock"].apply(lambda x: float(x))
        df = df.rename(columns={
            "id": "ID",
            "name": "Наименование",
            "sku": "Артикул",
            "category": "Категория",
            "unit": "Ед.",
            "price": "Цена, ₽",
            "current_stock": "Остаток",
            "min_stock": "Мин.",
            "description": "Описание",
        })
        st.dataframe(
            df[["ID", "Наименование", "Артикул", "Категория", "Ед.", "Цена, ₽", "Остаток", "Мин.", "Описание"]],
            use_container_width=True,
            hide_index=True,
        )
        st.caption(f"Всего: {len(products)} позиций")
    else:
        st.info("Товаров не найдено.")

# ── Добавить ──────────────────────────────────────────────────────────────────
with tab_add:
    st.subheader("Новый товар")
    with st.form("form_add_product"):
        c1, c2 = st.columns(2)
        name = c1.text_input("Наименование *")
        sku = c2.text_input("Артикул (SKU) *")
        category = c1.text_input("Категория")
        unit = c2.text_input("Единица измерения", value="шт")
        price = c1.number_input("Цена, ₽", min_value=0.0, step=0.01)
        min_stock = c2.number_input("Мин. остаток", min_value=0.0, step=1.0)
        description = st.text_area("Описание")
        submitted = st.form_submit_button("Добавить товар", use_container_width=True)

        if submitted:
            if not name or not sku:
                st.error("Наименование и артикул обязательны")
            else:
                try:
                    api.create_product({
                        "name": name,
                        "sku": sku,
                        "category": category or None,
                        "unit": unit,
                        "price": price,
                        "min_stock": min_stock,
                        "description": description or None,
                    })
                    st.success(f"Товар «{name}» добавлен!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Ошибка: {e}")

# ── Редактировать / Удалить ───────────────────────────────────────────────────
with tab_edit:
    st.subheader("Редактировать или удалить товар")
    try:
        all_products = api.get_products()
    except Exception as e:
        st.error(f"Ошибка: {e}")
        st.stop()

    if not all_products:
        st.info("Нет товаров для редактирования.")
    else:
        options = {f"[{p['id']}] {p['name']} ({p['sku']})": p for p in all_products}
        selected_label = st.selectbox("Выберите товар", list(options.keys()))
        p = options[selected_label]

        with st.form("form_edit_product"):
            ec1, ec2 = st.columns(2)
            new_name = ec1.text_input("Наименование", value=p["name"])
            new_cat = ec2.text_input("Категория", value=p["category"] or "")
            new_unit = ec1.text_input("Единица измерения", value=p["unit"])
            new_price = ec2.number_input("Цена, ₽", value=float(p["price"]), min_value=0.0, step=0.01)
            new_min = ec1.number_input("Мин. остаток", value=float(p["min_stock"]), min_value=0.0)
            new_desc = st.text_area("Описание", value=p["description"] or "")

            col_save, col_del = st.columns(2)
            save = col_save.form_submit_button("💾 Сохранить", use_container_width=True)
            delete = col_del.form_submit_button("🗑️ Удалить товар", use_container_width=True, type="secondary")

            if save:
                try:
                    api.update_product(p["id"], {
                        "name": new_name,
                        "category": new_cat or None,
                        "unit": new_unit,
                        "price": new_price,
                        "min_stock": new_min,
                        "description": new_desc or None,
                    })
                    st.success("Товар обновлён!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Ошибка: {e}")

            if delete:
                try:
                    api.delete_product(p["id"])
                    st.success(f"Товар «{p['name']}» удалён.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Ошибка удаления: {e}")
