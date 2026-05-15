import hashlib
import json
import os
import re
import unicodedata
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote, urlparse

import requests
from fastapi import Body, FastAPI, HTTPException
from fastapi import Request
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
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
CSFD = CSFDScraper(config.get("csfd_api_url"))
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


def clean_list(value):
    if isinstance(value, str):
        parts = re.split(r"[,;]", value)
    elif isinstance(value, list):
        parts = value
    else:
        parts = []

    cleaned = []
    seen = set()
    for item in parts:
        text = str(item or "").strip()
        key = text.lower()
        if text and key not in seen:
            cleaned.append(text)
            seen.add(key)
    return cleaned


def enabled_sources():
    sources = []
    if WS.username and WS.password:
        sources.append(("webshare", WS))
    if FS.username and FS.password:
        sources.append(("fastshare", FS))
    return sources


def ensure_search_sources():
    if not enabled_sources():
        raise HTTPException(
            status_code=400,
            detail="Nelze vyhledávat, dokud není v konfiguraci zadáno přihlášení alespoň k jednomu zdroji.",
        )


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
    else:
        match = re.search(
            r"\b(?:serie|série|season)\s*\.?\s*(\d{1,2})\D{0,12}(?:dil|díl|epizoda|episode|ep\.?)\s*\.?\s*(\d{1,3})\b",
            lower,
            re.I,
        )
        if match:
            season = int(match.group(1))
            episode = int(match.group(2))
        else:
            match = re.search(
                r"\b(\d{1,2})\D{0,12}(?:serie|série|season)\D{0,12}(\d{1,3})\D{0,6}(?:dil|díl|epizoda|episode|ep\.?)\b",
                lower,
                re.I,
            )
            if match:
                season = int(match.group(1))
                episode = int(match.group(2))
            else:
                match = re.search(r"\b(?:epizoda|episode|dil|díl|ep\.?)\s*\.?\s*(\d{1,3})\b", lower, re.I)
                if match:
                    season = 1
                    episode = int(match.group(1))

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


def normalize_search_text(value):
    text = unicodedata.normalize("NFKD", str(value or "").lower())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]+", "", text)


def query_terms(query):
    return [
        normalize_search_text(part)
        for part in re.split(r"\s+", str(query or "").strip())
        if normalize_search_text(part)
    ]


def stream_name_matches_query(filename, query):
    normalized_name = normalize_search_text(filename)
    terms = query_terms(query)
    return bool(normalized_name) and all(term in normalized_name for term in terms)


def infer_media_type(streams, metadata):
    if metadata.get("type") in ("movie", "tvshow"):
        return metadata["type"]
    for stream in streams:
        info = parse_stream_info(stream.get("name") or stream.get("filename"))
        if info["season"] is not None and info["episode"] is not None:
            return "tvshow"
    return "movie"


def metadata_for_query(query, media_type=None):
    csfd_data = CSFD.search_movie(query, media_type=media_type)
    if csfd_data:
        return {
            "source": "csfd",
            "id": f"csfd_{csfd_data['csfd_id']}",
            "type": media_type or csfd_data.get("type") or "movie",
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

    imdb_data = IMDB.search_movie(query, media_type=media_type)
    if imdb_data:
        imdb_id = imdb_data.get("imdb_id")
        return {
            "source": "imdb",
            "id": stable_imdb_id(imdb_id),
            "type": media_type or imdb_data.get("type") or "movie",
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
        "type": media_type or "movie",
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


def search_provider_streams(query, media_type="movie"):
    queries = [query]
    if media_type == "tvshow":
        queries.extend(series_search_queries(query))

    streams = []
    seen = set()
    for search_query in queries:
        for item in search_provider_files(search_query):
            provider = item.get("provider")
            ident = item.get("ident")
            if not provider or not ident or (provider, ident) in seen:
                continue

            filename = item.get("name") or item.get("filename") or ""
            if not stream_name_matches_query(filename, query):
                continue

            seen.add((provider, ident))
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
                    "stream_url": item.get("stream_url") or "",
                }
            )

    return sorted(
        streams,
        key=lambda item: (
            item.get("season") or 999,
            item.get("episode") or 999,
            item.get("provider") or "",
            item.get("filename") or "",
        ),
    )


def series_search_queries(query):
    extra = [f"{query} Epizoda"]
    for season in range(1, 9):
        extra.append(f"{query} S{season:02d}")
    return extra


