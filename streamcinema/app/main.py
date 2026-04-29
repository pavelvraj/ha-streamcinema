import hashlib
import json
import os
import re
from datetime import datetime
from pathlib import Path

from fastapi import Body, FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.database import get_db_connection, init_db
from app.scrapers.csfd import CSFDScraper
from app.scrapers.fastshare import FastshareScraper
from app.scrapers.imdb import IMDBScraper
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
IMDB = IMDBScraper()

app = FastAPI(title="StreamCinema API")


@app.middleware("http")
async def normalize_ingress_path(request, call_next):
    path = request.scope.get("path", "/")
    while "//" in path:
        path = path.replace("//", "/")
    request.scope["path"] = path or "/"
    return await call_next(request)


@app.on_event("startup")
def startup():
    init_db()


def stable_manual_id(query: str) -> str:
    digest = hashlib.sha1(query.strip().lower().encode("utf-8")).hexdigest()[:16]
    return f"manual_{digest}"


def stable_imdb_id(imdb_id: str) -> str:
    return f"imdb_{imdb_id}"


def safe_json_loads(value, fallback):
    if not value:
        return fallback
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return fallback


def json_dumps(value):
    return json.dumps(value or [], ensure_ascii=False)


def parse_stream_info(filename):
    name = filename or ""
    lower = name.lower()

    season = None
    episode = None
    match = re.search(r"\b[sS](\d{1,2})[ ._-]*[eE](\d{1,3})\b", name)
    if not match:
        match = re.search(r"\b(\d{1,2})[xX](\d{1,3})\b", name)
    if match:
        season = int(match.group(1))
        episode = int(match.group(2))

    extension = Path(name).suffix.lower().lstrip(".")
    if not extension:
        for candidate in ("mkv", "mp4", "avi", "m4v", "mov", "wmv"):
            if f".{candidate}" in lower:
                extension = candidate
                break

    width = None
    height = None
    if "2160" in lower or "4k" in lower:
        width, height = 3840, 2160
    elif "1080" in lower:
        width, height = 1920, 1080
    elif "720" in lower:
        width, height = 1280, 720

    return {
        "season": season,
        "episode": episode,
        "format": extension.upper() if extension else "",
        "width": width,
        "height": height,
    }


def infer_media_type(streams, metadata):
    if metadata.get("type") in ("movie", "tvshow"):
        return metadata["type"]
    for stream in streams:
        info = parse_stream_info(stream.get("name") or stream.get("filename"))
        if info["season"] is not None and info["episode"] is not None:
            return "tvshow"
    return "movie"


def metadata_for_query(query):
    csfd_data = CSFD.search_movie(query)
    if csfd_data:
        return {
            "source": "csfd",
            "id": f"csfd_{csfd_data['csfd_id']}",
            "type": csfd_data.get("type") or "movie",
            "title": csfd_data.get("title") or query,
            "original_title": csfd_data.get("original_title") or "",
            "year": csfd_data.get("year") or 0,
            "plot": csfd_data.get("plot") or "",
            "poster": csfd_data.get("poster") or "",
            "fanart": csfd_data.get("fanart") or csfd_data.get("poster") or "",
            "rating": csfd_data.get("rating") or 0.0,
            "genres": csfd_data.get("genres") or [],
            "csfd_id": csfd_data.get("csfd_id"),
            "imdb_id": csfd_data.get("imdb_id"),
        }

    imdb_data = IMDB.search_movie(query)
    if imdb_data:
        imdb_id = imdb_data.get("imdb_id")
        return {
            "source": "imdb",
            "id": stable_imdb_id(imdb_id),
            "type": imdb_data.get("type") or "movie",
            "title": imdb_data.get("title") or query,
            "original_title": "",
            "year": imdb_data.get("year") or 0,
            "plot": imdb_data.get("plot") or "",
            "poster": imdb_data.get("poster") or "",
            "fanart": imdb_data.get("poster") or "",
            "rating": imdb_data.get("rating") or 0.0,
            "genres": imdb_data.get("genres") or [],
            "csfd_id": None,
            "imdb_id": imdb_id,
        }

    return {
        "source": "manual",
        "id": stable_manual_id(query),
        "type": "movie",
        "title": query,
        "original_title": "",
        "year": 0,
        "plot": "Nenalezeno na CSFD ani IMDb",
        "poster": "",
        "fanart": "",
        "rating": 0.0,
        "genres": [],
        "csfd_id": None,
        "imdb_id": None,
    }


def search_provider_streams(query):
    all_files = []
    for scraper in (WS, FS):
        try:
            all_files.extend(scraper.search(query))
        except Exception as exc:
            print(f"{scraper.__class__.__name__} search failed: {exc}")

    streams = []
    seen = set()
    for item in all_files:
        provider = item.get("provider")
        ident = item.get("ident")
        if not provider or not ident or (provider, ident) in seen:
            continue
        seen.add((provider, ident))

        filename = item.get("name") or item.get("filename") or ""
        info = parse_stream_info(filename)
        streams.append(
            {
                "provider": provider,
                "ident": ident,
                "filename": filename,
                "size": int(item.get("size") or 0),
                "duration": item.get("duration"),
                "width": item.get("width") or info["width"],
                "height": item.get("height") or info["height"],
                "format": item.get("format") or info["format"],
                "season": item.get("season") or info["season"],
                "episode": item.get("episode") or info["episode"],
            }
        )
    return streams


