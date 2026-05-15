# Changelog

This file is intentionally duplicated at the repository root for Home Assistant compatibility. The add-on changelog source is `streamcinema/CHANGELOG.md`.

## 0.3.15

- The edit form can now change title, genres, and the stored search query.
- Collection items remember the original search text for future refreshes.
- Media details now include an `Aktualizovat` button that searches again, keeps matching streams, removes missing streams, and offers newly found streams for the existing item.
- Stream checks now preselect broken streams marked for removal.
- Genres are shown as badges in search and collection views and can be edited before saving or from item details.
- Search only uses providers with configured credentials and is blocked with a clear message when no provider is configured.
- Clicking anywhere in a stream row toggles its checkbox in search and collection views.

## 0.3.14

- Webshare playback now uses the same backend proxy as Fastshare.
- The Webshare token is validated before playback and automatically refreshed after link errors.
- Webshare link generation sends `device_uuid`, forces HTTPS, and falls back from `video_stream` to `file_download`.
- The proxy forwards the `wst` cookie and `Range` requests so video can load and seek in the embedded browser player.
- Movie collection stream lists are separated from action buttons with a `Streamy` heading.

## 0.3.13

- Fixed general stream playback from the GUI for both Webshare and Fastshare.
- The frontend no longer encodes the provider separator in stream identifiers, so `/api/file_link/...` can resolve the provider again.
- The backend also tolerantly decodes older encoded stream identifier paths.

## 0.3.12

- Fixed movie playback from Fastshare in the embedded player.
- Fastshare login now uses the Kodi API hash and stores the `FASTSHARE` cookie.
- Fastshare search results persist the direct `download_url` when the API returns it.
- Fastshare playback now goes through a backend proxy that forwards the cookie and supports `Range` requests for loading and seeking video.

## 0.3.11

- TV show search results are grouped by seasons and episodes again.
- Each episode has its own sortable and filterable stream table.
- TV show table filters remain shared, so one format or size filter can narrow streams across all episodes.

## 0.3.10

- The collection detail edit section is hidden by default.
- Media details now show an `Upravit položku` button that opens the edit form.
- The edit form has `Uložit změny` and `Storno`; both return the detail view to its default state.

## 0.3.9

- Search results in the GUI now render as a table instead of row cards.
- The table header can sort by provider, filename, format, size, resolution, and duration.
- Header filters can narrow provider, format, filename text, and minimum or maximum size.
- Size sorting uses the real byte value, so `12 GB` correctly sorts above `150 MB`.

## 0.3.8

- Fixed file sizes for Fastshare search results.
- The Fastshare parser now reads the nested `data.value` shape from the Kodi API response.
- Numeric sizes returned as strings are treated as bytes and display correctly as MB/GB in the GUI.
- Video duration is also populated from the same nested API shape.

## 0.3.7

- ČSFD metadata now use the open CZDB API as a fallback because direct ČSFD HTML currently returns an anti-bot page.
- The ČSFD fallback fills title, original title, year, rating, poster, fanart, plot, genres, and IMDb ID when available.
- IMDb no longer returns empty metadata during an AWS WAF challenge and falls back to working suggestion data.
- IMDb details try to enrich metadata through CZDB by IMDb ID.

## 0.3.6

- Search now always merges results from both Webshare and Fastshare.
- Stream results are filtered by every word from the original query.
- Filtering compares normalized names without dots, spaces, and diacritics, so `Jacks` matches `Percy.Jackson.mkv`.
- Fastshare no longer stops after the first non-empty result set and collects results from all available Fastshare search methods.

## 0.3.5

- Fastshare search now uses the same `api_kodi.php` endpoint as the official KODI plugin.
- The primary Fastshare request sends `process=search`, `pagination=200`, `term`, and `adult=0`.
- The previous Fastshare API shape remains as a fallback in case the endpoint changes.
- Updated the Home Assistant add-on description.

## 0.3.4

- Added a `Přehrát` button to each stream.
- The GUI can resolve direct links through `/api/file_link/...` and open them in an embedded HTML5 player.
- The player includes controls, fullscreen support, and an external open-link fallback.
- Moved the stream bulk actions `Kontrola` and `Vyřadit označené` directly above the stream list.

## 0.3.3

- Made stream rows more compact in search results and the collection.
- Format, size, resolution, and duration now sit on the same line as badges.

## 0.3.2

- Replaced media type and collection filter dropdowns with one-click option buttons.
- Added manual rating editing in the media detail.

## 0.3.1

- Search results for TV shows are now grouped into seasons and episodes before saving.
- Episode parsing better recognizes `S01E02`, `1x02`, `Epizoda 2`, `Díl 2`, and textual season variants.
- Stream provider badges now use colors distinct from stream status badges.
- The ČSFD scraper is more robust and can optionally use an external `node-csfd-api` service through `csfd_api_url`.
- Added documentation for `csfd_api_url` and clarified the official IMDb API status.

## 0.3.0