def search_provider_files(query):
    all_files = []
    for _source_name, scraper in enabled_sources():
        try:
            all_files.extend(scraper.search(query))
        except Exception as exc:
            print(f"{scraper.__class__.__name__} search failed: {exc}")
    return all_files


def upsert_media(conn, metadata, selected_streams):
    media_type = infer_media_type(selected_streams, metadata)
    media_id = metadata.get("id") or stable_manual_id(metadata.get("title") or "media")

    conn.execute(
        """
        INSERT INTO media (
            id, type, title, original_title, year, genres, rating, plot,
            poster, fanart, imdb_id, csfd_id, search_query
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            csfd_id=excluded.csfd_id,
            search_query=excluded.search_query
        """,
        (
            media_id,
            media_type,
            metadata.get("title") or "",
            metadata.get("original_title") or "",
            metadata.get("year") or 0,
            json_dumps(clean_list(metadata.get("genres"))),
            metadata.get("rating") or 0.0,
            metadata.get("plot") or "",
            metadata.get("poster") or "",
            metadata.get("fanart") or metadata.get("poster") or "",
            metadata.get("imdb_id"),
            metadata.get("csfd_id"),
            metadata.get("search_query") or metadata.get("title") or "",
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
        "SELECT 1 FROM streams WHERE media_id=? AND provider=? AND ident=?",
        (media_id, provider, ident),
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
            , stream_url
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', ?, ?, ?, ?)
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
            stream.get("stream_url") or "",
        ),
    )


