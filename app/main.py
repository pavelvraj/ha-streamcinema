from fastapi import FastAPI, Query
from typing import Optional
import sqlite3, json
import os

app = FastAPI(title="StreamCinema Local API")
DB = "/config/streamcinema/data/db.sqlite"

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

@app.get("/")
def read_root():
    return {"Status": "StreamCinema API is running", "DB_Path": "/config/streamcinema/data"}

@app.get("/api/ping")
def ping():
    return "pong"

@app.get("/api/media/{collection}/filter/{filter_name}/{filter_value}/")
def media_filter(collection: str, filter_name: str, filter_value: str, page: int = 1):
    db = get_db()
    media_type = "movie" if collection == "movies" else "tvshow"
    
    if filter_name == "titleOrActor":
        rows = db.execute(
            "SELECT * FROM media WHERE type=? AND title LIKE ? LIMIT 20 OFFSET ?",
            (media_type, f"%{filter_value}%", (page-1)*20)
        ).fetchall()
    elif filter_name == "genre":
        rows = db.execute(
            "SELECT * FROM media WHERE type=? AND genres LIKE ? LIMIT 20 OFFSET ?",
            (media_type, f"%{filter_value}%", (page-1)*20)
        ).fetchall()
    else:
        rows = []
    
    data = []
    for row in rows:
        item = dict(row)
        item["streams"] = db.execute(
            "SELECT * FROM streams WHERE media_id=?", (item["id"],)
        ).fetchall()
        item["info_labels"] = {
            "title": item["title"], "year": item["year"],
            "genre": json.loads(item["genres"] or "[]"),
            "plot": item["plot"], "rating": item["rating"],
            "playcount": 0
        }
        item["art"] = {"poster": item["poster"], "fanart": item["fanart"]}
        item["services"] = {"imdb": item["imdb_id"]}
        data.append(item)
    
    total = db.execute(
        "SELECT COUNT(*) FROM media WHERE type=?", (media_type,)
    ).fetchone()[0]
    
    return {"data": data, "totalCount": len(data), "page": page, "pageCount": total//20+1}

@app.get("/api/media/{collection}/popular/-1/")
def popular_media(collection: str):
    db = get_db()
    media_type = "movie" if collection == "movies" else "tvshow"
    rows = db.execute(
        "SELECT * FROM media WHERE type=? ORDER BY csfd_rating DESC LIMIT 20",
        (media_type,)
    ).fetchall()
    # stejná serializace jako výše...
    return {"data": [dict(r) for r in rows], "totalCount": len(rows)}
