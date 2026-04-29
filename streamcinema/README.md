# StreamCinema API

Lokální backend pro vyhledávání filmů a seriálů na Webshare a Fastshare, ukládání výsledků do SQLite databáze a zpřístupnění katalogu přes HTTP API. Projekt je připravený jako Home Assistant add-on, takže může běžet přímo na Home Assistant OS, například na Raspberry Pi 4.

Add-on poskytuje jednoduché webové GUI na `/` a API endpointy pod `/api/...`, které jsou zamýšlené jako lokální náhrada backendu pro KODI/Stream-Cinema workflow.

## Co to dělá

- Vyhledá soubory na Webshare a Fastshare.
- Ke hledanému názvu se pokusí dohledat metadata z ČSFD.
- Uloží médium a nalezené streamy do SQLite databáze.
- Vrací data přes API ve struktuře použitelné pro katalog médií.
- Umí vrátit stream link podle identifikátoru providera.
- Nabízí jednoduché webové rozhraní pro ruční hledání.

## Aktuální omezení

- ČSFD může vracet anti-bot stránku. V takovém případě add-on poběží dál, ale metadata se pro dané hledání neuloží.
- Kompatibilita s KODI pluginem je základní a může vyžadovat další doladění podle konkrétní verze pluginu.
- Seriály zatím nejsou plnohodnotně modelované po sezónách a epizodách. Databázové jádro je připravené hlavně pro katalog médií a streamů.
- Fastshare a Webshare API/scraping se mohou změnit. Pokud provider změní endpointy nebo přihlašování, bude potřeba upravit scraper.

## Architektura

| Komponenta | Popis |
| --- | --- |
| Home Assistant add-on | Spouští aplikaci jako Docker kontejner v HA Supervisoru. |
| FastAPI backend | HTTP API a obsluha webového GUI. |
| SQLite databáze | Lokální databáze médií a streamů. |
| Webshare scraper | Vyhledávání souborů a získávání stream linku z Webshare. |
| Fastshare scraper | Vyhledávání souborů a získávání stream linku z Fastshare. |
| ČSFD scraper | Pokus o získání názvu, roku, hodnocení, popisu, žánrů a posteru. |
| Web GUI | Jednoduchá single-page stránka pro ruční hledání. |

## Databáze

Databáze se ukládá do mapovaného Home Assistant config adresáře:

```text
/config/streamcinema/data/db.sqlite
```

Hlavní tabulky:

- `media`: katalog filmů/seriálů a jejich metadata.
- `streams`: nalezené soubory u providerů, navázané na `media.id`.

Základní pole v `media`:

- `id`
- `type`
- `title`
- `original_title`
- `year`
- `genres`
- `rating`
- `plot`
- `poster`
- `fanart`
- `imdb_id`
- `csfd_id`

Základní pole v `streams`:

- `id`
- `media_id`
- `provider`
- `ident`
- `filename`
- `size`
- `duration`
- `width`
- `height`
- `audio`
- `subtitles`

## API

### Ping

```http
GET /api/ping
```

Očekávaná odpověď:

```json
{
  "status": "ok",
  "message": "pong"
}
```

### Ruční hledání

```http
GET /api/search_manual?q=Matrix
```

Spustí hledání na providerech, pokusí se stáhnout metadata z ČSFD a výsledek uloží do SQLite.

### Vyhledání v katalogu

```http
GET /api/media/movies/filter/titleOrActor/Matrix/
```

Pokud v lokální databázi nic nenajde, endpoint spustí live hledání a poté vrátí uložená média.

### Populární položky

```http
GET /api/media/movies/popular/-1/
```

Vrátí média z databáze seřazená podle hodnocení.

### Stream link

```http
GET /api/file_link/webshare:IDENT
GET /api/file_link/fastshare:IDENT
```

Vrátí přímý link získaný přes odpovídající provider.

## Nasazení do Home Assistantu

### 1. Připrav repozitář add-onu

Home Assistant očekává, že GitHub repozitář bude mít v rootu soubor `repository.yaml` a add-on bude v samostatné složce.

Doporučená struktura repozitáře:

```text
HA-Stream-Cinema/
  repository.yaml
  streamcinema/
    config.yaml
    Dockerfile
    run.sh
    requirements.txt
    README.md
    app/
      main.py
      database.py
      scrapers/
      static/
```

Root soubor `repository.yaml` může vypadat například takto:

```yaml
name: StreamCinema API Add-ons
url: https://github.com/TVUJ_UZIVATEL/HA-Stream-Cinema
maintainer: Pavel <pavel@example.com>
```

URL nahraď skutečnou adresou svého GitHub repozitáře.

### 2. Zkontroluj architekturu

V `streamcinema/config.yaml` je aktuálně povolená architektura:

```yaml
arch:
  - aarch64
```

To odpovídá Raspberry Pi 4 s 64bit Home Assistant OS. Pokud používáš jinou platformu, přidej odpovídající architekturu, například:

```yaml
arch:
  - aarch64
  - armv7
  - amd64
```

Používej jen architektury, na kterých chceš add-on skutečně stavět a provozovat.

### 3. Nahraj projekt na GitHub

Do Home Assistantu se přidává URL celého repozitáře, ne URL podsložky `streamcinema`.

Správně:

```text
https://github.com/TVUJ_UZIVATEL/HA-Stream-Cinema
```

Špatně:

```text
https://github.com/TVUJ_UZIVATEL/HA-Stream-Cinema/tree/main/streamcinema
```

### 4. Přidej repozitář v Home Assistantu

V Home Assistantu:

1. Otevři `Settings -> Add-ons -> Add-on Store`.
2. Klikni na tři tečky vpravo nahoře.
3. Otevři `Repositories`.
4. Vlož URL GitHub repozitáře.
5. Ulož.
6. Obnov Add-on Store.

Ve store by se měl objevit add-on `StreamCinema API`.

### 5. Nainstaluj a nastav add-on

1. Otevři add-on `StreamCinema API`.
2. Klikni na `Install`.
3. Po instalaci otevři záložku `Configuration`.
4. Vyplň přihlašovací údaje:

```yaml
webshare_username: ""
webshare_password: ""
fastshare_username: ""
fastshare_password: ""
```

Webshare nebo Fastshare může zůstat prázdný, ale pro získávání stream linků je obvykle potřeba funkční účet u daného providera.

5. Ulož konfiguraci.
6. V záložce `Info` klikni na `Start`.
7. Volitelně zapni `Start on boot`.

### 6. Ověř běh add-onu

V logu add-onu by se mělo objevit něco podobného:

```text
Startuji StreamCinema API...
INFO:     Started server process [...]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8765
```

API ověříš v prohlížeči:

```text
http://IP_ADRESA_HOME_ASSISTANTU:8765/api/ping
```

Webové GUI:

```text
http://IP_ADRESA_HOME_ASSISTANTU:8765/
```

## Lokální spuštění mimo Home Assistant

Pro rychlý vývoj můžeš aplikaci spustit i mimo HA. Doporučené je nastavit vlastní cestu k databázi, aby se nepoužívalo `/config`.

```powershell
cd streamcinema
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:STREAMCINEMA_DB_PATH = "$PWD\dev-db.sqlite"
python -m uvicorn app.main:app --host 0.0.0.0 --port 8765
```

Pak otevři:

```text
http://localhost:8765/
```

## Konfigurace add-onu

Konfigurace je uložená v Home Assistant Supervisoru a kontejner ji čte z:

```text
/data/options.json
```

Podporované volby:

| Volba | Popis |
| --- | --- |
| `webshare_username` | Uživatelské jméno nebo e-mail pro Webshare. |
| `webshare_password` | Heslo pro Webshare. |
| `fastshare_username` | Uživatelské jméno pro Fastshare. |
| `fastshare_password` | Heslo pro Fastshare. |

## Troubleshooting

### Add-on se nezobrazuje v Add-on Store

Zkontroluj:

- V rootu GitHub repozitáře existuje `repository.yaml`.
- Add-on je ve složce `streamcinema`.
- Ve složce `streamcinema` existuje `config.yaml`.
- URL v HA míří na root GitHub repozitáře.
- Architektura v `config.yaml` odpovídá zařízení.

### Add-on nejde spustit

Otevři log add-onu a hledej chyby při startu. Správný startovací příkaz je:

```text
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8765
```

Pokud log hlásí problém s importem modulu, zkontroluj, že Dockerfile kopíruje složku `app` do `/app/app`.

### API neodpovídá

Zkontroluj:

- Add-on běží.
- Port `8765/tcp` je v `config.yaml`.
- Voláš správnou IP adresu Home Assistantu.
- V HA síti není port blokovaný.

### Databáze se nevytváří

Zkontroluj, že `config.yaml` obsahuje:

```yaml
map:
  - config:rw
```

Add-on musí mít právo zapisovat do `/config`, aby mohl vytvořit:

```text
/config/streamcinema/data/db.sqlite
```

### ČSFD nevrací metadata

ČSFD může vrátit anti-bot stránku. V logu se potom objeví hláška podobná:

```text
CSFD Search Error: bot protection page returned
```

V takovém případě se médium uloží s fallback metadaty nebo bez metadat.

### Webshare nebo Fastshare nic nenajde

Zkontroluj:

- Přihlašovací údaje v konfiguraci add-onu.
- Jestli účet u providera funguje v běžném prohlížeči.
- Log add-onu, kde scraper vypisuje chyby providerů.

## Vývojové poznámky

- Backend je v `app/main.py`.
- SQLite helper je v `app/database.py`.
- Scrapery jsou v `app/scrapers/`.
- Web GUI je v `app/static/`.
- Docker entrypoint je `run.sh`.
- Python závislosti jsou v `requirements.txt`.

Po změně kódu v GitHub repozitáři je v Home Assistantu obvykle potřeba add-on znovu sestavit nebo přeinstalovat, aby Supervisor použil aktuální verzi.
