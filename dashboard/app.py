import os
import streamlit as st

st.set_page_config(
    page_title="Торнус Склад",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded",
)

DASHBOARD_PASSWORD = os.getenv("DASHBOARD_PASSWORD", "admin123")


def check_auth():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if st.session_state.authenticated:
        return True

    st.title("📦 Торнус Склад")
    st.subheader("Вход в систему")

    with st.form("login_form"):
        password = st.text_input("Пароль", type="password")
        submitted = st.form_submit_button("Войти", use_container_width=True)
        if submitted:
            if password == DASHBOARD_PASSWORD:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Неверный пароль")

    return False


if not check_auth():
    st.stop()

# ── Sidebar ──────────────────────────────────────────────────────────────────
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

# ── Main page ─────────────────────────────────────────────────────────────────
st.title("📦 Торнус Склад")
st.markdown(
    """
    Добро пожаловать в систему управления складом.

    Используйте навигацию в боковой панели для работы с системой:

    | Страница | Описание |
    |----------|----------|
    | **📊 Сводка** | Ключевые показатели, остатки, предупреждения |
    | **📋 Товары** | Справочник товаров: просмотр, добавление, редактирование |
    | **🔄 Движения** | Журнал движений: приход, расход, перемещение, инвентаризация |
    | **📈 Аналитика** | Графики, топ-товары, динамика оборота |
    | **📥 Импорт** | Загрузка товаров из CSV файлов |
    """
)
