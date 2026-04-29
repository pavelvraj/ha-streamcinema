import re
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


class CSFDScraper:
    BASE_URL = "https://www.csfd.cz"
    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
        )
    }

    def search_movie(self, query):
        try:
            response = requests.get(
                f"{self.BASE_URL}/hledat/",
                params={"q": query},
                headers=self.HEADERS,
                timeout=10,
            )
            response.raise_for_status()
            if self._is_bot_challenge(response.text):
                print("CSFD Search Error: bot protection page returned")
                return None
            soup = BeautifulSoup(response.content, "lxml")

            link = soup.select_one("a.film-title-name")
            if not link:
                link = soup.find("a", href=re.compile(r"/film/\d+"))
            if not link or not link.get("href"):
                return None

            match = re.search(r"/film/(\d+)", link["href"])
            if not match:
                return None

            return self.get_movie_details(match.group(1))
        except Exception as exc:
            print(f"CSFD Search Error: {exc}")
            return None

    def get_movie_details(self, csfd_id):
        try:
            response = requests.get(
                f"{self.BASE_URL}/film/{csfd_id}/prehled/",
                headers=self.HEADERS,
                timeout=10,
            )
            response.raise_for_status()
            if self._is_bot_challenge(response.text):
                print("CSFD Detail Error: bot protection page returned")
                return None
            soup = BeautifulSoup(response.content, "lxml")

            title = self._title(soup)
            year = self._year(soup)
            rating = self._rating(soup)
            poster = self._poster(soup)
            plot = self._plot(soup)
            genres = self._genres(soup)

            return {
                "csfd_id": csfd_id,
                "title": title,
                "year": year,
                "rating": rating,
                "poster": poster,
                "plot": plot,
                "genres": genres,
            }
        except Exception as exc:
            print(f"CSFD Detail Error: {exc}")
            return None

    def _title(self, soup):
        node = soup.select_one("h1")
        if not node:
            meta = soup.select_one("meta[property='og:title']")
            return meta.get("content", "").strip() if meta else ""
        return re.sub(r"\s+", " ", node.get_text(" ", strip=True)).split("(")[0].strip()

    def _is_bot_challenge(self, text):
        return "making sure you're not a bot" in text.lower()

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
        match = re.search(r"Obsahy\(\d+\)\s*(?:zobrazit (?:vsechny|všechny) obsahy)?\s*(.+?)(?:\n\s*\*|\n\s*Videa|\n\s*Recenze)", text, re.I | re.S)
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
        known = ["Akční", "Animovaný", "Drama", "Fantasy", "Horor", "Komedie", "Krimi", "Romantický", "Sci-Fi", "Thriller"]
        return [genre for genre in known if re.search(rf"\b{re.escape(genre)}\b", text, re.I)]
