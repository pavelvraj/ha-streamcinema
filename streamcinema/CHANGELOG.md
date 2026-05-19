# Changelog

Všechny důležité změny add-onu StreamCinema API jsou vedené v tomto souboru.

## 0.3.22

- Parser dílů nově rozpozná `S01E02` i po podtržítku nebo jiném oddělovači v názvu souboru.
- Přidáno rozpoznání numerických zápisů série/dílu jako `1-02`, `1 03`, `2 6`, `2_06` nebo `2.6`.
- Rozpoznávání má základní validaci rozsahu, aby se jako série/díl omylem nebraly roky nebo rozlišení.

## 0.3.21

- Průběh vyhledávání používá kompaktní formát `Filmů/Dílů · Streamů · Vyfiltrováno · Čas · aktuální krok`.
- Výsledky vyhledávání umí volitelně zobrazit `Ignorované streamy`, tedy položky vyřazené filtrem názvu.
- Přidáno tlačítko `Zastavit hledání`, které přeruší aktuální požadavek, vyčistí výsledky i vyhledávací pole a zobrazí informaci o zastavení.
- Pokud hledání skončí chybou, GUI zobrazí poslední dostupné výsledky; pokud server ještě nic nevrátil, zobrazí srozumitelné vysvětlení.

## 0.3.20

- Výběr žánrů ve vyhledávání i editaci je nově kompaktní chip seznam místo vysokého multi-select pole.
- Blok žánrů má omezenou výšku a vlastní scrollování, takže nerozbíjí rozložení stránky.
- Po zařazení vybraných streamů do sbírky se výsledky vyhledávání vyčistí a panel se schová.

## 0.3.19

- Opraveno zadávání hodnot do filtrů velikosti v aktualizační tabulce.
- Stav filtrů a řazení aktualizační nabídky se už neresetuje při každém překreslení tabulky, ale jen po nové aktualizaci.

## 0.3.18

- U každého streamu je nově tlačítko `Stáhnout`.
- Stažení používá stejný backend resolver/proxy link jako přehrávání, takže funguje jednotně pro Webshare i Fastshare.
- Tlačítko je dostupné ve vyhledávání, aktualizační nabídce i ve sbírce.

## 0.3.17

- Nové streamy nabídnuté po aktualizaci mají stejné třídění a filtrování jako výsledky vyhledávání.
- Výchozí řazení aktualizační nabídky je podle velikosti souboru sestupně.
- Filtrování a řazení aktualizační nabídky má vlastní stav, takže neovlivňuje hlavní výsledky vyhledávání.

## 0.3.16

- Vyhledávání a aktualizace zobrazují výrazný průběhový panel se spinnerem, běžícím časem a konkrétními kroky.
- Po dokončení hledání se zobrazí souhrn počtu streamů, zdrojů a u seriálů také sérií a dílů.
- Nové streamy nalezené aktualizací seriálu se znovu rozdělují podle sérií a dílů.
- Výběr žánrů je nově pevný vícenásobný seznam místo ručního textového pole.

## 0.3.15

- V části `Upravit položku` lze měnit název, žánry a uložený vyhledávací dotaz.
- Položky ve sbírce si ukládají původní text vyhledávání pro pozdější aktualizace.
- Detail položky má tlačítko `Aktualizovat`, které znovu vyhledá streamy, zachová nalezené, odstraní nenalezené a nabídne nové streamy k přidání do existující položky.
- Kontrola streamů rovnou zaškrtne nefunkční streamy označené k vyřazení.
- Žánry se zobrazují jako badge ve vyhledávání i ve sbírce a lze je upravit před uložením nebo v detailu položky.
- Vyhledávání používá jen zdroje s vyplněnými přihlašovacími údaji a bez alespoň jednoho zdroje hledání zablokuje s vysvětlením.
- Kliknutí kamkoliv do řádku streamu ve vyhledávání nebo sbírce přepíná příslušný checkbox.

## 0.3.14

- Webshare přehrávání nyní používá stejnou backend proxy jako Fastshare.
- Webshare token se před přehráním ověřuje a při chybě se automaticky obnoví.
- Generování Webshare linku posílá `device_uuid`, vynucuje HTTPS a zkouší fallback z `video_stream` na `file_download`.
- Proxy předává `wst` cookie a `Range` požadavky, aby šlo video načítat a posouvat i ve vestavěném prohlížečovém přehrávači.
- Ve sbírce je seznam streamů u filmu oddělený nadpisem `Streamy`, aby nelepil na akční tlačítka.

## 0.3.13

- Opraveno obecné přehrávání streamů z GUI pro Webshare i Fastshare.
- Frontend už nekóduje oddělovač providera v identifikátoru streamu, takže `/api/file_link/...` znovu správně rozpozná zdroj.
- Backend zároveň tolerantně dekóduje starší zakódovaný tvar identifikátoru.

## 0.3.12

- Opraveno přehrávání filmů z Fastshare ve vestavěném přehrávači.
- Fastshare přihlášení nyní používá Kodi API hash a ukládá cookie `FASTSHARE`.
- Výsledky Fastshare si ukládají přímý `download_url`, pokud ho API vrátí.
- Přehrávání Fastshare jde přes backend proxy, která předává cookie a podporuje `Range` požadavky pro načítání a posouvání videa.

