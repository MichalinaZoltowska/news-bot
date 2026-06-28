import sqlite3
import logging
from datetime import datetime
import feedparser
import streamlit as st
from thefuzz import fuzz

st.set_page_config(page_title="Newsy", layout="centered")
st.title("Najswiezsze Newsy Polityczne")

DB_NAME = "news_database.db"
SIMILARITY_THRESHOLD = 75 

RSS_FEEDS = {
    "TVN24 Najnowsze": "https://tvn24.pl/najnowsze.xml",
    "Rzeczpospolita": "https://www.rp.pl/rss/11",
    "PAP (Kraj)": "https://www.pap.pl/rss/pl/1",
    "PAP (Świat)": "https://www.pap.pl/rss/pl/2",
    "Polskie Radio": "https://www.polskieradio.pl/stacja/3/rss.aspx",
    "Dziennik Gazeta Prawna": "https://gospodarka.dziennik.pl/rss.xml"
}

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT UNIQUE, url TEXT UNIQUE,
            source TEXT, published_at TEXT, fetched_at TEXT
        )
    ''')
    # Tabela pomocnicza, zeby pamietac, kiedy ostatnio pobieralismy dane
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS last_update (id INTEGER PRIMARY KEY, timestamp TEXT)
    ''')
    conn.commit()
    conn.close()

def fetch_news_if_needed():
    """Pobiera newsy tylko, jesli od ostatniego pobrania minelo ponad 2 godziny."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute("SELECT timestamp FROM last_update WHERE id = 1")
    row = cursor.fetchone()
    
    now = datetime.now()
    should_update = False
    
    if not row:
        should_update = True
    else:
        last_time = datetime.fromisoformat(row[0])
        # Sprawdzamy czy minely 2 godziny (7200 sekund)
        if (now - last_time).total_seconds() > 7200:
            should_update = True
            
    if should_update:
        # Pobieramy dane z ostatnich tytułów do deduplikacji
        cursor.execute("SELECT title FROM articles ORDER BY id DESC LIMIT 100")
        recent_titles = [r[0] for r in cursor.fetchall()]

        for source_name, url in RSS_FEEDS.items():
            try:
                feed = feedparser.parse(url, agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
                for entry in feed.entries:
                    title = getattr(entry, 'title', '').strip()
                    link = getattr(entry, 'link', '')
                    if not link and hasattr(entry, 'id'): link = entry.id
                    link = link.strip()
                    
                    if not title or not link: continue

                    # Rozmyta deduplikacja
                    is_dup = False
                    for existing_title in recent_titles:
                        if fuzz.partial_ratio(title.lower(), existing_title.lower()) >= SIMILARITY_THRESHOLD:
                            is_dup = True
                            break
                    if is_dup: continue

                    try:
                        cursor.execute('''
                            INSERT OR IGNORE INTO articles (title, url, source, published_at, fetched_at)
                            VALUES (?, ?, ?, ?, ?)
                        ''', (title, link, source_name, getattr(entry, 'published', now.isoformat()), now.isoformat()))
                    except:
                        continue
            except:
                continue
                
        # Zapisujemy czas obecnej aktualizacji
        cursor.execute("INSERT OR REPLACE INTO last_update (id, timestamp) VALUES (1, ?)", (now.isoformat(),))
        conn.commit()
        
    conn.close()

def get_news():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT title, url, source, fetched_at FROM articles ORDER BY id DESC LIMIT 50")
    data = cursor.fetchall()
    conn.close()
    return data

# Uruchomienie darmowego mechanizmu
init_db()
with st.spinner("Sprawdzam swieze newsy..."):
    fetch_news_if_needed()

news_list = get_news()

if not news_list:
    st.info("Pobieram pierwsze dane, odswiez strone za chwile...")
else:
    st.write("Aktualizacja automatyczna przy odwiedzinach strony (maksymalnie co 2 godziny).")
    for title, url, source, fetched_at in news_list:
        st.markdown(f"### [{title}]({url})")
        st.caption(f"Zrodlo: {source}")
        st.markdown("---")