def upsert_media(conn, metadata, selected_streams):
    media_type = infer_media_type(selected_streams, metadata)
    media_id = metadata.get("id") or stable_manual_id(metadata.get("title") or "media")

    conn.execute(
        """
        INSERT INTO media (
            id, type, title, original_title, year, genres, rating, plot,
            poster, fanart, imdb_id, csfd_id
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            type=excluded.type,
            title=excluded.title,
            original_title=excluded.original_title,
            year=excluded.year,
            genres=excluded.genres,
            rating=excluded.rating,
            plot=excluded.plot,
            poster=excluded.poster,
            fanart=excluded.fanart,
            imdb_id=excluded.imdb_id,
            csfd_id=excluded.csfd_id
        """,
        (
            media_id,
            media_type,
            metadata.get("title") or "",
            metadata.get("original_title") or "",
            metadata.get("year") or 0,
            json_dumps(metadata.get("genres")),
            metadata.get("rating") or 0.0,
            metadata.get("plot") or "",
            metadata.get("poster") or "",
            metadata.get("fanart") or metadata.get("poster") or "",
            metadata.get("imdb_id"),
            metadata.get("csfd_id"),
        ),
    )

    for stream in selected_streams:
        add_stream(conn, media_id, stream)

    return media_id


def add_stream(conn, media_id, stream):
    provider = stream.get("provider")
    ident = stream.get("ident")
    if not provider or not ident:
        return

    exists = conn.execute(
        "SELECT 1 FROM streams WHERE provider=? AND ident=?",
        (provider, ident),
    ).fetchone()
    if exists:
        return

    filename = stream.get("filename") or stream.get("name") or ""
    info = parse_stream_info(filename)
    conn.execute(
        """
        INSERT INTO streams (
            media_id, provider, ident, filename, size, duration, width, height,
            season, episode, status, format, audio, subtitles
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', ?, ?, ?)
        """,
        (
            media_id,
            provider,
            ident,
            filename,
            int(stream.get("size") or 0),
            stream.get("duration"),
            stream.get("width") or info["width"],
            stream.get("height") or info["height"],
            stream.get("season") or info["season"],
            stream.get("episode") or info["episode"],
            stream.get("format") or info["format"],
            json_dumps(stream.get("audio") or [{"language": "cze"}]),
            json_dumps(stream.get("subtitles") or []),
        ),
    )


def serialize_stream_row(row):
    s = dict(row)
    return {
        "id": s.get("id"),
        "ident": f"{s.get('provider')}:{s.get('ident')}",
        "provider": s.get("provider"),
        "provider_ident": s.get("ident"),
        "filename": s.get("filename") or "",
        "size": s.get("size") or 0,
        "duration": s.get("duration"),
        "width": s.get("width"),
        "height": s.get("height"),
        "format": s.get("format") or "",
        "season": s.get("season"),
        "episode": s.get("episode"),
        "status": s.get("status") or "active",
        "last_checked_at": s.get("last_checked_at"),
        "audio": safe_json_loads(s.get("audio"), [{"language": "cze"}]),
        "subtitles": safe_json_loads(s.get("subtitles"), []),
    }


def group_episodes(streams):
    seasons = {}
    for stream in streams:
        season = stream.get("season")
        episode = stream.get("episode")
        if season is None or episode is None:
            continue
        seasons.setdefault(str(season), {}).setdefault(str(episode), []).append(stream)

    return [
        {
            "season": int(season),
            "episodes": [
                {
                    "episode": int(episode),
                    "streams": episode_streams,
                }
                for episode, episode_streams in sorted(
                    episodes.items(), key=lambda item: int(item[0])
                )
            ],
        }
        for season, episodes in sorted(seasons.items(), key=lambda item: int(item[0]))
    ]


def serialize_media_row(conn, row, include_streams=True):
    media = dict(row)
    streams = []
    if include_streams:
        stream_rows = conn.execute(
            "SELECT * FROM streams WHERE media_id=? ORDER BY season, episode, provider, filename",
            (media["id"],),
        ).fetchall()
        streams = [serialize_stream_row(s) for s in stream_rows]

    return {
        "_id": media["id"],
        "type": media.get("type") or "movie",
        "title": media.get("title") or "",
        "original_title": media.get("original_title") or "",
        "year": media.get("year") or 0,
        "genres": safe_json_loads(media.get("genres"), []),
        "rating": media.get("rating") or 0,
        "plot": media.get("plot") or "",
        "poster": media.get("poster") or "",
        "fanart": media.get("fanart") or media.get("poster") or "",
        "imdb_id": media.get("imdb_id"),
        "csfd_id": media.get("csfd_id"),
        "stream_count": len(streams),
        "streams": streams,
        "seasons": group_episodes(streams),
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
    }


