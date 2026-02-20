import hashlib, requests
import xml.etree.ElementTree as ET
from vendor.md5crypt import md5crypt  # převzato z původního pluginu

class WebshareClient:
    BASE = "https://webshare.cz/api"

    def __init__(self, username, password):
        self.token = self._login(username, password)

    def _post(self, path, data):
        data.setdefault("wst", getattr(self, "token", ""))
        r = requests.post(f"{self.BASE}{path}", data=data,
                          headers={"Referer": "https://webshare.cz/"})
        return ET.fromstring(r.content)

    def _login(self, username, password):
        salt = self._post("/salt/", {"username_or_email": username}).find("salt").text
        hashed = hashlib.sha1(md5crypt(password, salt=salt).encode()).hexdigest()
        return self._post("/login/", {
            "username_or_email": username, "password": hashed, "keep_logged_in": 1
        }).find("token").text

    def search(self, query, category="video", limit=50):
        root = self._post("/search/", {
            "what": query, "category": category, "limit": limit
        })
        results = []
        for f in root.findall("file"):
            results.append({
                "ident": f.find("ident").text,
                "name":  f.find("name").text,
                "size":  int(f.find("size").text or 0),
                "type":  f.find("type").text,
            })
        return results

    def get_link(self, ident, device_uuid):
        root = self._post("/file_link/", {
            "ident": ident, "download_type": "video_stream",
            "device_uuid": device_uuid
        })
        return root.find("link").text
