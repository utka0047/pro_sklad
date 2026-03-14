from datetime import date, timedelta
import streamlit as st
import pandas as pd

st.set_page_config(page_title="Движения | Торнус Склад", page_icon="🔄", layout="wide")

if not st.session_state.get("authenticated"):
    st.warning("Необходима авторизация")
    st.stop()

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import api_client as api

MOVEMENT_LABELS = {
    "IN": "📥 Приход",
    "OUT": "📤 Расход",
    "TRANSFER": "🔁 Перемещение",
    "INVENTORY": "📝 Инвентаризация",
}

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

st.title("🔄 Журнал движений")

tab_log, tab_new = st.tabs(["Журнал", "Новое движение"])

# ── Журнал ────────────────────────────────────────────────────────────────────
with tab_log:
    fc1, fc2, fc3, fc4 = st.columns(4)
    with fc1:
        f_type = st.selectbox("Тип", ["Все", "IN", "OUT", "TRANSFER", "INVENTORY"],
                              format_func=lambda x: MOVEMENT_LABELS.get(x, x))
    with fc2:
        try:
            products_list = api.get_products()
            prod_opts = {"Все товары": None}
            prod_opts.update({f"[{p['id']}] {p['name']}": p["id"] for p in products_list})
        except Exception:
            prod_opts = {"Все товары": None}
        f_product = st.selectbox("Товар", list(prod_opts.keys()))
    with fc3:
        f_date_from = st.date_input("С даты", value=date.today() - timedelta(days=30))
    with fc4:
        f_date_to = st.date_input("По дату", value=date.today())

    try:
        movements = api.get_movements(
            product_id=prod_opts[f_product],
            movement_type=f_type if f_type != "Все" else None,
            date_from=f_date_from,
            date_to=f_date_to,
        )
    except Exception as e:
        st.error(f"Ошибка: {e}")
        st.stop()

    if movements:
        df = pd.DataFrame(movements)
        df["movement_type"] = df["movement_type"].map(MOVEMENT_LABELS)
        df["created_at"] = pd.to_datetime(df["created_at"]).dt.strftime("%d.%m.%Y %H:%M")
        df = df.rename(columns={
            "id": "ID",
            "product_name": "Товар",
            "product_sku": "Артикул",
            "movement_type": "Тип",
            "quantity": "Кол-во",
            "quantity_before": "До",
            "quantity_after": "После",
            "comment": "Комментарий",
            "created_at": "Дата",
        })
        st.dataframe(
            df[["ID", "Дата", "Тип", "Товар", "Артикул", "Кол-во", "До", "После", "Комментарий"]],
            use_container_width=True,
            hide_index=True,
        )
        st.caption(f"Записей: {len(movements)}")
    else:
        st.info("Движений за выбранный период не найдено.")

# ── Новое движение ────────────────────────────────────────────────────────────
with tab_new:
    st.subheader("Зарегистрировать движение")

    try:
        all_products = api.get_products()
    except Exception as e:
        st.error(f"Ошибка загрузки товаров: {e}")
        st.stop()

    if not all_products:
        st.warning("Сначала добавьте товары в справочник.")
    else:
        with st.form("form_new_movement"):
            nc1, nc2 = st.columns(2)
            prod_map = {f"[{p['id']}] {p['name']} ({p['sku']})": p for p in all_products}
            sel_prod_label = nc1.selectbox("Товар *", list(prod_map.keys()))
            sel_product = prod_map[sel_prod_label]

            m_type = nc2.selectbox(
                "Тип движения *",
                ["IN", "OUT", "TRANSFER", "INVENTORY"],
                format_func=lambda x: MOVEMENT_LABELS[x],
            )

            quantity = nc1.number_input("Количество *", min_value=0.001, step=1.0, format="%.3f")
            comment = nc2.text_input("Комментарий")

            # Hint about current stock
            st.info(
                f"Текущий остаток: **{float(sel_product['current_stock']):.3f} {sel_product['unit']}**"
                + (" → после инвентаризации станет: " + f"**{quantity:.3f}**"
                   if m_type == "INVENTORY" else "")
            )

            submitted = st.form_submit_button("Зарегистрировать движение", use_container_width=True)
            if submitted:
                try:
                    api.create_movement({
                        "product_id": sel_product["id"],
                        "movement_type": m_type,
                        "quantity": quantity,
                        "comment": comment or None,
                    })
                    st.success(f"Движение зарегистрировано! Тип: {MOVEMENT_LABELS[m_type]}")
                    st.rerun()
                except Exception as e:
                    st.error(f"Ошибка: {e}")