def refresh_stream_grouping(conn, media_id):
    rows = conn.execute(
        "SELECT id, filename, width, height, format FROM streams WHERE media_id=?",
        (media_id,),
    ).fetchall()
    for row in rows:
        stream = dict(row)
        info = parse_stream_info(stream.get("filename") or "")
        conn.execute(
            """
            UPDATE streams
            SET season=?, episode=?, format=?, width=?, height=?
            WHERE id=?
            """,
            (
                info["season"],
                info["episode"],
                stream.get("format") or info["format"],
                stream.get("width") or info["width"],
                stream.get("height") or info["height"],
                stream["id"],
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
        "stream_url": s.get("stream_url") or "",
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
        "search_query": media.get("search_query") or media.get("title") or "",
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
    ensure_search_sources()
    metadata = metadata_for_query(query)
    metadata["search_query"] = query
    streams = search_provider_streams(query, metadata.get("type") or "movie")
    metadata["type"] = infer_media_type(streams, metadata)
    conn = get_db_connection()
    try:
        media_id = upsert_media(conn, metadata, streams)
        conn.commit()
        return [media_id]
    finally:
        conn.close()


def html_escape(value):
    return (
        str(value or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#039;")
    )


def format_size(size):
    size = float(size or 0)
    if not size:
        return "-"
    units = ["B", "KB", "MB", "GB", "TB"]
    index = 0
    while size >= 1024 and index < len(units) - 1:
        size /= 1024
        index += 1
    return f"{size:.1f} {units[index]}" if index else f"{int(size)} {units[index]}"


def provider_badge(provider):
    cls = "badge-ws" if provider == "webshare" else "badge-fs"
    return f'<span class="provider-badge {cls}">{html_escape(provider)}</span>'


def stream_table(streams):
    if not streams:
        return '<div class="empty-list">Nebyly nalezeny žádné streamy.</div>'

    rows = []
    for index, stream in enumerate(streams):
        stream_json = html_escape(json.dumps(stream, ensure_ascii=False))
        rows.append(
            f"""
            <tr>
                <td><input type="checkbox" name="stream" value="{index}"><input type="hidden" id="stream-{index}" value="{stream_json}"></td>
                <td>{provider_badge(stream.get("provider"))}</td>
                <td><strong>{html_escape(stream.get("filename"))}</strong></td>
                <td>{html_escape(stream.get("format") or "-")}</td>
                <td>{format_size(stream.get("size"))}</td>
                <td>{stream.get("width") or "-"}x{stream.get("height") or "-"}</td>
            </tr>
            """
        )
    return f"""
    <table class="stream-grid">
        <thead><tr><th></th><th>Zdroj</th><th>Název</th><th>Formát</th><th>Velikost</th><th>Rozlišení</th></tr></thead>
        <tbody>{"".join(rows)}</tbody>
    </table>
    """


def grouped_streams_html(streams):
    grouped = group_episodes(streams)
    if not grouped:
        return stream_table(streams)

    html = ['<div class="seasons">']
    loose = [s for s in streams if s.get("season") is None or s.get("episode") is None]
    for season in grouped:
        html.append(f'<details open><summary>Série {season["season"]}</summary>')
        for episode in season["episodes"]:
            html.append(f'<div class="episode-block"><h4>Díl {episode["episode"]}</h4>')
            html.append(stream_table(episode["streams"]))
            html.append("</div>")
        html.append("</details>")
    if loose:
        html.append("<h3>Nezařazené streamy</h3>")
        html.append(stream_table(loose))
    html.append("</div>")
    return "".join(html)


def render_search_page(result):
    metadata = result["metadata"]
    streams = result["streams"]
    metadata_json = html_escape(json.dumps(metadata, ensure_ascii=False))
    media_type = metadata.get("type") or "movie"
    rows_html = grouped_streams_html(streams) if media_type == "tvshow" else stream_table(streams)
    poster = metadata.get("poster") or ""
    poster_html = f'<img src="{html_escape(poster)}" alt="">' if poster else ""
    return f"""
    <!DOCTYPE html>
    <html lang="cs">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Stream Cinema - výsledky</title>
        <link rel="stylesheet" href="../static/style.css?v=0.3.17">
    </head>
    <body>
        <div class="app-shell">
            <header class="topbar">
                <div>
                    <h1>Stream Cinema</h1>
                    <p>Výsledky hledání</p>
                </div>
                <form class="search-box" action="search" method="get">
                    <input type="text" name="q" value="{html_escape(metadata.get("title"))}" placeholder="Hledat film nebo seriál">
                    <select name="media_type">
                        <option value="movie" {"selected" if media_type == "movie" else ""}>Film</option>
                        <option value="tvshow" {"selected" if media_type == "tvshow" else ""}>Seriál</option>
                    </select>
                    <button type="submit">Hledat</button>
                </form>
            </header>
            <section class="search-panel">
                <div class="search-header">
                    <div class="poster-small">{poster_html}</div>
                    <div>
                        <h2>{html_escape(metadata.get("title"))}</h2>
                        <p>{metadata.get("year") or "-"} · {"Seriál" if metadata.get("type") == "tvshow" else "Film"} · {metadata.get("rating") or 0}% · {html_escape(str(metadata.get("source") or "").upper())}</p>
                        <p>{html_escape(metadata.get("plot") or "Bez popisu.")}</p>
                    </div>
                </div>
                <div id="status" class="status hidden"></div>
                <div class="stream-actions">
                    <label><input type="checkbox" id="selectAllStreams"> Vybrat vše</label>
                    <button type="button" id="saveButton">Zařadit vybrané do sbírky</button>
                    <input type="text" id="moreQuery" placeholder="Hledat další streamy">
                    <button type="button" id="moreButton">Hledat další</button>
                    <a class="button-link" href="../">Zpět do katalogu</a>
                </div>
                <input type="hidden" id="metadataJson" value="{metadata_json}">
                <div class="stream-table">{rows_html}</div>
                <h3>Doplněné streamy</h3>
                <table class="stream-grid">
                    <thead><tr><th></th><th>Zdroj</th><th>Název</th><th>Formát</th><th>Velikost</th><th>Rozlišení</th></tr></thead>
                    <tbody id="extraRows"></tbody>
                </table>
            </section>
        </div>
        <script>
        (function () {{
            var nextIndex = {len(streams)};
            function status(message, type) {{
                var node = document.getElementById("status");
                node.textContent = message || "";
                node.className = message ? "status " + (type || "info") : "status hidden";
            }}
            function esc(value) {{
                return String(value || "").replace(/[&<>"']/g, function (ch) {{
                    return {{ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;" }}[ch];
                }});
            }}
            function size(bytes) {{
                bytes = Number(bytes || 0);
                if (!bytes) return "-";
                var units = ["B", "KB", "MB", "GB", "TB"];
                var index = 0;
                while (bytes >= 1024 && index < units.length - 1) {{
                    bytes = bytes / 1024;
                    index += 1;
                }}
                return (index ? bytes.toFixed(1) : String(Math.round(bytes))) + " " + units[index];
            }}
            function appendStream(stream) {{
                var row = document.createElement("tr");
                var index = nextIndex++;
                var providerClass = stream.provider === "webshare" ? "badge-ws" : "badge-fs";
                row.innerHTML =
                    '<td><input type="checkbox" name="stream" value="' + index + '"><input type="hidden" id="stream-' + index + '"></td>' +
                    '<td><span class="provider-badge ' + providerClass + '">' + esc(stream.provider) + '</span></td>' +
                    '<td><strong>' + esc(stream.filename) + '</strong></td>' +
                    '<td>' + esc(stream.format || "-") + '</td>' +
                    '<td>' + size(stream.size) + '</td>' +
                    '<td>' + (stream.width || "-") + 'x' + (stream.height || "-") + '</td>';
                document.getElementById("extraRows").appendChild(row);
                document.getElementById("stream-" + index).value = JSON.stringify(stream);
            }}
            document.getElementById("selectAllStreams").addEventListener("change", function () {{
                var checks = document.querySelectorAll("input[name='stream']");
                for (var i = 0; i < checks.length; i += 1) checks[i].checked = this.checked;
            }});
            document.getElementById("saveButton").addEventListener("click", function () {{
                var checks = document.querySelectorAll("input[name='stream']:checked");
                var streams = [];
                for (var i = 0; i < checks.length; i += 1) {{
                    streams.push(JSON.parse(document.getElementById("stream-" + checks[i].value).value));
                }}
                if (!streams.length) {{
                    status("Vyber alespoň jeden stream.", "error");
                    return;
                }}
                status("Ukládám vybrané streamy...", "info");
                fetch("media", {{
                    method: "POST",
                    headers: {{ "Content-Type": "application/json" }},
                    body: JSON.stringify({{ metadata: JSON.parse(document.getElementById("metadataJson").value), streams: streams }})
                }}).then(function (response) {{
                    if (response.status === 404) {{
                        return fetch("/api/media", {{
                            method: "POST",
                            headers: {{ "Content-Type": "application/json" }},
                            body: JSON.stringify({{ metadata: JSON.parse(document.getElementById("metadataJson").value), streams: streams }})
                        }});
                    }}
                    return response;
                }}).then(function (response) {{
                    if (!response.ok) throw new Error("HTTP " + response.status);
                    return response.json();
                }}).then(function () {{
                    status("Vybrané streamy byly zařazeny do sbírky.", "success");
                }}).catch(function () {{
                    status("Uložení selhalo. Zkontroluj log add-onu.", "error");
                }});
            }});
            document.getElementById("moreButton").addEventListener("click", function () {{
                var value = document.getElementById("moreQuery").value;
                if (!value) return;
                status("Hledám další streamy...", "info");
                fetch("search_json?q=" + encodeURIComponent(value) + "&media_type={media_type}")
                    .then(function (response) {{
                        if (!response.ok) throw new Error("HTTP " + response.status);
                        return response.json();
                    }})
                    .then(function (data) {{
                        var streams = data.streams || [];
                        for (var i = 0; i < streams.length; i += 1) appendStream(streams[i]);
                        status("Doplněno streamů: " + streams.length + ".", "success");
                    }})
                    .catch(function () {{
                        status("Doplnění streamů selhalo.", "error");
                    }});
            }});
        }}());
        </script>
    </body>
    </html>
    """


@app.get("/")
async def read_index():
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/api/ping")
def ping():
    return {"status": "ok", "message": "pong"}


@app.get("/api/source_status")
def source_status():
    sources = [name for name, _scraper in enabled_sources()]
    return {
        "enabled_sources": sources,
        "can_search": bool(sources),
        "message": "" if sources else "Nelze vyhledávat, dokud není v konfiguraci zadáno přihlášení alespoň k jednomu zdroji.",
    }


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


def run_search_preview(q: str, media_type: str = "movie"):
    query = (q or "").strip()
    if not query:
        return {"metadata": None, "streams": []}

    ensure_search_sources()
    media_type = media_type if media_type in ("movie", "tvshow") else "movie"
    metadata = metadata_for_query(query, media_type=media_type)
    metadata["search_query"] = query
    streams = search_provider_streams(query, media_type)
    metadata["type"] = media_type
    return {
        "metadata": metadata,
        "streams": streams,
        "totalCount": len(streams),
        "enabled_sources": [name for name, _scraper in enabled_sources()],
    }


@app.get("/api/search_json")
def search_preview_json(q: str, media_type: str = "movie"):
    return run_search_preview(q, media_type)


@app.get("/api/search", response_class=HTMLResponse)
def search_preview_page(q: str, media_type: str = "movie"):
    return HTMLResponse(render_search_page(run_search_preview(q, media_type)))


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


@app.put("/api/media/{media_id}")
def update_media(media_id: str, payload: dict = Body(...)):
    conn = get_db_connection()
    try:
        row = conn.execute("SELECT * FROM media WHERE id=?", (media_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Media not found")

        current = dict(row)
        media_type = payload.get("type") or current.get("type") or "movie"
        if media_type not in ("movie", "tvshow"):
            raise HTTPException(status_code=400, detail="Invalid media type")

        plot = payload.get("plot")
        poster = payload.get("poster")
        title = payload.get("title")
        fanart = payload.get("fanart")
        rating = payload.get("rating")
        genres = clean_list(payload.get("genres")) if "genres" in payload else safe_json_loads(current.get("genres"), [])
        search_query = payload.get("search_query")
        try:
            rating = max(0.0, min(100.0, float(rating))) if rating is not None else current.get("rating") or 0.0
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="Invalid rating")

        conn.execute(
            """
            UPDATE media
            SET type=?, title=?, genres=?, rating=?, plot=?, poster=?, fanart=?, search_query=?
            WHERE id=?
            """,
            (
                media_type,
                title if title is not None else current.get("title") or "",
                json_dumps(genres),
                rating,
                plot if plot is not None else current.get("plot") or "",
                poster if poster is not None else current.get("poster") or "",
                fanart if fanart is not None else (poster if poster is not None else current.get("fanart") or current.get("poster") or ""),
                search_query if search_query is not None else current.get("search_query") or current.get("title") or "",
                media_id,
            ),
        )
        refresh_stream_grouping(conn, media_id)
        conn.commit()
        row = conn.execute("SELECT * FROM media WHERE id=?", (media_id,)).fetchone()
        return serialize_media_row(conn, row, include_streams=True)
    finally:
        conn.close()


@app.delete("/api/media/{media_id}")
def delete_media(media_id: str):
    conn = get_db_connection()
    try:
        row = conn.execute("SELECT 1 FROM media WHERE id=?", (media_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Media not found")
        conn.execute("DELETE FROM streams WHERE media_id=?", (media_id,))
        conn.execute("DELETE FROM media WHERE id=?", (media_id,))
        conn.commit()
        return {"status": "ok"}
    finally:
        conn.close()


@app.post("/api/media/{media_id}/streams")
def add_media_streams(media_id: str, payload: dict = Body(...)):
    streams = payload.get("streams") or []
    conn = get_db_connection()
    try:
        row = conn.execute("SELECT * FROM media WHERE id=?", (media_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Media not found")

        before = conn.execute(
            "SELECT COUNT(*) FROM streams WHERE media_id=?",
            (media_id,),
        ).fetchone()[0]
        for stream in streams:
            add_stream(conn, media_id, stream)
        refresh_stream_grouping(conn, media_id)
        after = conn.execute(
            "SELECT COUNT(*) FROM streams WHERE media_id=?",
            (media_id,),
        ).fetchone()[0]
        conn.commit()
        row = conn.execute("SELECT * FROM media WHERE id=?", (media_id,)).fetchone()
        return {
            "status": "ok",
            "added": max(0, after - before),
            "media": serialize_media_row(conn, row, include_streams=True),
        }
    finally:
        conn.close()


@app.post("/api/media/{media_id}/refresh")
def refresh_media_streams(media_id: str):
    ensure_search_sources()
    conn = get_db_connection()
    try:
        row = conn.execute("SELECT * FROM media WHERE id=?", (media_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Media not found")

        media = dict(row)
        query = (media.get("search_query") or media.get("title") or "").strip()
        if not query:
            raise HTTPException(status_code=400, detail="Media has no stored search query")

        found_streams = search_provider_streams(query, media.get("type") or "movie")
        found_keys = {
            (stream.get("provider"), str(stream.get("ident")))
            for stream in found_streams
            if stream.get("provider") and stream.get("ident")
        }

        existing_rows = conn.execute(
            "SELECT * FROM streams WHERE media_id=?",
            (media_id,),
        ).fetchall()
        existing_keys = {
            (row["provider"], str(row["ident"])): row
            for row in existing_rows
        }

        removed = 0
        kept = 0
        now = datetime.utcnow().isoformat(timespec="seconds")
        for key, stream_row in existing_keys.items():
            if key in found_keys:
                kept += 1
                conn.execute(
                    "UPDATE streams SET status='active', last_checked_at=? WHERE id=?",
                    (now, stream_row["id"]),
                )
            else:
                removed += 1
                conn.execute("DELETE FROM streams WHERE id=?", (stream_row["id"],))

        new_streams = [
            stream for stream in found_streams
            if (stream.get("provider"), str(stream.get("ident"))) not in existing_keys
        ]

        refresh_stream_grouping(conn, media_id)
        conn.commit()
        row = conn.execute("SELECT * FROM media WHERE id=?", (media_id,)).fetchone()
        return {
            "status": "ok",
            "query": query,
            "kept": kept,
            "removed": removed,
            "new_streams": new_streams,
            "media": serialize_media_row(conn, row, include_streams=True),
        }
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


@app.post("/api/media/{media_id}/streams/delete_selected")
def delete_selected_streams(media_id: str, payload: dict = Body(...)):
    stream_ids = []
    for value in payload.get("stream_ids") or []:
        try:
            stream_ids.append(int(value))
        except (TypeError, ValueError):
            continue

    if not stream_ids:
        return {"status": "ok", "deleted": 0}

    placeholders = ",".join("?" for _ in stream_ids)
    conn = get_db_connection()
    try:
        cursor = conn.execute(
            f"DELETE FROM streams WHERE media_id=? AND id IN ({placeholders})",
            [media_id] + stream_ids,
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
        ident = unquote(ident or "")
        provider, file_id = ident.split(":", 1)
        if provider == "webshare":
            link = f"api/stream_proxy/{provider}:{file_id}"
        elif provider == "fastshare":
            link = f"api/stream_proxy/{provider}:{file_id}"
        else:
            link = None
        return {"link": link}
    except Exception as exc:
        print(f"Link error: {exc}")
        return {"link": None}


def stored_stream_url(provider, file_id):
    conn = get_db_connection()
    try:
        row = conn.execute(
            "SELECT stream_url FROM streams WHERE provider=? AND ident=? AND stream_url<>'' ORDER BY id DESC LIMIT 1",
            (provider, file_id),
        ).fetchone()
        return row["stream_url"] if row else ""
    finally:
        conn.close()


def is_fastshare_url(url):
    parsed = urlparse(url or "")
    return parsed.scheme in ("http", "https") and (
        parsed.netloc.endswith("fastshare.cloud") or parsed.netloc.endswith("fastshare.cz")
    )


def is_webshare_url(url):
    parsed = urlparse(url or "")
    return parsed.scheme in ("http", "https") and parsed.netloc.endswith("webshare.cz")


@app.get("/api/stream_proxy/{ident:path}")
def stream_proxy(ident: str, request: Request, url: str = ""):
    try:
        ident = unquote(ident or "")
        provider, file_id = ident.split(":", 1)
        if provider not in ("fastshare", "webshare"):
            raise HTTPException(status_code=404, detail="Unsupported provider")

        if provider == "fastshare" and not FS.logged_in:
            FS.login()
        if provider == "webshare" and not WS.token:
            WS.ensure_token()

        if provider == "fastshare":
            source_url = url if is_fastshare_url(url) else ""
            source_url = source_url or stored_stream_url(provider, file_id) or FS.get_link(file_id)
            headers = dict(FS.stream_headers())
        else:
            source_url = url if is_webshare_url(url) else ""
            source_url = source_url or WS.get_link(file_id)
            headers = dict(WS.stream_headers())

        if not source_url or "/free/" in source_url:
            raise HTTPException(status_code=404, detail="Stream link unavailable")

        range_header = request.headers.get("range")
        if range_header:
            headers["Range"] = range_header

        upstream = requests.get(source_url, headers=headers, stream=True, timeout=15)
        upstream.raise_for_status()

        response_headers = {}
        for header in ("content-type", "content-length", "content-range", "accept-ranges"):
            value = upstream.headers.get(header)
            if value:
                response_headers[header] = value

        return StreamingResponse(
            upstream.iter_content(chunk_size=1024 * 512),
            status_code=upstream.status_code,
            headers=response_headers,
            media_type=upstream.headers.get("content-type") or "application/octet-stream",
        )
    except HTTPException:
        raise
    except Exception as exc:
        print(f"Stream proxy error: {exc}")
        raise HTTPException(status_code=502, detail="Stream proxy failed")