- Added deleting a whole movie or TV show collection item, including its streams.
- Added media editing for Film/TV show type, plot, and poster via URL or uploaded image.
- Re-groups streams after changing the media type.
- Added working collection stream checkboxes and selected stream removal.
- Added blue rating badges to every item in the collection list.
- Added colored stream badges for provider and status.

## 0.2.9

- Added Fastshare AJAX scraper based on the website endpoint `/test2.php`.
- Fastshare AJAX search now sends the base64 query used by `fastshare.cloud/<query>/s`.
- Fastshare HTML result parsing extracts ident, name, size, resolution, and duration.

## 0.2.8

- Fastshare parser now reads results from nested `search.file` responses.
- Fastshare search tries multi-word query variants, for example `Jack Reacher`, `Reacher`, and `Jack`.
- Empty Fastshare `total=0` responses are no longer logged as unrecognized responses.

## 0.2.7

- Fastshare scraper now tries both `fastshare.cloud` and `fastshare.cz`.
- Fastshare API, login, and web fallback work with both domains.
- Added `Hledání` and `Sbírka` tabs so search results and the collection stay separated.
- After saving streams, the GUI switches to the saved item in the `Sbírka` tab.

## 0.2.6

- Fixed saving selected streams from the fallback search results page.
- The fallback page no longer posts to `POST /media`; it posts to the correct API route.

## 0.2.5

- Fixed Fastshare search to use the mobile API shape `process=search&term=...&page=...`.
- Added Fastshare result pagination.
- Fastshare JSON parsing now supports more response field variants.
- Fastshare link fallback now returns `https://fastshare.cz/free/?lang=cs&u=IDENT` when premium link generation is unavailable.
- Added debug logging for unrecognized Fastshare API responses.

## 0.2.4

- Added a movie/TV show search selector.
- TV show search tries the base title, `Epizoda`, and seasons `S01` through `S08`.
- Episode parsing now recognizes `SxxEyy`, `1x02`, and `Epizoda 12`.
- The fallback result page shows movies in a table and TV shows grouped by season and episode.
- Stream providers are displayed as colored badges.
- `Hledat další` appends additional streams to the current result overview.
- IMDb fallback now uses the more available suggestion endpoint.

## 0.2.3

- `/api/search` now returns an HTML search result page for normal form submissions instead of raw JSON.
- JavaScript JSON search moved to `/api/search_json`.
- The fallback result page can select streams and save them to the collection even if the main Ingress JavaScript does not run.

## 0.2.2

- Added an HTML form fallback for search, so even without JavaScript the `Hledat` button calls `/api/search`.
- Added cache busting for `app.js` and `style.css`.
- Added an XHR fallback for older WebViews without `fetch`.
- Removed `Promise.finally` and `Element.closest` for compatibility.
- Added a visible `GUI načteno.` indicator so it is clear whether JavaScript started.

## 0.2.1

- Fixed the `Hledat` button in the Home Assistant Ingress GUI.
- Removed inline `onclick`/`onchange` handlers from the frontend.
- Rewrote the frontend to use more compatible JavaScript without `?.`, `??`, and `replaceAll`.
- The search button now shows `Hledám...` while a search request is running.

## 0.2.0

- Added a catalog view for saved movies and TV shows.
- Added a media detail view with poster, plot, rating, genres, and streams.
- TV shows are grouped by season and episode based on stream filenames.
- Search now displays found streams before saving and lets the user choose which streams to add.
- Added stream checks that mark broken streams for removal.
- Added single-stream removal and bulk removal of streams marked for deletion.
- Added IMDb metadata fallback when ČSFD does not return metadata.
- Extended the stream database model with status, format, season, episode, and last check timestamp.

## 0.1.16

- Fixed Webshare login by removing the invalid `rounds` argument from `md5_crypt` and adding the Webshare `digest` field.
- Fastshare search now tries multiple API parameter variants and falls back to web search parsing.
- Improved provider error logging.

## 0.1.15

- Fixed opening the web GUI through Home Assistant Ingress when Supervisor requested `//`.
- The backend now normalizes duplicate slashes before routing.
- Removed the explicit `ingress_entry: /` option, which could contribute to the double slash path.

## 0.1.14

- Added a root-level changelog copy so Home Assistant can display the `Seznam změn` link even when it looks at repository-level metadata.
- Bumped the add-on version to force Supervisor metadata refresh.

## 0.1.13

- Added `CHANGELOG.md` inside the add-on folder.
- Cleaned up the GitHub repository layout so the add-on lives only in `streamcinema/`.
- Removed the old root add-on copy that could make Home Assistant show version `0.1.10`.

## 0.1.12

- Added Home Assistant Ingress.
- Added the `Stream Cinema` sidebar entry.
- Added `panel_title`, `panel_icon`, and `panel_admin`.
- Switched frontend asset and API paths to relative paths for Ingress.

## 0.1.11

- Fixed app startup from `main:app` to `app.main:app`.
- Installed Docker dependencies from `requirements.txt`.
- Fixed SQLite initialization and data directory creation.
- Fixed media and stream API serialization.
- Added a working popular media endpoint.

## 0.1.10

- Initial development version.
