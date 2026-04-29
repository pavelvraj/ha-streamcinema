import hashlib
import json
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.database import get_db_connection, init_db
from app.scrapers.csfd import CSFDScraper
from app.scrapers.fastshare import FastshareScraper
from app.scrapers.webshare import WebshareScraper


BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
OPTIONS_PATH = Path(os.getenv("STREAMCINEMA_OPTIONS_PATH", "/data/options.json"))


def load_config():
    if not OPTIONS_PATH.exists():
        return {}

    try:
        with OPTIONS_PATH.open(encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Config load error: {exc}")
        return {}


config = load_config()
WS = WebshareScraper(config.get("webshare_username"), config.get("webshare_password"))
FS = FastshareScraper(config.get("fastshare_username"), config.get("fastshare_password"))
CSFD = CSFDScraper()

app = FastAPI(title="StreamCinema API")


@app.on_event("startup")
def startup():
    init_db()


def stable_manual_id(query: str) -> str:
    digest = hashlib.sha1(query.strip().lower().encode("utf-8")).hexdigest()[:16]
    return f"manual_{digest}"


def safe_json_loads(value, fallback):
    if not value:
        return fallback
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return fallback


def serialize_media_row(conn, row):
    media = dict(row)
    streams = conn.execute(
        "SELECT * FROM streams WHERE media_id=? ORDER BY provider, filename",
        (media["id"],),
    ).fetchall()

    item = {
        "_id": media["id"],
        "type": media.get("type") or "movie",
        "info_labels": {
            "title": media.get("title") or "",
            "originaltitle": media.get("original_title") or "",
            "year": media.get("year") or 0,
            "plot": media.get("plot") or "",
            "rating": media.get("rating") or 0,
            "genre": safe_json_loads(media.get("genres"), []),
        },
        "art": {
            "poster": media.get("poster") or "",
            "fanart": media.get("fanart") or media.get("poster") or "",
        },
        "streams": [],
    }

    for stream in streams:
        s = dict(stream)
        item["streams"].append(
            {
                "ident": f"{s.get('provider')}:{s.get('ident')}",
                "filename": s.get("filename") or "",
                "size": s.get("size") or 0,
                "codec": "h264",
                "width": s.get("width") or 1920,
                "height": s.get("height") or 1080,
                "duration": s.get("duration"),
                "audio": safe_json_loads(s.get("audio"), [{"language": "cze"}]),
                "subtitles": safe_json_loads(s.get("subtitles"), []),
            }
        )

    return item


def search_and_save(query):
    query = query.strip()
    if not query:
        return []

    print(f"Searching: {query}")

    all_files = []
    for scraper in (WS, FS):
        try:
            all_files.extend(scraper.search(query))
        except Exception as exc:
            print(f"{scraper.__class__.__name__} search failed: {exc}")

    csfd_data = CSFD.search_movie(query)

    if csfd_data:
        media_id = f"csfd_{csfd_data['csfd_id']}"
        title = csfd_data.get("title") or query
        year = csfd_data.get("year") or 0
        plot = csfd_data.get("plot") or ""
        poster = csfd_data.get("poster") or ""
        rating = csfd_data.get("rating") or 0.0
        genres = json.dumps(csfd_data.get("genres") or [], ensure_ascii=False)
        csfd_id = csfd_data.get("csfd_id")
    else:
        media_id = stable_manual_id(query)
        title = query
        year = 0
        plot = "Nenalezeno na CSFD"
        poster = ""
        rating = 0.0
        genres = "[]"
        csfd_id = None

    conn = get_db_connection()
    try:
        conn.execute(
            """
            INSERT INTO media (id, type, title, year, plot, poster, rating, genres, csfd_id)
            VALUES (?, 'movie', ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                title=excluded.title,
                year=excluded.year,
                plot=excluded.plot,
                poster=excluded.poster,
                rating=excluded.rating,
                genres=excluded.genres,
                csfd_id=excluded.csfd_id
            """,
            (media_id, title, year, plot, poster, rating, genres, csfd_id),
        )

        for res in all_files:
            ident = res.get("ident")
            provider = res.get("provider")
            if not ident or not provider:
                continue

            exists = conn.execute(
                "SELECT 1 FROM streams WHERE ident=? AND provider=?",
                (ident, provider),
            ).fetchone()
            if exists:
                continue

            conn.execute(
                """
                INSERT INTO streams (media_id, provider, ident, filename, size)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    media_id,
                    provider,
                    ident,
                    res.get("name") or "",
                    int(res.get("size") or 0),
                ),
            )

        conn.commit()
    finally:
        conn.close()

    return [media_id]


@app.get("/")
async def read_index():
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/api/ping")
def ping():
    return {"status": "ok", "message": "pong"}


@app.get("/api/search_manual")
def manual_search(q: str):
    media_ids = search_and_save(q)
    return {"status": "ok", "found_ids": media_ids}


@app.get("/api/media/{collection}/filter/{filter_name}/{filter_value}/")
def media_filter(collection: str, filter_name: str, filter_value: str, page: int = 1):
    conn = get_db_connection()
    try:
        if filter_name == "titleOrActor":
            count = conn.execute(
                "SELECT COUNT(*) FROM media WHERE title LIKE ?",
                (f"%{filter_value}%",),
            ).fetchone()[0]

            if count == 0:
                search_and_save(filter_value)

            rows = conn.execute(
                "SELECT * FROM media WHERE title LIKE ? ORDER BY title",
                (f"%{filter_value}%",),
            ).fetchall()
        elif filter_name == "genre":
            rows = conn.execute(
                "SELECT * FROM media WHERE genres LIKE ? ORDER BY title",
                (f"%{filter_value}%",),
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM media ORDER BY title").fetchall()

        data = [serialize_media_row(conn, row) for row in rows]
        return {"data": data, "totalCount": len(data), "page": page, "pageCount": 1}
    finally:
        conn.close()


@app.get("/api/media/{collection}/popular/-1/")
def popular_media(collection: str):
    conn = get_db_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM media ORDER BY rating DESC, title LIMIT 20"
        ).fetchall()
        data = [serialize_media_row(conn, row) for row in rows]
        return {"data": data, "totalCount": len(data), "page": 1, "pageCount": 1}
    finally:
        conn.close()


@app.get("/api/file_link/{ident:path}")
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
    except Exception as exc:
        print(f"Link error: {exc}")
        return {"link": None}
