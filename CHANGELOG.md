# Changelog

This file is intentionally duplicated at the repository root for Home Assistant compatibility. The add-on changelog source is `streamcinema/CHANGELOG.md`.

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
