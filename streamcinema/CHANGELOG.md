# Changelog

Všechny důležité změny add-onu StreamCinema API jsou vedené v tomto souboru.

## 0.2.8

- Fastshare parser nově čte výsledky z vnořeného tvaru `search.file`.
- Fastshare hledání zkouší varianty víceslovných dotazů, například `Jack Reacher`, `Reacher`, `Jack`.
- Prázdná Fastshare odpověď `total=0` už se neloguje jako nerozpoznaná odpověď.

## 0.2.7

- Fastshare scraper nyní zkouší `fastshare.cloud` i `fastshare.cz`.
- Fastshare API, login a web fallback pracují s oběma doménami.
- Přidány záložky `Hledání` a `Sbírka`, aby se výsledky hledání nemíchaly s katalogem.
- Po uložení streamů se GUI přepne do záložky `Sbírka` na uložené médium.

## 0.2.6

- Opraveno ukládání vybraných streamů z fallback výsledkové stránky.
- Fallback stránka už neposílá `POST /media`, ale správně `POST /api/media` relativně přes `media`.

## 0.2.5

- Opraveno Fastshare vyhledávání podle mobilního API tvaru `process=search&term=...&page=...`.
- Přidáno stránkování Fastshare výsledků.
- Parser Fastshare JSONu podporuje více variant názvů polí.
- Fastshare link bez premium loginu vrací free URL `https://fastshare.cz/free/?lang=cs&u=IDENT`.
- Přidáno ladicí logování nerozpoznané Fastshare API odpovědi.

## 0.2.4

- Přidán výběr, zda hledat film nebo seriál.
- Seriálové hledání zkouší základní název, `Epizoda` a série `S01` až `S08`.
- Parser dílů rozpozná `SxxEyy`, `1x02` i `Epizoda 12`.
- Fallback výsledková stránka zobrazuje filmy v tabulce a seriály po sériích a dílech.
- Zdroje streamů jsou označené barevnými štítky.
- Tlačítko `Hledat další` doplňuje další nalezené streamy do aktuálního přehledu.
- IMDb fallback nově používá dostupnější suggestion endpoint.

## 0.2.3

- `/api/search` nyní při formulářovém odeslání vrací HTML stránku s výsledky místo surového JSONu.
- JSON vyhledávání pro JavaScript bylo přesunuto na `/api/search_json`.
- Výsledková fallback stránka umožňuje vybrat streamy a uložit je do sbírky i v případě, že hlavní JavaScript v Ingressu neběží.

## 0.2.2

- Přidán HTML formulářový fallback pro hledání, takže i bez JavaScriptu klik na `Hledat` zavolá `/api/search`.
- Přidán cache-busting pro `app.js` a `style.css`.
- Přidán XHR fallback pro starší WebView bez `fetch`.
- Odstraněn `Promise.finally` a `Element.closest` kvůli kompatibilitě.
- Přidána viditelná indikace `GUI načteno.`, aby šlo poznat, že se JavaScript spustil.

## 0.2.1

- Opraveno kliknutí na tlačítko `Hledat` v Home Assistant Ingress GUI.
- Frontend už nepoužívá inline `onclick`/`onchange` handlery.
- Frontend byl přepsán na kompatibilnější JavaScript bez `?.`, `??` a `replaceAll`.
- Tlačítko hledání při běžícím dotazu ukazuje stav `Hledám...`.

## 0.2.0

- Přidán katalog uložených filmů a seriálů.
- Přidán detail média s posterem, popisem, hodnocením, žánry a streamy.
- Seriály se zobrazují po sériích a dílech podle názvů streamů.
- Vyhledávání nyní zobrazí nalezené streamy před uložením a dovolí vybrat konkrétní položky.
- Přidána kontrola streamů s označením chybných položek k vyřazení.
- Přidáno samostatné vyřazení streamu i hromadné vyřazení označených streamů.
- Přidán IMDb fallback metadat, když ČSFD nic nevrátí.
- Rozšířena databáze streamů o stav, formát, sezónu, díl a čas poslední kontroly.

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
