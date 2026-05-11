import re
import unicodedata
from urllib.parse import quote
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


class CSFDScraper:
    BASE_URL = "https://www.csfd.cz"
    CZDB_URL = "https://api.czdb.cz/search"
    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "cs-CZ,cs;q=0.9,sk;q=0.8,en;q=0.6",
    }

    def __init__(self, api_base_url=None):
        self.api_base_url = (api_base_url or "").rstrip("/")
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)

    def search_movie(self, query, media_type=None):
        api_result = self._search_api(query, media_type)
        if api_result:
            return api_result

        czdb_result = self._search_czdb(query, media_type)
        if czdb_result:
            return czdb_result

        try:
            response = self.session.get(
                f"{self.BASE_URL}/hledat/",
                params={"q": query},
                timeout=10,
            )
            response.raise_for_status()
            if self._is_bot_challenge(response.text):
                print("CSFD Search Error: bot protection page returned")
                return None

            soup = BeautifulSoup(response.content, "lxml")
            link = self._best_search_link(soup, media_type)
            if not link or not link.get("href"):
                return None

            match = re.search(r"/film/(\d+)", link["href"])
            if not match:
                return None

            return self.get_movie_details(match.group(1), media_type=media_type)
        except Exception as exc:
            print(f"CSFD Search Error: {exc}")
            return None

    def get_movie_details(self, csfd_id, media_type=None):
        api_result = self._movie_api(csfd_id, media_type=media_type)
        if api_result:
            return api_result

        czdb_result = self._movie_czdb(csfd_id, media_type=media_type)
        if czdb_result:
            return czdb_result

        try:
            response = self.session.get(
                f"{self.BASE_URL}/film/{csfd_id}/prehled/",
                timeout=10,
            )
            response.raise_for_status()
            if self._is_bot_challenge(response.text):
                print("CSFD Detail Error: bot protection page returned")
                return None

            soup = BeautifulSoup(response.content, "lxml")
            title = self._title(soup)
            poster = self._poster(soup)
            return {
                "csfd_id": str(csfd_id),
                "title": title,
                "year": self._year(soup),
                "rating": self._rating(soup),
                "poster": poster,
                "fanart": poster,
                "plot": self._plot(soup),
                "genres": self._genres(soup),
                "type": media_type or self._media_type(soup),
            }
        except Exception as exc:
            print(f"CSFD Detail Error: {exc}")
            return None

    def _search_api(self, query, media_type=None):
        if not self.api_base_url:
            return None
        try:
            response = self.session.get(
                f"{self.api_base_url}/search/{quote(query)}",
                timeout=12,
            )
            response.raise_for_status()
            candidate = self._best_api_search_result(response.json(), media_type)
            if not candidate:
                return None
            csfd_id = candidate.get("id") or candidate.get("csfd_id")
            if csfd_id:
                details = self._movie_api(csfd_id, media_type=media_type)
                if details:
                    return details
            return self._normalize_api_movie(candidate, media_type)
        except Exception as exc:
            print(f"CSFD API Search Error: {exc}")
            return None

    def _movie_api(self, csfd_id, media_type=None):
        if not self.api_base_url:
            return None
        try:
            response = self.session.get(f"{self.api_base_url}/movie/{csfd_id}", timeout=12)
            response.raise_for_status()
            return self._normalize_api_movie(response.json(), media_type)
        except Exception as exc:
            print(f"CSFD API Detail Error: {exc}")
            return None

    def _search_czdb(self, query, media_type=None):
        try:
            response = self.session.get(self.CZDB_URL, params={"q": query}, timeout=12)
            response.raise_for_status()
            candidate = self._best_czdb_search_result(response.json(), query, media_type)
            if not candidate:
                return None
            csfd_id = candidate.get("csfd_id")
            if csfd_id:
                details = self._movie_czdb(csfd_id, media_type=media_type)
                if details:
                    return details
            return self._normalize_czdb_movie(candidate, media_type)
        except Exception as exc:
            print(f"CSFD CZDB Search Error: {exc}")
            return None

    def _movie_czdb(self, csfd_id, media_type=None):
        try:
            response = self.session.get(self.CZDB_URL, params={"uid": csfd_id}, timeout=12)
            response.raise_for_status()
            results = self._czdb_results(response.json())
            return self._normalize_czdb_movie(results[0], media_type) if results else None
        except Exception as exc:
            print(f"CSFD CZDB Detail Error: {exc}")
            return None

    def _czdb_results(self, data):
        if isinstance(data, dict):
            results = data.get("results") or []
            return results if isinstance(results, list) else []
        if isinstance(data, list):
            return data
        return []

    def _best_czdb_search_result(self, data, query, media_type=None):
        candidates = [item for item in self._czdb_results(data) if isinstance(item, dict)]
        if not candidates:
            return None

        normalized_query = self._normalize_match_text(query)
        query_terms = [
            self._normalize_match_text(term)
            for term in re.split(r"\s+", str(query or "").strip())
            if self._normalize_match_text(term)
        ]

        def score(item):
            weighted_names = [
                (str(item.get("nazev") or ""), 140),
                (str(item.get("original") or ""), 120),
                (str(item.get("alt_nazev") or ""), 70),
            ]
            value = 0
            for name, weight in weighted_names:
                if not name or name == "@":
                    continue
                normalized_name = self._normalize_match_text(name)
                if normalized_name == normalized_query:
                    value = max(value, weight)
                elif normalized_name.startswith(normalized_query):
                    value = max(value, weight - 40)
                elif query_terms and all(term in normalized_name for term in query_terms):
                    value = max(value, weight - 70)
            if media_type == "tvshow" and self._looks_like_series(item):
                value += 15
            if media_type == "movie" and not self._looks_like_series(item):
                value += 10
            return value

        def tie_breaker(item):
            year = self._safe_int(item.get("rok"))
            return -year if media_type == "movie" and len(query_terms) > 1 else 0

        best = max(
            enumerate(candidates),
            key=lambda pair: (score(pair[1]), tie_breaker(pair[1]), -pair[0]),
        )[1]
        return best if score(best) > 0 else candidates[0]

    def _normalize_czdb_movie(self, data, media_type=None):
        if not isinstance(data, dict):
            return None

        title = self._clean_czdb_value(data.get("nazev"))
        original_title = self._clean_czdb_value(data.get("original"))
        if not title:
            return None

        poster = self._clean_czdb_value(data.get("obrazek_url")) or self._clean_czdb_value(data.get("imgo"))
        fanart = self._clean_czdb_value(data.get("backgrop")) or poster
        genres = [
            genre.strip()
            for genre in str(data.get("zanr") or "").split(",")
            if genre.strip() and genre.strip() != "N/A"
        ]

        rating = 0.0
        match = re.search(r"(\d+(?:[.,]\d+)?)", str(data.get("hodnoceni") or ""))
        if match:
            rating = float(match.group(1).replace(",", "."))

        return {
            "csfd_id": str(data.get("csfd_id")) if data.get("csfd_id") else None,
            "imdb_id": self._clean_czdb_value(data.get("imdb_id")),
            "title": title,
            "original_title": original_title,
            "year": self._safe_int(data.get("rok")),
            "rating": rating,
            "poster": poster,
            "fanart": fanart,
            "plot": self._clean_czdb_value(data.get("plot")),
            "genres": genres,
            "type": media_type or ("tvshow" if self._looks_like_series(data) else "movie"),
        }

    def _clean_czdb_value(self, value):
        text = str(value or "").strip()
        return "" if text in ("", "@", "0", "N/A", "None") else text

    def _looks_like_series(self, item):
        text = " ".join(
            str(item.get(key) or "")
            for key in ("typ", "nazev", "original", "alt_nazev")
        ).lower()
        return "seri" in text or "series" in text or "tv" in text

    def _normalize_match_text(self, value):
        text = unicodedata.normalize("NFKD", str(value or "").lower())
        text = "".join(ch for ch in text if not unicodedata.combining(ch))
        return re.sub(r"[^a-z0-9]+", "", text)

    def _best_api_search_result(self, data, media_type=None):
        if isinstance(data, list):
            candidates = data
        elif isinstance(data, dict):
            candidates = []
            preferred = ["tvSeries", "series"] if media_type == "tvshow" else ["movies", "films"]
            for key in preferred + ["movies", "films", "tvSeries", "series"]:
                value = data.get(key)
                if isinstance(value, list):
                    candidates.extend(value)
        else:
            candidates = []

        if not candidates:
            return None

        for item in candidates:
            item_type = str(item.get("type") or "").lower()
            if media_type == "tvshow" and ("seri" in item_type or "tv" in item_type):
                return item
            if media_type == "movie" and not ("seri" in item_type or "epiz" in item_type):
                return item
        return candidates[0]

    def _normalize_api_movie(self, data, media_type=None):
        if not isinstance(data, dict):
            return None
        title = data.get("title") or data.get("name") or ""
        if not title:
            return None

        descriptions = data.get("descriptions") or []
        plot = data.get("plot") or data.get("description") or ""
        if not plot and descriptions:
            plot = descriptions[0]

        poster = data.get("poster") or data.get("photo") or ""
        if poster.startswith("//"):
            poster = "https:" + poster
        fanart = data.get("photo") or poster
        if fanart.startswith("//"):
            fanart = "https:" + fanart

        item_type = str(data.get("type") or "").lower()
        normalized_type = media_type or ("tvshow" if "seri" in item_type or "tv" in item_type else "movie")
        csfd_id = data.get("id") or data.get("csfd_id")
        return {
            "csfd_id": str(csfd_id) if csfd_id else None,
            "title": title,
            "year": self._safe_int(data.get("year")),
            "rating": float(data.get("rating") or 0),
            "poster": poster,
            "fanart": fanart,
            "plot": plot,
            "genres": data.get("genres") or [],
            "type": normalized_type,
        }

    def _best_search_link(self, soup, media_type=None):
        selectors = []
        if media_type == "tvshow":
            selectors.extend(
                [
                    "#tabs-search-series a.film-title-name",
                    ".search-series a.film-title-name",
                    "a[href*='/film/'][href*='serial']",
                ]
            )
        selectors.extend(
            [
                "#tabs-search-films a.film-title-name",
                ".search-films a.film-title-name",
                "a.film-title-name",
            ]
        )
        for selector in selectors:
            link = soup.select_one(selector)
            if link and link.get("href"):
                return link
        return soup.find("a", href=re.compile(r"/film/\d+"))

    def _title(self, soup):
        node = soup.select_one("h1")
        if node:
            return re.sub(r"\s+", " ", node.get_text(" ", strip=True)).split("(")[0].strip()
        meta = soup.select_one("meta[property='og:title']")
        return meta.get("content", "").strip() if meta else ""

    def _is_bot_challenge(self, text):
        lower = text.lower()
        return "making sure you're not a bot" in lower or "cf-challenge" in lower

    def _year(self, soup):
        for text in soup.stripped_strings:
            match = re.search(r"\b(19\d{2}|20\d{2})\b", text)
            if match:
                return int(match.group(1))
        return 0

    def _rating(self, soup):
        node = soup.select_one(".film-rating-average")
        text = node.get_text(" ", strip=True) if node else soup.get_text(" ", strip=True)
        match = re.search(r"(\d{1,3})\s*%", text)
        return float(match.group(1)) if match else 0.0

    def _poster(self, soup):
        meta = soup.select_one("meta[property='og:image']")
        if meta and meta.get("content"):
            return urljoin(self.BASE_URL, meta["content"])

        node = soup.select_one(".film-poster img, img.film-poster")
        if node and node.get("src"):
            return urljoin(self.BASE_URL, node["src"])

        return ""

    def _plot(self, soup):
        node = soup.select_one(".plot-full p, .plot-preview p, .plots-full p")
        if node:
            return node.get_text(" ", strip=True)

        text = soup.get_text("\n", strip=True)
        match = re.search(
            r"Obsahy\(\d+\)\s*(?:zobrazit (?:vsechny|všechny) obsahy)?\s*(.+?)(?:\n\s*\*|\n\s*Videa|\n\s*Recenze)",
            text,
            re.I | re.S,
        )
        return re.sub(r"\s+", " ", match.group(1)).strip() if match else ""

    def _genres(self, soup):
        genres = [
            node.get_text(" ", strip=True)
            for node in soup.select(".genres a, a[href*='/zanr']")
            if node.get_text(" ", strip=True)
        ]
        if genres:
            return list(dict.fromkeys(genres))

        text = soup.get_text("\n", strip=True)
        known = [
            "Akční",
            "Animovaný",
            "Drama",
            "Fantasy",
            "Horor",
            "Komedie",
            "Krimi",
            "Romantický",
            "Sci-Fi",
            "Thriller",
        ]
        return [genre for genre in known if re.search(rf"\b{re.escape(genre)}\b", text, re.I)]

    def _media_type(self, soup):
        text = soup.get_text(" ", strip=True).lower()
        return "tvshow" if "seriál" in text else "movie"

    def _safe_int(self, value):
        try:
            return int(value or 0)
        except (TypeError, ValueError):
            return 0
