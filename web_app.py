import streamlit as st


picture = st.camera_input("Сделать фото")

if picture is not None:
    st.image(picture)
