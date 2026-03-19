import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="Аналитика | Торнус Склад", page_icon="📈", layout="wide")

if not st.session_state.get("authenticated"):
    st.warning("Необходима авторизация")
    st.stop()

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import api_client as api

with st.sidebar:
    if st.button("Выйти", use_container_width=True):
        st.session_state.authenticated = False
        st.rerun()
st.title("📈 Аналитика")

# ── График движений ───────────────────────────────────────────────────────────
st.subheader("График движений за период")

days = st.slider("Период (дней)", min_value=7, max_value=365, value=30, step=7)

try:
    chart_data = api.get_movements_chart(days=days)
except Exception as e:
    st.error(f"Ошибка: {e}")
    st.stop()

if chart_data:
    df_chart = pd.DataFrame(chart_data)
    df_chart["date"] = pd.to_datetime(df_chart["date"])

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df_chart["date"], y=df_chart["in_qty"],
        name="Приход", marker_color="#2ecc71",
    ))
    fig.add_trace(go.Bar(
        x=df_chart["date"], y=df_chart["out_qty"],
        name="Расход", marker_color="#e74c3c",
    ))
    fig.update_layout(
        barmode="group",
        xaxis_title="Дата",
        yaxis_title="Количество",
        legend_title="Тип",
        height=400,
        margin=dict(l=0, r=0, t=20, b=0),
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Нет данных о движениях за выбранный период.")

st.divider()

# ── Топ товаров ───────────────────────────────────────────────────────────────
col_top, col_pie = st.columns([3, 2])

with col_top:
    st.subheader("🏆 Топ товаров по оборачиваемости (расход)")
    top_limit = st.slider("Кол-во товаров", 5, 20, 10)
    try:
        top_products = api.get_top_products(limit=top_limit)
    except Exception as e:
        st.error(f"Ошибка: {e}")
        top_products = []

    if top_products:
        df_top = pd.DataFrame(top_products)
        df_top = df_top[df_top["total_out"] > 0].head(top_limit)
        if not df_top.empty:
            fig_top = px.bar(
                df_top,
                x="total_out",
                y="name",
                orientation="h",
                labels={"total_out": "Расход (всего)", "name": "Товар"},
                color="total_out",
                color_continuous_scale="Reds",
                height=max(300, len(df_top) * 35),
            )
            fig_top.update_layout(showlegend=False, margin=dict(l=0, r=0, t=20, b=0))
            fig_top.update_yaxes(categoryorder="total ascending")
            st.plotly_chart(fig_top, use_container_width=True)
        else:
            st.info("Нет данных о расходе.")
    else:
        st.info("Нет данных.")

with col_pie:
    st.subheader("📊 Структура склада по категориям")
    try:
        products = api.get_products()
    except Exception as e:
        st.error(f"Ошибка: {e}")
        products = []

    if products:
        df_p = pd.DataFrame(products)
        df_p["value"] = df_p["current_stock"].astype(float) * df_p["price"].astype(float)
        df_cat = df_p.groupby(df_p["category"].fillna("Без категории"))["value"].sum().reset_index()
        df_cat.columns = ["Категория", "Стоимость"]
        df_cat = df_cat[df_cat["Стоимость"] > 0]
        if not df_cat.empty:
            fig_pie = px.pie(
                df_cat,
                values="Стоимость",
                names="Категория",
                height=350,
            )
            fig_pie.update_layout(margin=dict(l=0, r=0, t=20, b=0))
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("Нет данных о стоимости по категориям.")

st.divider()

# ── Таблица топ-товаров ───────────────────────────────────────────────────────
st.subheader("Детализация по топ-товарам")
if top_products:
    df_detail = pd.DataFrame(top_products)
    df_detail = df_detail.rename(columns={
        "name": "Наименование",
        "sku": "Артикул",
        "category": "Категория",
        "unit": "Ед.",
        "total_in": "Приход (всего)",
        "total_out": "Расход (всего)",
    })
    st.dataframe(
        df_detail[["Наименование", "Артикул", "Категория", "Ед.", "Приход (всего)", "Расход (всего)"]],
        use_container_width=True,
        hide_index=True,
    )
