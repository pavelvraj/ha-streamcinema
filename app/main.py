from fastapi import FastAPI, HTTPException, BackgroundTasks
import sys,sqlite3, json, os

print("PYTHONPATH:", sys.path)
print("FILES IN /app:", os.listdir("/app"))
print("FILES IN /app/app:", os.listdir("/app/app"))

from app.database import init_db, get_db_connection
from app.scrapers.webshare import WebshareScraper
from app.scrapers.fastshare import FastshareScraper
from app.scrapers.csfd import CSFDScraper

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# Načtení konfigurace
OPTIONS_PATH = "/data/options.json"
config = {}
if os.path.exists(OPTIONS_PATH):
    with open(OPTIONS_PATH) as f: config = json.load(f)

WS = WebshareScraper(config.get("webshare_username"), config.get("webshare_password"))
FS = FastshareScraper(config.get("fastshare_username"), config.get("fastshare_password"))
CSFD = CSFDScraper()

app = FastAPI()

@app.on_event("startup")
def startup():
    init_db()

# --- Pomocné funkce ---
def search_and_save(query):
    """
    Spustí hledání na WS/FS/CSFD a uloží výsledky do DB.
    Vrací seznam nalezených médií.
    """
    print(f"Hledám: {query}")
    
    # 1. Scrape providerů
    ws_res = WS.search(query)
    fs_res = FS.search(query)
    all_files = ws_res + fs_res
    
    if not all_files:
        return []

    # 2. Scrape metadat (ČSFD)
    csfd_data = CSFD.search_movie(query)
    
    conn = get_db_connection()
    c = conn.cursor()

    # Identifikace média
    if csfd_data:
        media_id = f"csfd_{csfd_data['csfd_id']}"
        title = csfd_data['title']
        year = csfd_data['year']
        plot = csfd_data['plot']
        poster = csfd_data['poster']
        rating = csfd_data['rating']
        genres = json.dumps(csfd_data['genres'])
    else:
        # Fallback
        media_id = f"manual_{abs(hash(query))}"
        title = query
        year = 0
        plot = "Nenalezeno na ČSFD"
        poster = ""
        rating = 0.0
        genres = "[]"

    # 3. Uložení média
    c.execute('''
        INSERT OR REPLACE INTO media (id, title, year, plot, poster, rating, genres)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (media_id, title, year, plot, poster, rating, genres))
    
    # 4. Uložení streamů
    for res in all_files:
        c.execute("SELECT id FROM streams WHERE ident=? AND provider=?", (res['ident'], res['provider']))
        if not c.fetchone():
            c.execute('''
                INSERT INTO streams (media_id, provider, ident, filename, size)
                VALUES (?, ?, ?, ?, ?)
            ''', (media_id, res['provider'], res['ident'], res['name'], res['size']))
            
    conn.commit()
    conn.close()
    return [media_id]

# --- Endpointy ---

@app.get("/")
async def read_index():
    return FileResponse('/app/app/static/index.html')

# Mountování statických souborů
app.mount("/static", StaticFiles(directory="/app/app/static"), name="static")

@app.get("/api/ping")
def ping():
    return "pong"

# Nový endpoint pro manuální spuštění hledání (např. z webového GUI)
@app.get("/api/search_manual")
def manual_search(q: str):
    media_ids = search_and_save(q)
    return {"status": "ok", "found_ids": media_ids}

# KODI: Hlavní endpoint pro filtrování/hledání
@app.get("/api/media/{collection}/filter/{filter_name}/{filter_value}/")
def media_filter(collection: str, filter_name: str, filter_value: str, page: int = 1):
    conn = get_db_connection()
    c = conn.cursor()
    
    # Pokud KODI hledá podle názvu (titleOrActor),
    # zkusíme nejdřív najít v DB, a pokud nic nenajdeme, spustíme LIVE hledání!
    if filter_name == "titleOrActor":
        # Zkusíme najít v lokální DB
        c.execute("SELECT COUNT(*) FROM media WHERE title LIKE ?", (f"%{filter_value}%",))
        count = c.fetchone()[0]
        
        if count == 0:
            # Nic v DB -> Spustíme scraper!
            search_and_save(filter_value)

        # Teď už by tam data měla být
        c.execute("SELECT * FROM media WHERE title LIKE ?", (f"%{filter_value}%",))
    
    elif filter_name == "genre":
        c.execute("SELECT * FROM media WHERE genres LIKE ?", (f"%{filter_value}%",))
    else:
        # Fallback - vrátit vše (nebo nic)
        c.execute("SELECT * FROM media")
        
    rows = c.fetchall()
    
    data = []
    for row in rows:
        media = dict(row)
        # Načteme streamy k médiu
        c.execute("SELECT * FROM streams WHERE media_id=?", (media['id'],))
        streams = [dict(s) for s in c.fetchall()]
        
        # Formátování pro KODI
        item = {
            "_id": media['id'],
            "info_labels": {
                "title": media['title'],
                "originaltitle": media.get('original_title', ''),
                "year": media['year'],
                "plot": media['plot'],
                "rating": media['rating'],
                "genre": json.loads(media['genres'] or "[]")
            },
            "art": {
                "poster": media['poster'],
                "fanart": media['fanart'] or media['poster']
            },
            "streams": []
        }
        
        # Streamy
        for s in streams:
            # DŮLEŽITÉ: Prefixujeme providera do identu, aby plugin věděl, co s tím
            ident_combined = f"{s['provider']}:{s['ident']}"
            
            item["streams"].append({
                "ident": ident_combined,
                "size": s['size'],
                "codec": "h264",  # Placeholder
                "width": 1920,    # Placeholder
                "height": 1080,   # Placeholder
                "audio": [{"language": "cze"}],
                "subtitles": []
            })
        data.append(item)
    
    return {"data": data, "totalCount": len(data), "page": 1, "pageCount": 1}

# KODI: Popular (zatím vrátíme top hodnocené z DB)
@app.get("/api/media/{collection}/popular/-1/")
def popular_media(collection: str):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM media ORDER BY rating DESC LIMIT 20")
    rows = c.fetchall()
    
    # ... (stejná serializace jako výše) ...
    # Pro stručnost zkopíruj logiku z media_filter nebo si udělej pomocnou funkci
    # return {"data": serialized_rows, ...}
    return {"data": [], "totalCount": 0} # Placeholder

# NOVÝ: Helper pro získání linku (volaný z pluginu)
@app.get("/api/file_link/{ident}")
def get_file_link(ident: str):
    try:
        provider, file_id = ident.split(":", 1)
        if provider == "webshare":
            link = WS.get_link(file_id)
        elif provider == "fastshare":
            link = FS.get_link(file_id)
        else:
            link = None
        return {"link": link}
    except Exception as e:
        print(f"Link Error: {e}")
        return {"link": None}

