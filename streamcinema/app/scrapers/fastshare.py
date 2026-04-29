import re
from urllib.parse import quote, urljoin, urlparse

import requests
from bs4 import BeautifulSoup


class FastshareScraper:
    API_URL = "https://fastshare.cz/api/api_json2.php"
    BASE_URL = "https://www.fastshare.cz"
    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
        )
    }

    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)
        self.logged_in = False

    def login(self):
        if not self.username or not self.password:
            return False

        try:
            response = self.session.post(
                "https://fastshare.cz/login",
                data={
                    "login_name": self.username,
                    "login_password": self.password,
                    "permanent": 1,
                },
                timeout=10,
            )
            response.raise_for_status()
            text = response.text.lower()
            if "logout" in text or "odhl" in text:
                self.logged_in = True
                return True
        except Exception as exc:
            print(f"FS Login Error: {exc}")

        return False

    def search(self, query):
        if self.username and self.password and not self.logged_in:
            self.login()

        results = self._search_api(query)
        if results:
            return results

        return self._search_web(query)

    def _search_api(self, query):
        variants = [
            {"process": "search", "string": query, "type": "video"},
            {"process": "search", "string": query, "type": "all"},
            {"process": "search", "term": query, "type": "video"},
            {"process": "search", "q": query, "type": "video"},
        ]

        last_error = None
        for params in variants:
            try:
                response = self.session.get(self.API_URL, params=params, timeout=10)
                response.raise_for_status()
                return self._parse_api_response(response.json())
            except Exception as exc:
                last_error = exc

        if last_error:
            print(f"FS API Search Error: {last_error}")
        return []

    def _parse_api_response(self, data):
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            items = (
                data.get("files")
                or data.get("data")
                or data.get("items")
                or data.get("results")
                or []
            )
        else:
            items = []

        results = []
        for item in items:
            if not isinstance(item, dict):
                continue

            ident = item.get("id") or item.get("file_id") or item.get("ident")
            name = item.get("name") or item.get("filename") or item.get("title")
            size = item.get("size_bytes") or item.get("size") or 0
            if not ident or not name:
                continue

            results.append(
                {
                    "provider": "fastshare",
                    "ident": str(ident),
                    "name": str(name),
                    "size": self._parse_size(size),
                }
            )

        return results

    def _search_web(self, query):
        urls = [
            f"{self.BASE_URL}/{quote(query)}/s",
            f"{self.BASE_URL}/fastshare/s",
        ]
        params_list = [
            {"type": "video"},
            {"term": query, "type": "video"},
        ]

        for url in urls:
            for params in params_list:
                try:
                    response = self.session.get(url, params=params, timeout=10)
                    response.raise_for_status()
                    results = self._parse_search_html(response.text)
                    if results:
                        return results
                except Exception as exc:
                    print(f"FS Web Search Error: {exc}")

        return []

    def _parse_search_html(self, html):
        soup = BeautifulSoup(html, "lxml")
        results = []
        seen = set()

        for link in soup.select("a[href]"):
            href = link.get("href") or ""
            absolute_url = urljoin(self.BASE_URL, href)
            parsed = urlparse(absolute_url)
            if "fastshare.cz" not in parsed.netloc:
                continue

            ident = self._ident_from_url(absolute_url)
            if not ident or ident in seen:
                continue

            name = link.get_text(" ", strip=True) or link.get("title") or ""
            if not self._looks_like_media(name):
                continue

            container_text = link.parent.get_text(" ", strip=True) if link.parent else name
            results.append(
                {
                    "provider": "fastshare",
                    "ident": ident,
                    "name": name,
                    "size": self._parse_size(container_text),
                }
            )
            seen.add(ident)

        return results[:20]

    def _ident_from_url(self, url):
        patterns = [
            r"[?&]id=(\d+)",
            r"/file/(\d+)",
            r"/(\d+)[-/]",
            r"/download/(\d+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None

    def _looks_like_media(self, name):
        lower = name.lower()
        extensions = (".mkv", ".mp4", ".avi", ".mov", ".wmv", ".m4v")
        return any(ext in lower for ext in extensions)

    def _parse_size(self, value):
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value)

        text = str(value).replace(",", ".")
        match = re.search(r"(\d+(?:\.\d+)?)\s*(kb|mb|gb|tb|b)", text, re.I)
        if not match:
            return 0

        amount = float(match.group(1))
        unit = match.group(2).lower()
        multipliers = {
            "b": 1,
            "kb": 1024,
            "mb": 1024**2,
            "gb": 1024**3,
            "tb": 1024**4,
        }
        return int(amount * multipliers[unit])

    def get_link(self, ident):
        if not self.logged_in and not self.login():
            return None

        try:
            response = self.session.get(
                self.API_URL,
                params={"process": "download_file", "file_id": ident},
                timeout=10,
            )
            response.raise_for_status()
            return response.json().get("link")
        except Exception as exc:
            print(f"FS Link Error: {exc}")
            return None
