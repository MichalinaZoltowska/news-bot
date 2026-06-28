import sqlite3
import streamlit as st

st.set_page_config(page_title="Newsy", layout="centered")

st.title("Najswiezsze Newsy Polityczne")
st.write("Aktualizacja automatyczna co 2-3 godziny.")

# Funkcja gwarantujaca, ze tabela bedzie istniala
def init_db():
    conn = sqlite3.connect("news_database.db")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT UNIQUE,
            url TEXT UNIQUE,
            source TEXT,
            published_at TEXT,
            fetched_at TEXT
        )
    ''')
    conn.commit()
    conn.close()

def get_news():
    conn = sqlite3.connect("news_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT title, url, source, fetched_at FROM articles ORDER BY id DESC LIMIT 50")
    data = cursor.fetchall()
    conn.close()
    return data

# Najpierw upewniamy sie, ze tabela istnieje, potem czytamy dane
init_db()
news_list = get_news()

if not news_list:
    st.info("Baza danych jest jeszcze pusta. Poczekaj na pierwsze automatyczne pobranie danych przez Cron Job.")
else:
    for title, url, source, fetched_at in news_list:
        st.markdown(f"### [{title}]({url})")
        st.caption(f"Zrodlo: {source}")
        st.markdown("---")
