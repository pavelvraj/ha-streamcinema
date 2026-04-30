import json
import re
from urllib.parse import quote
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


class IMDBScraper:
    BASE_URL = "https://www.imdb.com"
    HEADERS = {
        "Accept-Language": "cs-CZ,cs;q=0.9,en-US;q=0.8,en;q=0.7",
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
        ),
    }

    def search_movie(self, query, media_type=None):
        try:
            suggestion = self._search_suggestion(query, media_type)
            if suggestion:
                details = self.get_movie_details(suggestion["imdb_id"])
                if details:
                    return details
                return suggestion

            response = requests.get(
                f"{self.BASE_URL}/find/",
                params={"q": query, "s": "tt"},
                headers=self.HEADERS,
                timeout=10,
            )
            response.raise_for_status()
            soup = BeautifulSoup(response.content, "lxml")

            link = soup.select_one("a[href*='/title/tt']")
            if not link or not link.get("href"):
                return None

            match = re.search(r"/title/(tt\d+)", link["href"])
            if not match:
                return None

            return self.get_movie_details(match.group(1))
        except Exception as exc:
            print(f"IMDB Search Error: {exc}")
            return None

    def _search_suggestion(self, query, media_type=None):
        clean = re.sub(r"\s+", "_", query.strip().lower())
        if not clean:
            return None

        url = f"https://v3.sg.media-imdb.com/suggestion/{quote(clean[0])}/{quote(clean)}.json"
        try:
            response = requests.get(url, headers=self.HEADERS, timeout=10)
            response.raise_for_status()
            data = response.json()
        except Exception as exc:
            print(f"IMDB Suggestion Error: {exc}")
            return None

        wanted = "TV series" if media_type == "tvshow" else "feature"
        fallback = None
        for item in data.get("d", []):
            imdb_id = item.get("id")
            title = item.get("l")
            if not imdb_id or not title or not imdb_id.startswith("tt"):
                continue

            item_type = item.get("q") or ""
            candidate = {
                "source": "imdb",
                "imdb_id": imdb_id,
                "csfd_id": None,
                "title": title,
                "year": item.get("y") or 0,
                "rating": 0.0,
                "poster": item.get("i", {}).get("imageUrl", "") if isinstance(item.get("i"), dict) else "",
                "plot": item_type,
                "genres": [],
                "type": "tvshow" if "TV" in item_type else "movie",
            }

            if media_type and candidate["type"] == media_type:
                return candidate
            if not media_type and wanted in item_type:
                return candidate
            if fallback is None:
                fallback = candidate

        return fallback

    def get_movie_details(self, imdb_id):
        try:
            response = requests.get(
                f"{self.BASE_URL}/title/{imdb_id}/",
                headers=self.HEADERS,
                timeout=10,
            )
            response.raise_for_status()
            soup = BeautifulSoup(response.content, "lxml")
            data = self._json_ld(soup)

            title = data.get("name") or self._text(soup.select_one("h1"))
            year = self._year(data, soup)
            rating = self._rating(data, soup)
            poster = data.get("image") or ""
            plot = data.get("description") or ""
            genres = data.get("genre") or []
            if isinstance(genres, str):
                genres = [genres]
            media_type = self._media_type(data)

            return {
                "source": "imdb",
                "imdb_id": imdb_id,
                "csfd_id": None,
                "title": title,
                "year": year,
                "rating": rating,
                "poster": poster,
                "plot": plot,
                "genres": genres,
                "type": media_type,
            }
        except Exception as exc:
            print(f"IMDB Detail Error: {exc}")
            return None

    def _json_ld(self, soup):
        for node in soup.select("script[type='application/ld+json']"):
            try:
                return json.loads(node.string or "{}")
            except json.JSONDecodeError:
                continue
        return {}

    def _year(self, data, soup):
        date = data.get("datePublished") or ""
        match = re.search(r"\b(19\d{2}|20\d{2})\b", date)
        if match:
            return int(match.group(1))

        text = soup.get_text(" ", strip=True)
        match = re.search(r"\b(19\d{2}|20\d{2})\b", text)
        return int(match.group(1)) if match else 0

    def _rating(self, data, soup):
        rating = data.get("aggregateRating", {}).get("ratingValue")
        if rating is None:
            text = soup.get_text(" ", strip=True)
            match = re.search(r"(\d+(?:\.\d+)?)\s*/\s*10", text)
            rating = match.group(1) if match else None
        try:
            return round(float(rating) * 10, 1)
        except (TypeError, ValueError):
            return 0.0

    def _media_type(self, data):
        value = data.get("@type")
        values = value if isinstance(value, list) else [value]
        return "tvshow" if "TVSeries" in values else "movie"

    def _text(self, node):
        return node.get_text(" ", strip=True) if node else ""
