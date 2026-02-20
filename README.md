# StreamCinema API (Home Assistant Add-on)

Lokální náhrada za původní Stream Cinema backend, běžící jako Home Assistant add-on na Raspberry Pi 4.  
Cílem je:

- mít vlastní databázi filmů a seriálů,
- automaticky vyhledávat streamy na **Webshare** a **Fastshare**,
- stahovat metadata z **ČSFD.cz**,
- zpřístupnit vše přes API kompatibilní s KODI pluginem (Stream-Cinema) a jednoduché webové GUI.

---

## Funkce

- Vyhledávání filmů/seriálů na Webshare.cz a Fastshare.cz.
- Automatické uložení výsledků do SQLite databáze na HA (`/config/streamcinema/data/db.sqlite`).
- Získání metadat (název, rok, žánry, popis, hodnocení, poster) z ČSFD.cz.
- API kompatibilní se strukturo u původního pluginu Stream-Cinema (`/api/media/...`).
- Webové GUI pro manuální hledání a základní správu katalogu.
- Připraveno pro napojení KODI pluginu (přes HTTP).

---

## Architektura

### Komponenty

| Komponenta        | Popis                                       |
|-------------------|---------------------------------------------|
| Home Assistant    | Hostuje add-on (Docker kontejner)          |
| StreamCinema API  | FastAPI backend, běží v add-onu            |
| SQLite DB         | Uložení médií a streamů (`/config/streamcinema/data`) |
| Webshare scraper  | Hledání a linkování souborů z Webshare.cz  |
| Fastshare scraper | Hledání a linkování souborů z Fastshare.cz |
| ČSFD scraper      | Metadata (titulek, poster, hodnocení, žánry) |
| Web GUI           | Single-page aplikace na `/` v rámci add-onu |

### Datový model

**Tabulka `media`:**

- `id` – unikátní ID (např. `csfd_123456`, `manual_<hash>`),
- `type` – typ média (`movie`, `tvshow`),
- `title`, `original_title`,
- `year`,
- `genres` (JSON pole),
- `rating`,
- `plot`,
- `poster`, `fanart`,
- `imdb_id`, `csfd_id`.

**Tabulka `streams`:**

- `id` – PK,
- `media_id` – FK do `media.id`,
- `provider` – `webshare` nebo `fastshare`,
- `ident` – ID souboru u providera,
- `filename`,
- `size`,
- (volitelně) `duration`, `width`, `height`, `audio`, `subtitles`.

---

## Instalace jako Home Assistant Add-on

### 1. Přidání repozitáře

V Home Assistant:

1. Otevři **Settings → Add-ons → Add-on Store**.
2. Klikni na **⋮ (tři tečky) → Repositories**.
3. Přidej URL tohoto GitHub repozitáře.
4. Po uložení obnov stránku Add-on Store.

Ve spodní části se objeví sekce **StreamCinema API** (název repozitáře/doplňku).

### 2. Instalace a start

1. Otevři add-on **StreamCinema API**.
2. Klikni na **Install**.
3. Po instalaci otevři záložku **Configuration**:
   - vyplň `webshare_username`, `webshare_password`,
   - volitelně `fastshare_username`, `fastshare_password`,
   - případně uprav port (standardně `8765`).
4. Ulož konfiguraci.
5. V záložce **Info** klikni na **Start**.
6. Volitelně zapni **Start on boot**.

Log add-onu by měl zobrazit:

```text
Startuji StreamCinema API...
INFO:     Started server process [X]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8765
