(function () {
    var API_URL = "api";
    var catalogItems = [];
    var currentSearch = null;
    var selectedMediaId = null;
    var searchSort = { key: "size", direction: "desc" };
    var searchFilters = { provider: "", format: "", text: "", minSize: "", maxSize: "" };

    function el(id) {
        return document.getElementById(id);
    }

    function showStatus(message, type) {
        var node = el("status");
        if (!node) return;
        node.textContent = message || "";
        node.className = message ? "status " + (type || "info") : "status hidden";
    }

    function setSearching(isSearching) {
        var button = el("searchButton");
        if (!button) return;
        button.disabled = isSearching;
        button.textContent = isSearching ? "Hledám..." : "Hledat";
    }

    function requestJson(url, options) {
        if (!window.fetch) {
            return requestJsonXhr(url, options);
        }
        return fetch(url, options || {}).then(function (response) {
            if (!response.ok) {
                return response.text().then(function (text) {
                    throw new Error(text || ("HTTP " + response.status));
                });
            }
            return response.json();
        });
    }

    function requestJsonXhr(url, options) {
        options = options || {};
        return new Promise(function (resolve, reject) {
            var xhr = new XMLHttpRequest();
            xhr.open(options.method || "GET", url, true);
            var headers = options.headers || {};
            Object.keys(headers).forEach(function (key) {
                xhr.setRequestHeader(key, headers[key]);
            });
            xhr.onload = function () {
                if (xhr.status < 200 || xhr.status >= 300) {
                    reject(new Error(xhr.responseText || ("HTTP " + xhr.status)));
                    return;
                }
                try {
                    resolve(JSON.parse(xhr.responseText || "{}"));
                } catch (error) {
                    reject(error);
                }
            };
            xhr.onerror = function () {
                reject(new Error("Network error"));
            };
            xhr.send(options.body || null);
        });
    }

    function formatBytes(value) {
        var bytes = Number(value || 0);
        if (!bytes) return "-";
        var units = ["B", "KB", "MB", "GB", "TB"];
        var size = bytes;
        var index = 0;
        while (size >= 1024 && index < units.length - 1) {
            size = size / 1024;
            index += 1;
        }
        return size.toFixed(index ? 1 : 0) + " " + units[index];
    }

    function formatDuration(value) {
        var seconds = Number(value || 0);
        if (!seconds) return "-";
        var hours = Math.floor(seconds / 3600);
        var minutes = Math.floor((seconds % 3600) / 60);
        return hours ? (hours + " h " + minutes + " min") : (minutes + " min");
    }

    function ratingBadge(value) {
        return '<span class="catalog-rating">' + Number(value || 0).toFixed(0) + '%</span>';
    }

    function providerBadge(provider) {
        var cls = provider === "webshare" ? "badge-ws" : "badge-fs";
        return '<span class="provider-badge ' + cls + '">' + escapeHtml(provider || "-") + '</span>';
    }

    function statusBadge(status) {
        var pending = status === "pending_delete";
        return '<span class="status-badge ' + (pending ? "status-pending" : "status-active") + '">' +
            (pending ? "ke vyřazení" : "aktivní") +
            '</span>';
    }

    function streamMetaLine(stream, includeDuration) {
        var parts = [
            escapeHtml(stream.format || "-"),
            formatBytes(stream.size),
            (stream.width || "-") + "x" + (stream.height || "-"),
        ];
        if (includeDuration) parts.push(formatDuration(stream.duration));
        return '<span class="stream-meta">' + parts.join(" · ") + '</span>';
    }

    function streamIdent(stream) {
        if (stream.ident && String(stream.ident).indexOf(":") > 0) return stream.ident;
        return (stream.provider || "") + ":" + (stream.provider_ident || stream.ident || "");
    }

    function resetSearchTableState() {
        searchSort = { key: "size", direction: "desc" };
        searchFilters = { provider: "", format: "", text: "", minSize: "", maxSize: "" };
    }

    function normalizeText(value) {
        return String(value || "").toLowerCase();
    }

    function parseSizeFilter(value) {
        var text = String(value || "").trim().replace(",", ".");
        var match;
        var amount;
        var unit;
        if (!text) return 0;
        match = text.match(/^(\d+(?:\.\d+)?)\s*(b|kb|mb|gb|tb)?$/i);
        if (!match) return 0;
        amount = Number(match[1] || 0);
        unit = String(match[2] || "gb").toLowerCase();
        if (unit === "tb") return amount * 1024 * 1024 * 1024 * 1024;
        if (unit === "gb") return amount * 1024 * 1024 * 1024;
        if (unit === "mb") return amount * 1024 * 1024;
        if (unit === "kb") return amount * 1024;
        return amount;
    }

    function streamResolution(stream) {
        if (!stream.width && !stream.height) return "-";
        return (stream.width || "-") + "x" + (stream.height || "-");
    }

    function uniqueStreamValues(streams, key) {
        var seen = {};
        var values = [];
        for (var i = 0; i < streams.length; i += 1) {
            var value = String(streams[i][key] || "").trim();
            if (!value || seen[value]) continue;
            seen[value] = true;
            values.push(value);
        }
        return values.sort(function (a, b) { return a.localeCompare(b); });
    }

    function searchSortLabel(key) {
        if (searchSort.key !== key) return "";
        return searchSort.direction === "asc" ? " ▲" : " ▼";
    }

    function searchSortButton(key, label) {
        if (!label) return "";
        return '<button type="button" class="sort-button" data-action="sort-search" data-key="' + escapeHtml(key) + '">' +
            escapeHtml(label + searchSortLabel(key)) +
            '</button>';
    }

    function filteredSearchEntries(streams) {
        var entries = [];
        var text = normalizeText(searchFilters.text);
        var minSize = parseSizeFilter(searchFilters.minSize);
        var maxSize = parseSizeFilter(searchFilters.maxSize);

        for (var i = 0; i < streams.length; i += 1) {
            var entry = streams[i] && streams[i].stream ? streams[i] : { stream: streams[i], index: i };
            var stream = entry.stream;
            var size = Number(stream.size || 0);
            if (searchFilters.provider && stream.provider !== searchFilters.provider) continue;
            if (searchFilters.format && String(stream.format || "") !== searchFilters.format) continue;
            if (text && normalizeText(stream.filename).indexOf(text) < 0) continue;
            if (minSize && size < minSize) continue;
            if (maxSize && size > maxSize) continue;
            entries.push(entry);
        }

        entries.sort(function (a, b) {
            var av = searchSortValue(a.stream, searchSort.key);
            var bv = searchSortValue(b.stream, searchSort.key);
            var result;
            if (typeof av === "number" || typeof bv === "number") {
                result = Number(av || 0) - Number(bv || 0);
            } else {
                result = String(av || "").localeCompare(String(bv || ""));
            }
            return searchSort.direction === "asc" ? result : -result;
        });
        return entries;
    }

    function searchSortValue(stream, key) {
        if (key === "selected") return 0;
        if (key === "provider") return stream.provider || "";
        if (key === "filename") return stream.filename || "";
        if (key === "format") return stream.format || "";
        if (key === "size") return Number(stream.size || 0);
        if (key === "resolution") return Number(stream.width || 0) * Number(stream.height || 0);
        if (key === "duration") return Number(stream.duration || 0);
        if (key === "season") return Number(stream.season || 999);
        if (key === "episode") return Number(stream.episode || 999);
        return "";
    }

    function updateSearchFilter(id, key) {
        var node = el(id);
        searchFilters[key] = node ? node.value : "";
    }

    function escapeHtml(value) {
        return String(value == null ? "" : value)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    function getCatalogFilter() {
        var input = el("catalogFilter");
        return input ? input.value.trim() : "";
    }

    function getTypeFilter() {
        var input = el("typeFilter");
        return input ? input.value : "all";
    }

    function renderSegmentedInput(id, value, options) {
        var html = '<input type="hidden" id="' + escapeHtml(id) + '" value="' + escapeHtml(value) + '">';
        html += '<div class="segmented" role="group">';
        for (var i = 0; i < options.length; i += 1) {
            var option = options[i];
            html += '<button type="button" class="option-button ' + (option.value === value ? "active" : "") + '" data-option-target="' +
                escapeHtml(id) + '" data-option-value="' + escapeHtml(option.value) + '">' + escapeHtml(option.label) + '</button>';
        }
        html += '</div>';
        return html;
    }

    function loadCatalog() {
        var q = getCatalogFilter();
        var query = "media_type=" + encodeURIComponent(getTypeFilter());
        if (q) query += "&q=" + encodeURIComponent(q);

        return requestJson(API_URL + "/catalog?" + query)
            .then(function (data) {
                catalogItems = data.data || [];
                renderCatalog();
                if (!selectedMediaId && catalogItems.length) {
                    return showDetail(catalogItems[0]._id);
                }
            })
            .catch(function (error) {
                console.error(error);
                showStatus("Nepodařilo se načíst katalog.", "error");
            });
    }

    function renderCatalog() {
        var container = el("catalogList");
        if (!container) return;

        if (!catalogItems.length) {
            container.innerHTML = '<div class="empty-list">Katalog je prázdný.</div>';
            return;
        }

        container.innerHTML = catalogItems.map(function (item) {
            var active = item._id === selectedMediaId ? "active" : "";
            var poster = item.poster || "";
            var typeLabel = item.type === "tvshow" ? "Seriál" : "Film";
            return '' +
                '<button class="catalog-item ' + active + '" data-action="detail" data-id="' + escapeHtml(item._id) + '">' +
                    '<div class="thumb">' + (poster ? '<img src="' + escapeHtml(poster) + '" alt="">' : "") + '</div>' +
                    '<div class="catalog-copy">' +
                        '<strong>' + escapeHtml(item.title) + '</strong>' +
                        '<span>' + typeLabel + ' · ' + (item.year || "-") + ' · ' + (item.stream_count || 0) + ' streamů</span>' +
                    '</div>' +
                    ratingBadge(item.rating) +
                '</button>';
        }).join("");
    }

    function searchMedia() {
        var input = el("searchInput");
        var type = el("searchType");
        var panel = el("searchPanel");
        var query = input ? input.value.trim() : "";
        var mediaType = type ? type.value : "movie";
        console.log("StreamCinema search click", query);
        if (!query) {
            showStatus("Zadej název filmu nebo seriálu.", "error");
            return;
        }

        setSearching(true);
        showStatus("Vyhledávám streamy a metadata...", "info");
        if (panel) {
            panel.classList.remove("hidden");
            panel.innerHTML = "";
        }

        requestJson(API_URL + "/search_json?q=" + encodeURIComponent(query) + "&media_type=" + encodeURIComponent(mediaType))
            .then(function (data) {
                resetSearchTableState();
                currentSearch = data;
                renderSearchResults();
                showStatus("", "info");
                setSearching(false);
            })
            .catch(function (error) {
                console.error(error);
                showStatus("Vyhledávání selhalo. Zkontroluj log add-onu.", "error");
                setSearching(false);
            });
    }

    function renderSearchResults() {
        var panel = el("searchPanel");
        if (!panel) return;

        var metadata = currentSearch ? currentSearch.metadata : null;
        var streams = currentSearch ? (currentSearch.streams || []) : [];
        if (!metadata) {
            panel.innerHTML = "";
            panel.classList.add("hidden");
            return;
        }

        var poster = metadata.poster || "";
        panel.innerHTML = '' +
            '<div class="search-header">' +
                '<div class="poster-small">' + (poster ? '<img src="' + escapeHtml(poster) + '" alt="">' : "") + '</div>' +
                '<div>' +
                    '<h2>' + escapeHtml(metadata.title) + '</h2>' +
                    '<p>' + (metadata.year || "-") + ' · ' + (metadata.type === "tvshow" ? "Seriál" : "Film") + ' · ' + (metadata.rating || 0) + '% · ' + String(metadata.source || "").toUpperCase() + '</p>' +
                    '<p>' + escapeHtml(metadata.plot || "Bez popisu.") + '</p>' +
                '</div>' +
            '</div>' +
            '<div class="stream-actions">' +
                '<label><input type="checkbox" id="selectAllStreams"> Vybrat vše</label>' +
                '<button type="button" data-action="save-selected">Zařadit vybrané do sbírky</button>' +
            '</div>' +
            renderSearchStreams(metadata.type, streams);

        panel.classList.remove("hidden");
    }

    function renderSearchStreams(mediaType, streams) {
        if (!streams.length) {
            return '<div class="empty-list">Nebyly nalezeny žádné streamy.</div>';
        }

        if (mediaType === "tvshow") {
            return renderSearchSeriesTables(streams);
        }

        return renderSearchStreamTable(streams, "");
    }

    function renderSearchSeriesTables(streams) {
        var grouped = {};
        var loose = [];
        var seasons;
        var html = '<h3>Série a díly</h3><div class="seasons search-seasons">';

        for (var i = 0; i < streams.length; i += 1) {
            var stream = streams[i];
            if (stream.season && stream.episode) {
                if (!grouped[stream.season]) grouped[stream.season] = {};
                if (!grouped[stream.season][stream.episode]) grouped[stream.season][stream.episode] = [];
                grouped[stream.season][stream.episode].push({ stream: stream, index: i });
            } else {
                loose.push({ stream: stream, index: i });
            }
        }

        seasons = Object.keys(grouped).sort(function (a, b) { return Number(a) - Number(b); });
        if (!seasons.length) {
            return '<h3>Neroztříděné streamy</h3>' + renderSearchStreamTable(streams, "loose");
        }

        for (var s = 0; s < seasons.length; s += 1) {
            var season = seasons[s];
            var episodes = Object.keys(grouped[season]).sort(function (a, b) { return Number(a) - Number(b); });
            html += '<details open><summary>Série ' + escapeHtml(season) + '</summary>';
            for (var e = 0; e < episodes.length; e += 1) {
                var episode = episodes[e];
                html += '<div class="episode-block"><h4>Díl ' + escapeHtml(episode) + '</h4>' +
                    renderSearchStreamTable(grouped[season][episode], "s" + season + "e" + episode) +
                    '</div>';
            }
            html += '</details>';
        }
        html += '</div>';
        if (loose.length) {
            html += '<h3>Neroztříděné streamy</h3>' + renderSearchStreamTable(loose, "loose");
        }
        return html;
    }

    function renderSearchStreamTable(streams, scope) {
        var normalizedEntries = streams.map(function (entry, position) {
            if (entry && entry.stream) return entry;
            return { stream: entry, index: position };
        });
        var scopeSuffix = scope ? "-" + scope : "";
        var streamValues = normalizedEntries.map(function (entry) { return entry.stream; });
        var originalCount = normalizedEntries.length;
        var formats = uniqueStreamValues(streamValues, "format");
        var providers = uniqueStreamValues(streamValues, "provider");
        var entries = filteredSearchEntries(normalizedEntries);
        var filterAttrs = scope ? ' data-filter-scope="' + escapeHtml(scope) + '"' : "";

        var html = '<div class="search-table-wrap"><table class="search-results-table">';
        html += '<thead>';
        html += '<tr>' +
            '<th class="check-col">' + searchSortButton("selected", "") + '</th>' +
            '<th>' + searchSortButton("provider", "Zdroj") + '</th>' +
            '<th>' + searchSortButton("filename", "Název") + '</th>' +
            '<th>' + searchSortButton("format", "Formát") + '</th>' +
            '<th>' + searchSortButton("size", "Velikost") + '</th>' +
            '<th>' + searchSortButton("resolution", "Rozlišení") + '</th>' +
            '<th>' + searchSortButton("duration", "Délka") + '</th>' +
            '<th>Akce</th>' +
            '</tr>';
        html += '<tr class="filter-row">' +
            '<th></th>' +
            '<th><select id="searchFilterProvider' + scopeSuffix + '" data-search-filter="provider"' + filterAttrs + '><option value="">Vše</option>' + providers.map(function (provider) {
                return '<option value="' + escapeHtml(provider) + '"' + (searchFilters.provider === provider ? " selected" : "") + '>' + escapeHtml(provider) + '</option>';
            }).join("") + '</select></th>' +
            '<th><input id="searchFilterText' + scopeSuffix + '" data-search-filter="text"' + filterAttrs + ' value="' + escapeHtml(searchFilters.text) + '" placeholder="Filtrovat název"></th>' +
            '<th><select id="searchFilterFormat' + scopeSuffix + '" data-search-filter="format"' + filterAttrs + '><option value="">Vše</option>' + formats.map(function (format) {
                return '<option value="' + escapeHtml(format) + '"' + (searchFilters.format === format ? " selected" : "") + '>' + escapeHtml(format) + '</option>';
            }).join("") + '</select></th>' +
            '<th><div class="size-filter"><input id="searchFilterMinSize' + scopeSuffix + '" data-search-filter="minSize"' + filterAttrs + ' value="' + escapeHtml(searchFilters.minSize) + '" placeholder="min GB"><input id="searchFilterMaxSize' + scopeSuffix + '" data-search-filter="maxSize"' + filterAttrs + ' value="' + escapeHtml(searchFilters.maxSize) + '" placeholder="max GB"></div></th>' +
            '<th></th>' +
            '<th></th>' +
            '<th><span class="result-count">' + entries.length + "/" + originalCount + '</span></th>' +
            '</tr>';
        html += '</thead><tbody>';
        if (!entries.length) {
            html += '<tr><td colspan="8" class="empty-table-cell">Filtr neodpovídá žádnému streamu.</td></tr>';
        } else {
            html += entries.map(function (entry) {
                var stream = entry.stream;
                var season = stream.season && stream.episode ? '<span class="episode-badge">S' + stream.season + ' E' + stream.episode + '</span>' : "";
                return '<tr>' +
                    '<td class="check-col"><input type="checkbox" class="search-stream-check" data-index="' + entry.index + '"></td>' +
                    '<td>' + providerBadge(stream.provider) + '</td>' +
                    '<td><strong>' + escapeHtml(stream.filename) + '</strong> ' + season + '</td>' +
                    '<td>' + escapeHtml(stream.format || "-") + '</td>' +
                    '<td class="numeric-cell" data-sort-value="' + Number(stream.size || 0) + '">' + formatBytes(stream.size) + '</td>' +
                    '<td>' + escapeHtml(streamResolution(stream)) + '</td>' +
                    '<td class="numeric-cell">' + formatDuration(stream.duration) + '</td>' +
                    '<td><button type="button" class="play-button compact-button" data-action="play-stream" data-ident="' + escapeHtml(streamIdent(stream)) + '" data-source-url="' + escapeHtml(stream.stream_url || "") + '" data-title="' + escapeHtml(stream.filename) + '">Přehrát</button></td>' +
                    '</tr>';
            }).join("");
        }
        html += '</tbody></table></div>';
        return html;
    }

    function toggleSearchStreams(checked) {
        var checks = document.querySelectorAll(".search-stream-check");
        for (var i = 0; i < checks.length; i += 1) {
            checks[i].checked = checked;
        }
    }

    function saveSelectedStreams() {
        var checks = document.querySelectorAll(".search-stream-check:checked");
        var streams = [];
        for (var i = 0; i < checks.length; i += 1) {
            streams.push(currentSearch.streams[Number(checks[i].getAttribute("data-index"))]);
        }

        if (!streams.length) {
            showStatus("Vyber alespoň jeden stream.", "error");
            return;
        }

        showStatus("Ukládám vybrané streamy...", "info");
        requestJson(API_URL + "/media", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ metadata: currentSearch.metadata, streams: streams }),
        })
            .then(function (media) {
                selectedMediaId = media._id;
                showStatus("Vybrané streamy byly zařazeny do sbírky.", "success");
                return loadCatalog().then(function () {
                    switchTab("collectionTab");
                    return showDetail(media._id);
                });
            })
            .catch(function (error) {
                console.error(error);
                showStatus("Uložení vybraných streamů selhalo.", "error");
            });
    }

    function showDetail(mediaId) {
        selectedMediaId = mediaId;
        renderCatalog();
        return requestJson(API_URL + "/media/" + encodeURIComponent(mediaId))
            .then(function (item) {
                renderDetail(item);
            })
            .catch(function (error) {
                console.error(error);
                showStatus("Detail se nepodařilo načíst.", "error");
            });
    }

    function renderDetail(item) {
        var poster = item.poster || "";
        var genres = (item.genres || []).join(", ");
        var panel = el("detailPanel");
        if (!panel) return;
        var isTvshow = item.type === "tvshow";

        panel.innerHTML = '' +
            '<div class="detail-head">' +
                '<div class="poster">' + (poster ? '<img src="' + escapeHtml(poster) + '" alt="">' : "") + '</div>' +
                '<div class="detail-meta">' +
                    '<div class="detail-title-row">' +
                        '<div>' +
                            '<h2>' + escapeHtml(item.title) + '</h2>' +
                            '<p>' + (item.year || "-") + ' · ' + (item.type === "tvshow" ? "Seriál" : "Film") + ' · ' + escapeHtml(genres) + '</p>' +
                        '</div>' +
                        '<strong class="rating">' + (item.rating || 0) + '%</strong>' +
                    '</div>' +
                    '<p class="plot">' + escapeHtml(item.plot || "Bez popisu.") + '</p>' +
                    '<div class="detail-actions">' +
                        '<button type="button" id="editMediaButton" data-action="open-media-edit">Upravit položku</button>' +
                        '<button type="button" class="danger" data-action="delete-media" data-id="' + escapeHtml(item._id) + '">Smazat položku</button>' +
                    '</div>' +
                '</div>' +
            '</div>' +
            '<section id="mediaEditForm" class="edit-form hidden">' +
                '<h3>Upravit položku</h3>' +
                '<div class="edit-grid">' +
                    '<label>Typ' + renderSegmentedInput("editType", isTvshow ? "tvshow" : "movie", [{ value: "movie", label: "Film" }, { value: "tvshow", label: "Seriál" }]) + '</label>' +
                    '<label>Hodnocení ČSFD (%)<input id="editRating" type="number" min="0" max="100" step="1" value="' + escapeHtml(item.rating || 0) + '"></label>' +
                    '<label>URL obrázku<input id="editPosterUrl" type="text" value="' + escapeHtml(poster) + '" placeholder="https://..."></label>' +
                    '<label>Vlastní obrázek<input id="editPosterFile" type="file" accept="image/*"></label>' +
                '</div>' +
                '<label>Popis<textarea id="editPlot" rows="5">' + escapeHtml(item.plot || "") + '</textarea></label>' +
                '<div class="edit-actions">' +
                    '<button type="button" data-action="save-media" data-id="' + escapeHtml(item._id) + '">Uložit změny</button>' +
                    '<button type="button" data-action="cancel-media-edit" data-id="' + escapeHtml(item._id) + '">Storno</button>' +
                '</div>' +
            '</section>' +
            renderStreamBulkActions(item) +
            (item.type === "tvshow" ? renderSeasons(item) : renderMovieStreams(item));
    }

    function openMediaEditForm() {
        var form = el("mediaEditForm");
        var button = el("editMediaButton");
        if (form) form.classList.remove("hidden");
        if (button) button.classList.add("hidden");
    }

    function cancelMediaEdit(mediaId) {
        var form = el("mediaEditForm");
        var button = el("editMediaButton");
        if (form) form.classList.add("hidden");
        if (button) button.classList.remove("hidden");
        if (mediaId) showDetail(mediaId);
    }

    function renderStreamBulkActions(item) {
        return '' +
            '<div class="stream-toolbar">' +
                '<button type="button" data-action="check-media" data-id="' + escapeHtml(item._id) + '">Kontrola</button>' +
                '<button type="button" class="danger" data-action="delete-pending" data-id="' + escapeHtml(item._id) + '">Vyřadit označené</button>' +
            '</div>';
    }

    function renderMovieStreams(item) {
        return '<section class="collection-streams">' +
            '<h3>Streamy</h3>' +
            renderStreams(item.streams || []) +
            '</section>';
    }

    function renderSeasons(item) {
        if (!item.seasons || !item.seasons.length) {
            return '<h3>Streamy</h3>' + renderStreams(item.streams || []);
        }

        var looseStreams = (item.streams || []).filter(function (stream) {
            return !stream.season || !stream.episode;
        });
        var html = '<h3>Série a díly</h3><div class="seasons">';
        html += item.seasons.map(function (season) {
            return '<details open><summary>Série ' + season.season + '</summary>' +
                season.episodes.map(function (episode) {
                    return '<div class="episode-block"><h4>Díl ' + episode.episode + '</h4>' + renderStreams(episode.streams) + '</div>';
                }).join("") +
                '</details>';
        }).join("");
        html += '</div>';
        if (looseStreams.length) {
            html += '<h3>Nezařazené streamy</h3>' + renderStreams(looseStreams);
        }
        return html;
    }

    function renderStreams(streams) {
        if (!streams.length) {
            return '<div class="empty-list">Žádné streamy.</div>';
        }

        return '<div class="stream-table">' + streams.map(function (stream) {
            var pending = stream.status === "pending_delete";
            return '' +
                '<div class="stream-row ' + (pending ? "pending" : "") + '">' +
                    '<input type="checkbox" class="collection-stream-check" value="' + stream.id + '">' +
                    '<div>' +
                        '<strong>' + escapeHtml(stream.filename) + '</strong>' +
                        '<span class="stream-badges">' + providerBadge(stream.provider) + statusBadge(stream.status) + streamMetaLine(stream, true) + '</span>' +
                        '<span>' + (stream.last_checked_at ? "Kontrola " + escapeHtml(stream.last_checked_at) : "Zatím bez kontroly") + '</span>' +
                    '</div>' +
                    '<div class="row-actions">' +
                        '<button type="button" class="play-button" data-action="play-stream" data-ident="' + escapeHtml(stream.ident) + '" data-source-url="' + escapeHtml(stream.stream_url || "") + '" data-title="' + escapeHtml(stream.filename) + '">Přehrát</button>' +
                        '<button type="button" data-action="check-stream" data-id="' + stream.id + '">Kontrola</button>' +
                        '<button type="button" class="danger" data-action="delete-stream" data-id="' + stream.id + '">Vyřadit</button>' +
                    '</div>' +
                '</div>';
        }).join("") + '</div>';
    }

    function ensurePlayerModal() {
        var modal = el("playerModal");
        if (modal) return modal;

        modal = document.createElement("section");
        modal.id = "playerModal";
        modal.className = "player-modal hidden";
        modal.innerHTML = '' +
            '<div class="player-dialog">' +
                '<div class="player-header">' +
                    '<strong id="playerTitle">Přehrávač</strong>' +
                    '<div class="player-actions">' +
                        '<button type="button" data-action="fullscreen-player">Celá obrazovka</button>' +
                        '<button type="button" data-action="close-player">Zavřít</button>' +
                    '</div>' +
                '</div>' +
                '<video id="streamPlayer" controls playsinline preload="metadata"></video>' +
                '<a id="playerOpenLink" class="button-link" target="_blank" rel="noreferrer">Otevřít link</a>' +
            '</div>';
        document.body.appendChild(modal);
        return modal;
    }

    function playStream(ident, title, sourceUrl) {
        if (!ident || ident.indexOf(":") < 1) {
            showStatus("Stream nemá identifikátor pro přehrání.", "error");
            return;
        }

        showStatus("Získávám stream link...", "info");
        var parts = ident.split(":");
        var provider = parts.shift();
        var fileIdent = parts.join(":");
        requestJson(API_URL + "/file_link/" + encodeURIComponent(provider) + ":" + encodeURIComponent(fileIdent))
            .then(function (data) {
                if (!data.link) {
                    showStatus("Provider nevrátil přímý stream link.", "error");
                    return;
                }
                if (sourceUrl && data.link.indexOf("api/stream_proxy/") === 0) {
                    data.link += "?url=" + encodeURIComponent(sourceUrl);
                }
                var modal = ensurePlayerModal();
                var player = el("streamPlayer");
                var titleNode = el("playerTitle");
                var openLink = el("playerOpenLink");
                titleNode.textContent = title || "Přehrávač";
                openLink.href = data.link;
                player.src = data.link;
                player.onerror = function () {
                    showStatus("Stream link se podařilo získat, ale přehrávač ho nedokázal načíst.", "error");
                };
                modal.className = "player-modal";
                showStatus("", "info");
                var playPromise = player.play();
                if (playPromise && playPromise.catch) {
                    playPromise.catch(function () {
                        showStatus("Přehrávač je připravený. Spusť ho tlačítkem Play.", "info");
                    });
                }
            })
            .catch(function (error) {
                console.error(error);
                showStatus("Nepodařilo se získat stream link.", "error");
            });
    }

    function closePlayer() {
        var modal = el("playerModal");
        var player = el("streamPlayer");
        if (player) {
            player.pause();
            player.removeAttribute("src");
            player.load();
        }
        if (modal) modal.className = "player-modal hidden";
    }

    function fullscreenPlayer() {
        var player = el("streamPlayer");
        if (!player) return;
        if (player.requestFullscreen) player.requestFullscreen();
        else if (player.webkitEnterFullscreen) player.webkitEnterFullscreen();
        else if (player.webkitRequestFullscreen) player.webkitRequestFullscreen();
    }

    function checkMediaStreams(mediaId) {
        showStatus("Kontroluji streamy...", "info");
        requestJson(API_URL + "/media/" + encodeURIComponent(mediaId) + "/check_streams", { method: "POST" })
            .then(function () {
                showStatus("Kontrola dokončena. Chybné streamy jsou označené k vyřazení.", "success");
                return showDetail(mediaId);
            })
            .catch(function (error) {
                console.error(error);
                showStatus("Kontrola streamů selhala.", "error");
            });
    }

    function checkStream(streamId) {
        requestJson(API_URL + "/streams/" + streamId + "/check", { method: "POST" })
            .then(function () {
                showStatus("Stream byl zkontrolován.", "success");
                return showDetail(selectedMediaId);
            })
            .catch(function (error) {
                console.error(error);
                showStatus("Kontrola streamu selhala.", "error");
            });
    }

    function deleteStream(streamId) {
        if (!confirm("Opravdu vyřadit tento stream?")) return;
        requestJson(API_URL + "/streams/" + streamId, { method: "DELETE" })
            .then(function () {
                showStatus("Stream byl vyřazen.", "success");
                return loadCatalog().then(function () {
                    return showDetail(selectedMediaId);
                });
            })
            .catch(function (error) {
                console.error(error);
                showStatus("Vyřazení streamu selhalo.", "error");
            });
    }

    function deletePendingStreams(mediaId) {
        var checks = document.querySelectorAll(".collection-stream-check:checked");
        var ids = [];
        for (var i = 0; i < checks.length; i += 1) {
            ids.push(Number(checks[i].value));
        }

        if (ids.length) {
            if (!confirm("Vyřadit vybrané streamy?")) return;
            requestJson(API_URL + "/media/" + encodeURIComponent(mediaId) + "/streams/delete_selected", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ stream_ids: ids }),
            })
                .then(function (result) {
                    showStatus("Vyřazeno streamů: " + (result.deleted || 0) + ".", "success");
                    return loadCatalog().then(function () {
                        return showDetail(mediaId);
                    });
                })
                .catch(function (error) {
                    console.error(error);
                    showStatus("Vyřazení vybraných streamů selhalo.", "error");
                });
            return;
        }

        if (!confirm("Nejsou vybrané žádné streamy. Vyřadit všechny streamy označené kontrolou jako chybné?")) return;
        requestJson(API_URL + "/media/" + encodeURIComponent(mediaId) + "/pending_streams", { method: "DELETE" })
            .then(function (result) {
                showStatus("Vyřazeno streamů: " + (result.deleted || 0) + ".", "success");
                return loadCatalog().then(function () {
                    return showDetail(mediaId);
                });
            })
            .catch(function (error) {
                console.error(error);
                showStatus("Vyřazení označených streamů selhalo.", "error");
            });
    }

    function readPosterValue() {
        var fileInput = el("editPosterFile");
        var urlInput = el("editPosterUrl");
        if (!fileInput || !fileInput.files || !fileInput.files.length) {
            return Promise.resolve(urlInput ? urlInput.value.trim() : "");
        }

        return new Promise(function (resolve, reject) {
            var reader = new FileReader();
            reader.onload = function () {
                resolve(String(reader.result || ""));
            };
            reader.onerror = function () {
                reject(new Error("Image read failed"));
            };
            reader.readAsDataURL(fileInput.files[0]);
        });
    }

    function saveMediaEdits(mediaId) {
        var type = el("editType");
        var plot = el("editPlot");
        var rating = el("editRating");
        showStatus("Ukládám změny položky...", "info");
        readPosterValue()
            .then(function (poster) {
                return requestJson(API_URL + "/media/" + encodeURIComponent(mediaId), {
                    method: "PUT",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        type: type ? type.value : "movie",
                        rating: rating ? rating.value : 0,
                        plot: plot ? plot.value : "",
                        poster: poster,
                    }),
                });
            })
            .then(function (media) {
                selectedMediaId = media._id;
                showStatus("Položka byla upravena.", "success");
                return loadCatalog().then(function () {
                    return showDetail(media._id);
                });
            })
            .catch(function (error) {
                console.error(error);
                showStatus("Uložení změn položky selhalo.", "error");
            });
    }

    function deleteMedia(mediaId) {
        if (!confirm("Opravdu smazat celou položku ze sbírky včetně všech streamů?")) return;
        requestJson(API_URL + "/media/" + encodeURIComponent(mediaId), { method: "DELETE" })
            .then(function () {
                selectedMediaId = null;
                showStatus("Položka byla smazána.", "success");
                var panel = el("detailPanel");
                if (panel) panel.innerHTML = '<div class="empty-state">Vyber položku ze sbírky.</div>';
                return loadCatalog();
            })
            .catch(function (error) {
                console.error(error);
                showStatus("Smazání položky selhalo.", "error");
            });
    }

    function switchTab(tabId) {
        var pages = document.querySelectorAll(".tab-page");
        var buttons = document.querySelectorAll(".tab-button");
        for (var i = 0; i < pages.length; i += 1) {
            pages[i].className = pages[i].id === tabId ? "tab-page active" : "tab-page";
        }
        for (var j = 0; j < buttons.length; j += 1) {
            buttons[j].className = buttons[j].getAttribute("data-tab") === tabId ? "tab-button active" : "tab-button";
        }
    }

    function handleClick(event) {
        var target = closestAction(event.target);
        if (!target) return;
        var action = target.getAttribute("data-action");
        var id = target.getAttribute("data-id");

        if (action === "detail") showDetail(id);
        if (action === "save-selected") saveSelectedStreams();
        if (action === "sort-search") {
            event.preventDefault();
            sortSearchResults(target.getAttribute("data-key"));
        }
        if (action === "check-media") checkMediaStreams(id);
        if (action === "delete-pending") deletePendingStreams(id);
        if (action === "check-stream") checkStream(id);
        if (action === "delete-stream") deleteStream(id);
        if (action === "open-media-edit") openMediaEditForm();
        if (action === "cancel-media-edit") cancelMediaEdit(id || selectedMediaId);
        if (action === "save-media") saveMediaEdits(id);
        if (action === "delete-media") deleteMedia(id);
        if (action === "play-stream") {
            event.preventDefault();
            playStream(target.getAttribute("data-ident"), target.getAttribute("data-title"), target.getAttribute("data-source-url"));
        }
        if (action === "close-player") closePlayer();
        if (action === "fullscreen-player") fullscreenPlayer();
    }

    function sortSearchResults(key) {
        if (!key || key === "selected") return;
        if (searchSort.key === key) {
            searchSort.direction = searchSort.direction === "asc" ? "desc" : "asc";
        } else {
            searchSort.key = key;
            searchSort.direction = key === "size" || key === "resolution" || key === "duration" ? "desc" : "asc";
        }
        renderSearchResults();
    }

    function refreshSearchAfterFilter(inputId, scope) {
        var selector = scope ? '[data-filter-scope="' + scope + '"]' : "";
        var node = scope ? document.querySelector("#" + inputId + selector) : el(inputId);
        var start = node && typeof node.selectionStart === "number" ? node.selectionStart : null;
        var end = node && typeof node.selectionEnd === "number" ? node.selectionEnd : null;
        renderSearchResults();
        node = scope ? document.querySelector("#" + inputId + selector) : el(inputId);
        if (!node) return;
        node.focus();
        if (start !== null && node.setSelectionRange) {
            node.setSelectionRange(start, end);
        }
    }

    function setOption(targetId, value) {
        var input = el(targetId);
        if (!input) return;
        input.value = value;

        var buttons = document.querySelectorAll('[data-option-target="' + targetId + '"]');
        for (var i = 0; i < buttons.length; i += 1) {
            buttons[i].className = buttons[i].getAttribute("data-option-value") === value ? "option-button active" : "option-button";
        }

        var event;
        if (typeof Event === "function") {
            event = new Event("change", { bubbles: true });
        } else {
            event = document.createEvent("Event");
            event.initEvent("change", true, true);
        }
        input.dispatchEvent(event);
    }

    function closestAction(node) {
        while (node && node !== document) {
            if (node.getAttribute && node.getAttribute("data-action")) return node;
            node = node.parentNode;
        }
        return null;
    }

    function init() {
        window.streamCinemaSearch = function (event) {
            if (event && event.preventDefault) event.preventDefault();
            searchMedia();
            return false;
        };

        showStatus("GUI načteno.", "success");
        var searchForm = el("searchForm");
        var searchInput = el("searchInput");
        var typeFilter = el("typeFilter");
        var catalogFilter = el("catalogFilter");

        if (searchForm) {
            searchForm.addEventListener("submit", function (event) {
                event.preventDefault();
                searchMedia();
            });
        }
        if (searchInput) {
            searchInput.addEventListener("keydown", function (event) {
                if (event.key === "Enter") searchMedia();
            });
        }
        if (typeFilter) typeFilter.addEventListener("change", loadCatalog);
        if (catalogFilter) catalogFilter.addEventListener("input", loadCatalog);

        document.addEventListener("click", handleClick);
        document.addEventListener("click", function (event) {
            var target = event.target;
            if (!target || !target.getAttribute || !target.getAttribute("data-option-target")) return;
            setOption(target.getAttribute("data-option-target"), target.getAttribute("data-option-value"));
        });
        var tabs = document.querySelectorAll(".tab-button");
        for (var i = 0; i < tabs.length; i += 1) {
            tabs[i].addEventListener("click", function () {
                switchTab(this.getAttribute("data-tab"));
            });
        }
        document.addEventListener("change", function (event) {
            if (event.target && event.target.id === "selectAllStreams") {
                toggleSearchStreams(event.target.checked);
            }
            if (event.target && event.target.getAttribute && event.target.getAttribute("data-search-filter")) {
                updateSearchFilter(event.target.id, event.target.getAttribute("data-search-filter"));
                refreshSearchAfterFilter(event.target.id, event.target.getAttribute("data-filter-scope"));
            }
        });
        document.addEventListener("input", function (event) {
            if (event.target && event.target.getAttribute && event.target.getAttribute("data-search-filter")) {
                updateSearchFilter(event.target.id, event.target.getAttribute("data-search-filter"));
                refreshSearchAfterFilter(event.target.id, event.target.getAttribute("data-filter-scope"));
            }
        });

        loadCatalog();
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
}());
