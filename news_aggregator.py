import sqlite3
import logging
from datetime import datetime
import feedparser
from thefuzz import fuzz

# 1. Konfiguracja logowania (kluczowa na produkcji, by wiedzieć co nie działa)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("aggregator.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)

DB_NAME = "news_database.db"
SIMILARITY_THRESHOLD = 75  # Procent podobieństwa tytułów, powyżej którego uznajemy news za duplikat

# Lista przykładowych, stabilnych kanałów RSS w Polsce
RSS_FEEDS = {
    "PAP (Kraj)": "https://www.pap.pl/rss/pl/1",
    "PAP (Świat)": "https://www.pap.pl/rss/pl/2",
    "Polskie Radio (Wiadomości)": "https://www.polskieradio.pl/stacja/3/rss.aspx",
    "Dziennik Gazeta Prawna": "https://gospodarka.dziennik.pl/rss.xml",
    "Rzeczpospolita": "https://www.rp.pl/rss/11"
}

def init_db():
    """Inicjalizuje bazę danych SQLite, jeśli jeszcze nie istnieje."""
    with sqlite3.connect(DB_NAME) as conn:
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
    logging.info("Baza danych została zainicjalizowana.")

def is_duplicate(cursor, new_title):
    """
    Sprawdza, czy w bazie (z ostatnich 24 godzin) istnieje artykuł 
    o tytule bardzo podobnym do nowego (odporność na drobne zmiany w tytule).
    """
    # Pobieramy tylko w miarę świeże artykuły, żeby nie przeciążać pętli
    cursor.execute("SELECT title FROM articles ORDER BY id DESC LIMIT 100")
    recent_titles = [row[0] for row in cursor.fetchall()]

    for existing_title in recent_titles:
        # fuzz.partial_ratio dobrze radzi sobie z podobnymi nagłówkami prasowymi
        similarity = fuzz.partial_ratio(new_title.lower(), existing_title.lower())
        if similarity >= SIMILARITY_THRESHOLD:
            logging.debug(f"Wykryto duplikat: '{new_title}' jest podobny do '{existing_title}' ({similarity}%)")
            return True
    return False

def fetch_and_save_news():
    """Główna funkcja pobierająca, filtrująca i zapisująca dane."""
    logging.info("Rozpoczęto pobieranie newsów z kanałów RSS...")
    
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        
        articles_added = 0
        duplicates_skipped = 0

        for source_name, url in RSS_FEEDS.items():
            try:
                feed = feedparser.parse(url)
                logging.info(f"Pobieranie ze źródła: {source_name} (znaleziono {len(feed.entries)} wpisów)")
                
                for entry in feed.entries:
                    title = getattr(entry, 'title', '').strip()
                    link = getattr(entry, 'link', '').strip()
                    # Zabezpieczenie przed niepełnymi danymi w RSS
                    if not title or not link:
                        continue
                        
                    published = getattr(entry, 'published', datetime.now().isoformat())

                    # Krok 1: Sprawdzenie dokładnego duplikatu URL (najszybsze)
                    cursor.execute("SELECT 1 FROM articles WHERE url = ?", (link,))
                    if cursor.fetchone():
                        continue

                    # Krok 2: Rozmyte sprawdzanie duplikatów po tytule (Fuzzy Matching)
                    if is_duplicate(cursor, title):
                        duplicates_skipped += 1
                        continue

                    # Krok 3: Zapis do bazy danych
                    try:
                        cursor.execute('''
                            INSERT INTO articles (title, url, source, published_at, fetched_at)
                            VALUES (?, ?, ?, ?, ?)
                        ''', (title, link, source_name, published, datetime.now().isoformat()))
                        articles_added += 1
                    except sqlite3.IntegrityError:
                        # Dodatkowe zabezpieczenie przed unikalnością pól w SQLite
                        continue

            except Exception as e:
                logging.error(f"Błąd podczas przetwarzania źródła {source_name}: {str(e)}")

        conn.commit()
        logging.info(f"Zakończono cykl. Dodano nowych artykułów: {articles_added}. Odrzucono duplikatów: {duplicates_skipped}.")

if __name__ == "__main__":
    init_db()
    fetch_and_save_news()