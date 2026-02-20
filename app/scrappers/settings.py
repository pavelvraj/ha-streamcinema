import json
import os

OPTIONS_PATH = "/data/options.json"

def get_settings():
    # Výchozí hodnoty pro testování na PC (mimo HA)
    settings = {
        "webshare_username": "",
        "webshare_password": "",
        "fastshare_username": "",
        "fastshare_password": ""
    }
    
    # Pokud běžíme v HA, načteme options.json
    if os.path.exists(OPTIONS_PATH):
        try:
            with open(OPTIONS_PATH, "r") as f:
                data = json.load(f)
                settings.update(data)
        except Exception as e:
            print(f"Chyba při čtení options.json: {e}")
            
    return settings

# Použití
config = get_settings()
WS_USER = config["webshare_username"]
WS_PASS = config["webshare_password"]
FS_USER = config["fastshare_username"]
FS_PASS = config["fastshare_password"]