def check_stream(stream):
    provider = stream["provider"]
    ident = stream["ident"]
    try:
        if provider == "webshare":
            link = WS.get_link(ident)
        elif provider == "fastshare":
            link = FS.get_link(ident)
        else:
            link = None
        return "active" if link else "pending_delete"
    except Exception as exc:
        print(f"Stream check error: {exc}")
        return "pending_delete"


def search_and_save(query):
    metadata = metadata_for_query(query)
    streams = search_provider_streams(query)
    metadata["type"] = infer_media_type(streams, metadata)
    conn = get_db_connection()
    try:
        media_id = upsert_media(conn, metadata, streams)
        conn.commit()
        return [media_id]
    finally:
        conn.close()


@app.get("/")
async def read_index():
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/api/ping")
def ping():
    return {"status": "ok", "message": "pong"}


@app.get("/api/catalog")
def catalog(q: str = "", media_type: str = "all"):
    conn = get_db_connection()
    try:
        clauses = []
        params = []
        if q:
            clauses.append("title LIKE ?")
            params.append(f"%{q}%")
        if media_type in ("movie", "tvshow"):
            clauses.append("type=?")
            params.append(media_type)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = conn.execute(
            f"SELECT * FROM media {where} ORDER BY title COLLATE NOCASE",
            params,
        ).fetchall()
        data = [serialize_media_row(conn, row, include_streams=True) for row in rows]
        return {"data": data, "totalCount": len(data)}
    finally:
        conn.close()


@app.get("/api/media/{media_id}")
def media_detail(media_id: str):
    conn = get_db_connection()
    try:
        row = conn.execute("SELECT * FROM media WHERE id=?", (media_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Media not found")
        return serialize_media_row(conn, row, include_streams=True)
    finally:
        conn.close()


@app.get("/api/search")
def search_preview(q: str):
    query = q.strip()
    if not query:
        return {"metadata": None, "streams": []}

    metadata = metadata_for_query(query)
    streams = search_provider_streams(query)
    metadata["type"] = infer_media_type(streams, metadata)
    return {"metadata": metadata, "streams": streams, "totalCount": len(streams)}


@app.post("/api/media")
def add_media(payload: dict = Body(...)):
    metadata = payload.get("metadata") or {}
    streams = payload.get("streams") or []
    if not metadata.get("title"):
        raise HTTPException(status_code=400, detail="Missing media metadata")
    if not streams:
        raise HTTPException(status_code=400, detail="Select at least one stream")

    conn = get_db_connection()
    try:
        media_id = upsert_media(conn, metadata, streams)
        conn.commit()
        row = conn.execute("SELECT * FROM media WHERE id=?", (media_id,)).fetchone()
        return serialize_media_row(conn, row, include_streams=True)
    finally:
        conn.close()


@app.get("/api/search_manual")
def manual_search(q: str):
    media_ids = search_and_save(q)
    return {"status": "ok", "found_ids": media_ids}


@app.post("/api/media/{media_id}/check_streams")
def check_media_streams(media_id: str):
    conn = get_db_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM streams WHERE media_id=? ORDER BY id",
            (media_id,),
        ).fetchall()
        checked = []
        now = datetime.utcnow().isoformat(timespec="seconds")
        for row in rows:
            stream = dict(row)
            status = check_stream(stream)
            conn.execute(
                "UPDATE streams SET status=?, last_checked_at=? WHERE id=?",
                (status, now, stream["id"]),
            )
            stream["status"] = status
            stream["last_checked_at"] = now
            checked.append(serialize_stream_row(stream))
        conn.commit()
        return {"checked": checked}
    finally:
        conn.close()


@app.post("/api/streams/{stream_id}/check")
def check_single_stream(stream_id: int):
    conn = get_db_connection()
    try:
        row = conn.execute("SELECT * FROM streams WHERE id=?", (stream_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Stream not found")
        stream = dict(row)
        status = check_stream(stream)
        now = datetime.utcnow().isoformat(timespec="seconds")
        conn.execute(
            "UPDATE streams SET status=?, last_checked_at=? WHERE id=?",
            (status, now, stream_id),
        )
        conn.commit()
        stream["status"] = status
        stream["last_checked_at"] = now
        return serialize_stream_row(stream)
    finally:
        conn.close()


@app.delete("/api/streams/{stream_id}")
def delete_stream(stream_id: int):
    conn = get_db_connection()
    try:
        conn.execute("DELETE FROM streams WHERE id=?", (stream_id,))
        conn.commit()
        return {"status": "ok"}
    finally:
        conn.close()


@app.delete("/api/media/{media_id}/pending_streams")
def delete_pending_streams(media_id: str):
    conn = get_db_connection()
    try:
        cursor = conn.execute(
            "DELETE FROM streams WHERE media_id=? AND status='pending_delete'",
            (media_id,),
        )
        conn.commit()
        return {"status": "ok", "deleted": cursor.rowcount}
    finally:
        conn.close()


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