## 0.3.11

- Výsledky vyhledávání seriálů jsou znovu rozdělené podle sérií a dílů.
- Každý díl má vlastní tabulku streamů se stejným řazením a filtrováním jako filmové výsledky.
- Filtry v tabulkách seriálu zůstávají společné, takže lze jedním výběrem vyřadit formát nebo velikost napříč všemi díly.

## 0.3.10

- Část `Upravit položku` ve sbírce je nově ve výchozím stavu schovaná.
- Detail položky zobrazuje tlačítko `Upravit položku`, které otevře editační formulář.
- Formulář má tlačítka `Uložit změny` a `Storno`; obě po dokončení vrátí detail do základního stavu.

## 0.3.9

- Výsledky vyhledávání v GUI jsou nově v tabulce místo řádkových karet.
- Záhlaví tabulky umožňuje řadit podle zdroje, názvu, formátu, velikosti, rozlišení a délky.
- Filtry v záhlaví umožňují omezit zdroj, formát, část názvu a minimální nebo maximální velikost.
- Řazení podle velikosti používá skutečné bajty, takže například `12 GB` je správně větší než `150 MB`.

## 0.3.8

- Opravena velikost souborů u Fastshare výsledků.
- Fastshare parser nyní čte vnořený tvar `data.value` z Kodi API odpovědi.
- Číselné velikosti vrácené jako text se berou jako bajty a v GUI se správně zobrazí jako MB/GB.
- Ze stejného vnořeného tvaru se doplňuje také délka videa.

## 0.3.7

- ČSFD metadata nově používají fallback přes otevřené CZDB API, protože přímé HTML ČSFD dnes vrací anti-bot stránku.
- ČSFD fallback doplňuje název, původní název, rok, hodnocení, plakát, fanart, popis, žánry a IMDb ID, pokud je dostupné.
- IMDb scraper už nevrací prázdná metadata při AWS WAF challenge a místo toho použije funkční suggestion data.
- IMDb detail se pokusí doplnit metadata přes CZDB podle IMDb ID.

## 0.3.6

- Vyhledávání nyní vždy sloučí výsledky z Webshare i Fastshare.
- Výsledky streamů se filtrují podle všech slov v původním zadání.
- Filtr porovnává normalizovaný název bez teček, mezer a diakritiky, takže například `Jacks` projde přes `Percy.Jackson.mkv`.
- Fastshare scraper už nekončí po první neprázdné sadě výsledků a sbírá výsledky ze všech dostupných Fastshare metod.

## 0.3.5

- Fastshare vyhledávání nyní používá stejný `api_kodi.php` endpoint jako oficiální KODI plugin.
- Primární Fastshare dotaz posílá `process=search`, `pagination=200`, `term` a `adult=0`.
- Původní Fastshare API varianta zůstává jako fallback pro případ změny endpointu.
- Aktualizován popisek add-onu pro Home Assistant repozitář.

## 0.3.4

- U každého streamu přidáno tlačítko `Přehrát`.
- GUI umí získat přímý link přes `/api/file_link/...` a otevřít ho ve vestavěném HTML5 přehrávači.
- Přehrávač má ovládání, možnost celé obrazovky a odkaz pro otevření streamu mimo GUI.
- Akce `Kontrola` a `Vyřadit označené` jsou přesunuté přímo nad seznam streamů.

## 0.3.3

- Streamy ve vyhledávání i ve sbírce mají kompaktnější řádek.
- Formát, velikost, rozlišení a délka jsou nově v jedné řádce vedle badge.

## 0.3.2

- Rozbalovací volby typu média a filtru sbírky nahrazeny jedním klikem ovládanými option tlačítky.
- V detailu položky je nově možné ručně upravit hodnocení v procentech.

## 0.3.1

- Výsledky vyhledávání seriálů se nově seskupují do sérií a dílů ještě před uložením do sbírky.
- Parser dílů lépe rozpoznává zápisy `S01E02`, `1x02`, `Epizoda 2`, `Díl 2` a textové varianty se sérií.
- Zdroje streamů mají odlišné barvy od badge stavů.
- ČSFD scraper je robustnější a podporuje volitelnou externí službu `node-csfd-api` přes konfiguraci `csfd_api_url`.
- Přidána dokumentace k `csfd_api_url` a poznámka k oficiálnímu IMDb API.

## 0.3.0

- Ve sbírce přidáno smazání celé položky filmu nebo seriálu včetně streamů.
- Detail položky nově umožňuje změnit typ Film/Seriál, popis a poster pomocí URL nebo nahraného obrázku.
- Po změně typu se streamy znovu přeskupí podle sérií a dílů.
- U streamů ve sbírce jsou funkční checkboxy a tlačítko `Vyřadit označené` maže vybrané streamy.
- Katalog zobrazuje modrý štítek s procentem hodnocení u každé položky.
- Streamy mají barevné badge pro zdroj i stav.

## 0.2.9

- Přidán Fastshare AJAX scraper podle webového endpointu `/test2.php`.
- Fastshare AJAX hledání posílá base64 dotaz stejně jako web `fastshare.cloud/<dotaz>/s`.
- Parser Fastshare HTML výsledků čte identifikátor, název, velikost, rozlišení a délku.

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
