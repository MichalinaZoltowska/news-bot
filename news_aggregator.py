import sqlite3
import logging
from datetime import datetime
import feedparser
from thefuzz import fuzz

# Konfiguracja logowania
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("aggregator.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)

DB_NAME = "news_database.db"
SIMILARITY_THRESHOLD = 75 

# Aktualne, sprawdzone i stabilne źródła RSS
RSS_FEEDS = {
    "TVN24 Najnowsze": "https://tvn24.pl/najnowsze.xml",
    "Rzeczpospolita": "https://www.rp.pl/rss/11"
}

def init_db():
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
    logging.info("Baza danych zostala zainicjalizowana.")

def is_duplicate(cursor, new_title):
    cursor.execute("SELECT title FROM articles ORDER BY id DESC LIMIT 100")
    recent_titles = [row[0] for row in cursor.fetchall()]

    for existing_title in recent_titles:
        similarity = fuzz.partial_ratio(new_title.lower(), existing_title.lower())
        if similarity >= SIMILARITY_THRESHOLD:
            return True
    return False

def fetch_and_save_news():
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
                    
                    # Inteligentne szukanie linku (odporne na format Rzeczpospolitej)
                    link = getattr(entry, 'link', '')
                    if not link and hasattr(entry, 'id'):
                        link = entry.id
                    link = link.strip()
                    
                    if not title or not link:
                        continue
                        
                    published = getattr(entry, 'published', datetime.now().isoformat())

                    cursor.execute("SELECT 1 FROM articles WHERE url = ?", (link,))
                    if cursor.fetchone():
                        continue

                    if is_duplicate(cursor, title):
                        duplicates_skipped += 1
                        continue

                    try:
                        cursor.execute('''
                            INSERT INTO articles (title, url, source, published_at, fetched_at)
                            VALUES (?, ?, ?, ?, ?)
                        ''', (title, link, source_name, published, datetime.now().isoformat()))
                        articles_added += 1
                    except sqlite3.IntegrityError:
                        continue

            except Exception as e:
                logging.error(f"Blad podczas przetwarzania zrodla {source_name}: {str(e)}")

        conn.commit()
        logging.info(f"Zakonczono cykl. Dodano nowych artykulow: {articles_added}. Odrzucono duplikatow: {duplicates_skipped}.")

if __name__ == "__main__":
    init_db()
    fetch_and_save_news()
