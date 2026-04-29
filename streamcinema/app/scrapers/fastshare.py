import requests


class FastshareScraper:
    API_URL = "https://fastshare.cz/api/api_json2.php"

    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.session = requests.Session()
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

        try:
            response = self.session.get(
                self.API_URL,
                params={"process": "search", "string": query, "type": "video"},
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()

            results = []
            for item in data.get("files", []):
                results.append(
                    {
                        "provider": "fastshare",
                        "ident": str(item.get("id") or ""),
                        "name": item.get("name") or "",
                        "size": int(item.get("size_bytes") or 0),
                    }
                )
            return [item for item in results if item["ident"]]
        except Exception as exc:
            print(f"FS Search Error: {exc}")
            return []

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
