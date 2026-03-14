import streamlit as st
import pandas as pd

st.set_page_config(page_title="Сводка | Торнус Склад", page_icon="📊", layout="wide")

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

st.title("📊 Сводка по складу")

try:
    summary = api.get_summary()
    low_stock = api.get_low_stock()
except Exception as e:
    st.error(f"Ошибка подключения к API: {e}")
    st.stop()

# ── Метрики ───────────────────────────────────────────────────────────────────
col1, col2, col3, col4, col5, col6 = st.columns(6)
col1.metric("Всего товаров", summary["total_products"])
col2.metric("В наличии (SKU)", summary["total_sku_count"])
col3.metric("⚠️ Низкий остаток", summary["low_stock_count"])
col4.metric("Стоимость склада", f"₽ {float(summary['total_stock_value']):,.0f}")
col5.metric("Движений сегодня", summary["movements_today"])
col6.metric("Движений за месяц", summary["movements_this_month"])

st.divider()

# ── Низкий остаток ────────────────────────────────────────────────────────────
if low_stock:
    st.subheader(f"⚠️ Товары с низким остатком ({len(low_stock)})")
    df = pd.DataFrame(low_stock)
    df = df.rename(columns={
        "name": "Наименование",
        "sku": "Артикул",
        "category": "Категория",
        "unit": "Ед.",
        "current_stock": "Текущий остаток",
        "min_stock": "Мин. остаток",
        "deficit": "Дефицит",
    })
    df = df[["Наименование", "Артикул", "Категория", "Ед.", "Текущий остаток", "Мин. остаток", "Дефицит"]]
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Дефицит": st.column_config.NumberColumn(format="%.3f", help="Нужно пополнить"),
        },
    )
else:
    st.success("Все товары в норме — нет позиций с низким остатком.")

st.divider()

# ── Остатки по всем товарам ───────────────────────────────────────────────────
st.subheader("📦 Текущие остатки по всем товарам")

try:
    products = api.get_products()
except Exception as e:
    st.error(f"Ошибка: {e}")
    st.stop()

if products:
    df_p = pd.DataFrame(products)
    df_p["low"] = df_p.apply(
        lambda r: "⚠️" if float(r["min_stock"]) > 0 and float(r["current_stock"]) < float(r["min_stock"]) else "✅",
        axis=1,
    )
    df_p = df_p.rename(columns={
        "name": "Наименование",
        "sku": "Артикул",
        "category": "Категория",
        "unit": "Ед.",
        "price": "Цена",
        "current_stock": "Остаток",
        "min_stock": "Мин.",
        "low": "Статус",
    })
    st.dataframe(
        df_p[["Наименование", "Артикул", "Категория", "Ед.", "Цена", "Остаток", "Мин.", "Статус"]],
        use_container_width=True,
        hide_index=True,
    )
else:
    st.info("Нет товаров в базе данных.")
