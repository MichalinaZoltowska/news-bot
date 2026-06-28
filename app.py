import sqlite3
import streamlit as st

st.set_page_config(page_title="Newsy", layout="centered")

st.title("Najswiezsze Newsy Polityczne")
st.write("Aktualizacja automatyczna co 2-3 godziny.")

def get_news():
    conn = sqlite3.connect("news_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT title, url, source, fetched_at FROM articles ORDER BY id DESC LIMIT 50")
    data = cursor.fetchall()
    conn.close()
    return data

news_list = get_news()

if not news_list:
    st.info("Baza danych jest jeszcze pusta.")
else:
    for title, url, source, fetched_at in news_list:
        st.markdown(f"### [{title}]({url})")
        st.caption(f"Zrodlo: {source}")
        st.markdown("---")
