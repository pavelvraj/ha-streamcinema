import requests

class FastshareClient:
    # Neoficiální API endpoint nalezený z mobilní aplikace
    API = "https://fastshare.cz/api/api_json2.php"

    def __init__(self, username, password):
        self.session = requests.Session()
        self._login(username, password)

    def _login(self, username, password):
        self.session.post("https://fastshare.cz/login", data={
            "login_name": username, "login_password": password
        })

    def search(self, query):
        r = self.session.get(self.API, params={
            "process": "search",
            "string": query,
            "type": "video"
        })
        return r.json().get("files", [])

    def get_link(self, file_id):
        r = self.session.get(self.API, params={
            "process": "download_file",
            "file_id": file_id
        })
        return r.json().get("link")
