import hashlib
import requests
import xml.etree.ElementTree as ET
from passlib.hash import md5_crypt

class WebshareScraper:
    API_URL = "https://webshare.cz/api"
    
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.token = None

    def _post(self, endpoint, data):
        if self.token:
            data['wst'] = self.token
        headers = {'User-Agent': 'Kodi StreamCinema Plugin'}
        try:
            response = requests.post(f"{self.API_URL}{endpoint}", data=data, headers=headers, timeout=10)
            return ET.fromstring(response.content)
        except Exception as e:
            print(f"WS Error: {e}")
            return None

    def login(self):
        if not self.username or not self.password: return False
        
        try:
            # 1. Salt
            salt_resp = self._post("/salt/", {"username_or_email": self.username})
            if salt_resp is None: return False
            salt = salt_resp.find("salt").text
            
            # 2. Hash (specifický WS postup)
            # Webshare používá md5_crypt s prefixem $1$
            password_md5 = md5_crypt.using(salt=salt, rounds=1000).hash(self.password)
            # Z výsledku se bere jen část hash (bez prefixu a saltu), ale passlib vrací celý řetězec
            # Webshare očekává SHA1 hash z celého md5crypt výsledku
            password_hash = hashlib.sha1(password_md5.encode('utf-8')).hexdigest()
            
            # 3. Login call
            token_resp = self._post("/login/", {
                "username_or_email": self.username,
                "password": password_hash,
                "keep_logged_in": 1
            })
            if token_resp is not None:
                token_el = token_resp.find("token")
                if token_el is not None:
                    self.token = token_el.text
                    return True
        except Exception as e:
            print(f"WS Login Exception: {e}")
        return False

    def search(self, query):
        if not self.token and not self.login(): return []
        
        root = self._post("/search/", {"what": query, "category": "video", "limit": 20})
        if root is None: return []
        
        results = []
        for f in root.findall("file"):
            results.append({
                "provider": "webshare",
                "ident": f.find("ident").text,
                "name": f.find("name").text,
                "size": int(f.find("size").text)
            })
        return results

    def get_link(self, ident):
        if not self.token and not self.login(): return None
        root = self._post("/file_link/", {"ident": ident, "download_type": "video_stream"})
        if root is not None:
            link = root.find("link")
            return link.text if link is not None else None
        return None
