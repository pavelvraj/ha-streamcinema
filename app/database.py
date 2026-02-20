import sqlite3
import os

DB_PATH = "/config/streamcinema/data/db.sqlite"

def get_db_connection():
    # Zajistíme existenci složky
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    
    # Tabulka médií (filmy/seriály)
    c.execute('''
        CREATE TABLE IF NOT EXISTS media (
            id TEXT PRIMARY KEY,
            type TEXT DEFAULT 'movie',
            title TEXT,
            original_title TEXT,
            year INTEGER,
            genres TEXT,        -- JSON list
            rating REAL,
            plot TEXT,
            poster TEXT,
            fanart TEXT,
            imdb_id TEXT,
            csfd_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Tabulka streamů (odkazy na soubory)
    c.execute('''
        CREATE TABLE IF NOT EXISTS streams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            media_id TEXT,
            provider TEXT,      -- 'webshare' nebo 'fastshare'
            ident TEXT,         -- ID souboru u providera
            filename TEXT,
            size INTEGER,
            duration INTEGER,
            width INTEGER,
            height INTEGER,
            audio TEXT,         -- JSON
            subtitles TEXT,     -- JSON
            FOREIGN KEY(media_id) REFERENCES media(id) ON DELETE CASCADE
        )
    ''')
    
    conn.commit()
    conn.close()

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn
