# Changelog

Všechny důležité změny add-onu StreamCinema API jsou vedené v tomto souboru.

## 0.1.16

- Opraven Webshare login: odstraněn neplatný parametr `rounds` u `md5_crypt` a doplněn Webshare `digest`.
- Fastshare hledání nyní zkouší více API parametrů a při selhání používá webový fallback.
- Zlepšeno logování chyb providerů.

## 0.1.15

- Opraveno otevření webového GUI přes Home Assistant Ingress, který posílal požadavek na cestu `//`.
- Backend nyní normalizuje vícenásobná lomítka v cestě před routováním.
- Odebrána explicitní volba `ingress_entry: /`, která mohla vést k dvojitému lomítku.

## 0.1.14

- Přidána kopie changelogu také do rootu repozitáře pro kompatibilitu s Home Assistant zobrazením `Seznam změn`.
- Zvýšena verze add-onu, aby Supervisor načetl nová metadata repozitáře.

## 0.1.13

- Přidán `CHANGELOG.md`, aby Home Assistant uměl zobrazit odkaz `Seznam změn`.
- Vyčištěna struktura GitHub repozitáře: add-on je pouze ve složce `streamcinema/`.
- Odstraněna stará root kopie add-on souborů, která mohla způsobovat zobrazení verze `0.1.10`.

## 0.1.12

- Přidán Home Assistant Ingress.
- Přidána položka `Stream Cinema` do levého menu Home Assistantu.
- Přidány volby `panel_title`, `panel_icon` a `panel_admin`.
- Upraveny frontend cesty na relativní, aby GUI fungovalo i pod Ingress URL.

## 0.1.11

- Opraven start aplikace z `main:app` na `app.main:app`.
- Dockerfile instaluje závislosti z `requirements.txt`.
- Opravena inicializace SQLite databáze a vytváření datové složky.
- Opravena serializace médií a streamů pro API.
- Doplněn funkční endpoint pro populární položky.

## 0.1.10

- Původní vývojová verze add-onu.
