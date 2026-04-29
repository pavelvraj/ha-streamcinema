import hashlib
import xml.etree.ElementTree as ET

import requests
from passlib.hash import md5_crypt


class WebshareScraper:
    API_URL = "https://webshare.cz/api"

    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.token = None

    def _post(self, endpoint, data):
        data = dict(data)
        if self.token:
            data["wst"] = self.token

        headers = {
            "Accept": "text/xml; charset=UTF-8",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "User-Agent": "Kodi StreamCinema Plugin",
        }

        try:
            response = requests.post(
                f"{self.API_URL}{endpoint}",
                data=data,
                headers=headers,
                timeout=10,
            )
            response.raise_for_status()
            return ET.fromstring(response.content)
        except Exception as exc:
            print(f"WS Error: {exc}")
            return None

    def _fatal_message(self, root):
        return root.findtext("message") or root.findtext("code") or "unknown error"

    def login(self):
        if not self.username or not self.password:
            return False

        try:
            salt_resp = self._post("/salt/", {"username_or_email": self.username})
            if salt_resp is None:
                return False
            if salt_resp.findtext("status") != "OK":
                print(f"WS Login Salt Error: {self._fatal_message(salt_resp)}")
                return False

            salt = salt_resp.findtext("salt")
            if not salt:
                print("WS Login Salt Error: missing salt")
                return False

            password_md5 = md5_crypt.using(salt=salt).hash(self.password)
            password_hash = hashlib.sha1(password_md5.encode("utf-8")).hexdigest()
            digest = hashlib.md5(
                f"{self.username}:Webshare:{password_hash}".encode("utf-8")
            ).hexdigest()

            token_resp = self._post(
                "/login/",
                {
                    "username_or_email": self.username,
                    "password": password_hash,
                    "digest": digest,
                    "keep_logged_in": 1,
                },
            )
            if token_resp is None:
                return False
            if token_resp.findtext("status") != "OK":
                print(f"WS Login Error: {self._fatal_message(token_resp)}")
                return False

            token = token_resp.findtext("token")
            if token:
                self.token = token
                return True
        except Exception as exc:
            print(f"WS Login Exception: {exc}")

        return False

    def search(self, query):
        if self.username and self.password and not self.token:
            self.login()

        root = self._post(
            "/search/",
            {"what": query, "category": "video", "limit": 20, "offset": 0},
        )
        if root is None:
            return []
        if root.findtext("status") != "OK":
            print(f"WS Search Error: {self._fatal_message(root)}")
            return []

        results = []
        for file_node in root.findall("file"):
            ident = file_node.findtext("ident")
            name = file_node.findtext("name") or ""
            size = file_node.findtext("size") or "0"
            if not ident:
                continue

            results.append(
                {
                    "provider": "webshare",
                    "ident": ident,
                    "name": name,
                    "size": int(size),
                }
            )
        return results

    def get_link(self, ident):
        if not self.token and not self.login():
            return None

        root = self._post(
            "/file_link/",
            {"ident": ident, "download_type": "video_stream"},
        )
        if root is None:
            return None
        if root.findtext("status") != "OK":
            print(f"WS Link Error: {self._fatal_message(root)}")
            return None

        return root.findtext("link")
