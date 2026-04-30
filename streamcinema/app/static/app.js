(function () {
    var API_URL = "api";
    var catalogItems = [];
    var currentSearch = null;
    var selectedMediaId = null;

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
        if (mediaType !== "tvshow") {
            return '<div class="stream-table">' + renderSearchStreamRows(streams) + '</div>';
        }

        var grouped = {};
        var loose = [];
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

        var seasons = Object.keys(grouped).sort(function (a, b) { return Number(a) - Number(b); });
        if (!seasons.length) {
            return '<h3>Neroztříděné streamy</h3><div class="stream-table">' + renderSearchStreamRows(streams) + '</div>';
        }

        var html = '<h3>Série a díly</h3><div class="seasons">';
        for (var s = 0; s < seasons.length; s += 1) {
            var season = seasons[s];
            var episodes = Object.keys(grouped[season]).sort(function (a, b) { return Number(a) - Number(b); });
            html += '<details open><summary>Série ' + escapeHtml(season) + '</summary>';
            for (var e = 0; e < episodes.length; e += 1) {
                var episode = episodes[e];
                html += '<div class="episode-block"><h4>Díl ' + escapeHtml(episode) + '</h4>' +
                    '<div class="stream-table">' + renderSearchStreamRows(grouped[season][episode]) + '</div></div>';
            }
            html += '</details>';
        }
        html += '</div>';
        if (loose.length) {
            html += '<h3>Neroztříděné streamy</h3><div class="stream-table">' + renderSearchStreamRows(loose) + '</div>';
        }
        return html;
    }

    function renderSearchStreamRows(streams) {
        if (!streams.length) {
            return '<div class="empty-list">Nebyly nalezeny žádné streamy.</div>';
        }

        return streams.map(function (entry, position) {
            var stream = entry.stream || entry;
            var index = entry.index != null ? entry.index : position;
            var season = stream.season && stream.episode ? '<span>S' + stream.season + ' E' + stream.episode + '</span>' : "";
            return '' +
                '<label class="stream-row selectable">' +
                    '<input type="checkbox" class="search-stream-check" data-index="' + index + '">' +
                    '<div>' +
                        '<strong>' + escapeHtml(stream.filename) + '</strong>' +
                        '<span class="stream-badges">' + providerBadge(stream.provider) + '</span>' +
                        '<span>' + escapeHtml(stream.format || "-") + ' · ' + formatBytes(stream.size) + ' · ' + (stream.width || "-") + 'x' + (stream.height || "-") + '</span>' +
                        season +
                    '</div>' +
                '</label>';
        }).join("");
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
                        '<button type="button" data-action="check-media" data-id="' + escapeHtml(item._id) + '">Kontrola</button>' +
                        '<button type="button" class="danger" data-action="delete-pending" data-id="' + escapeHtml(item._id) + '">Vyřadit označené</button>' +
                        '<button type="button" class="danger" data-action="delete-media" data-id="' + escapeHtml(item._id) + '">Smazat položku</button>' +
                    '</div>' +
                '</div>' +
            '</div>' +
            '<section class="edit-form">' +
                '<h3>Upravit položku</h3>' +
                '<div class="edit-grid">' +
                    '<label>Typ' + renderSegmentedInput("editType", isTvshow ? "tvshow" : "movie", [{ value: "movie", label: "Film" }, { value: "tvshow", label: "Seriál" }]) + '</label>' +
                    '<label>Hodnocení ČSFD (%)<input id="editRating" type="number" min="0" max="100" step="1" value="' + escapeHtml(item.rating || 0) + '"></label>' +
                    '<label>URL obrázku<input id="editPosterUrl" type="text" value="' + escapeHtml(poster) + '" placeholder="https://..."></label>' +
                    '<label>Vlastní obrázek<input id="editPosterFile" type="file" accept="image/*"></label>' +
                '</div>' +
                '<label>Popis<textarea id="editPlot" rows="5">' + escapeHtml(item.plot || "") + '</textarea></label>' +
                '<button type="button" data-action="save-media" data-id="' + escapeHtml(item._id) + '">Uložit změny</button>' +
            '</section>' +
            (item.type === "tvshow" ? renderSeasons(item) : renderStreams(item.streams || []));
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
                        '<span class="stream-badges">' + providerBadge(stream.provider) + statusBadge(stream.status) + '</span>' +
                        '<span>' + escapeHtml(stream.format || "-") + ' · ' + formatBytes(stream.size) + ' · ' + (stream.width || "-") + 'x' + (stream.height || "-") + ' · ' + formatDuration(stream.duration) + '</span>' +
                        '<span>' + (stream.last_checked_at ? "Kontrola " + escapeHtml(stream.last_checked_at) : "Zatím bez kontroly") + '</span>' +
                    '</div>' +
                    '<div class="row-actions">' +
                        '<button type="button" data-action="check-stream" data-id="' + stream.id + '">Kontrola</button>' +
                        '<button type="button" class="danger" data-action="delete-stream" data-id="' + stream.id + '">Vyřadit</button>' +
                    '</div>' +
                '</div>';
        }).join("") + '</div>';
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
        if (action === "check-media") checkMediaStreams(id);
        if (action === "delete-pending") deletePendingStreams(id);
        if (action === "check-stream") checkStream(id);
        if (action === "delete-stream") deleteStream(id);
        if (action === "save-media") saveMediaEdits(id);
        if (action === "delete-media") deleteMedia(id);
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
        });

        loadCatalog();
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
}());
