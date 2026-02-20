import requests

class FastshareScraper:
    API_URL = "https://fastshare.cz/api/api_json2.php"
    
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.logged_in = False

    def login(self):
        if not self.username or not self.password: return False
        try:
            # Fastshare nemá standardní API login, používá POST na /login
            r = self.session.post("https://fastshare.cz/login", data={
                "login_name": self.username,
                "login_password": self.password,
                "permanent": 1
            }, timeout=10)
            if "odhlásit" in r.text.lower() or "logout" in r.text.lower():
                self.logged_in = True
                return True
        except Exception as e:
            print(f"FS Login Error: {e}")
        return False

    def search(self, query):
        if not self.logged_in and not self.login(): return []
        
        try:
            r = self.session.get(self.API_URL, params={
                "process": "search",
                "string": query,
                "type": "video"
            }, timeout=10)
            data = r.json()
            
            results = []
            if "files" in data:
                for f in data["files"]:
                    results.append({
                        "provider": "fastshare",
                        "ident": f["id"],
                        "name": f["name"],
                        "size": int(f["size_bytes"] if "size_bytes" in f else 0)
                    })
            return results
        except Exception as e:
            print(f"FS Search Error: {e}")
            return []

    def get_link(self, ident):
        if not self.logged_in and not self.login(): return None
        try:
            r = self.session.get(self.API_URL, params={
                "process": "download_file",
                "file_id": ident
            }, timeout=10)
            data = r.json()
            return data.get("link")
        except:
            return None
