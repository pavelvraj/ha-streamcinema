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
        var select = el("typeFilter");
        return select ? select.value : "all";
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
                    '<div>' +
                        '<strong>' + escapeHtml(item.title) + '</strong>' +
                        '<span>' + typeLabel + ' · ' + (item.year || "-") + ' · ' + (item.stream_count || 0) + ' streamů</span>' +
                    '</div>' +
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
            panel.classList.add("hidden");
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
            '<div class="stream-table">' + renderSearchStreamRows(streams) + '</div>';

        panel.classList.remove("hidden");
    }

    function renderSearchStreamRows(streams) {
        if (!streams.length) {
            return '<div class="empty-list">Nebyly nalezeny žádné streamy.</div>';
        }

        return streams.map(function (stream, index) {
            var season = stream.season && stream.episode ? '<span>S' + stream.season + ' E' + stream.episode + '</span>' : "";
            return '' +
                '<label class="stream-row selectable">' +
                    '<input type="checkbox" class="search-stream-check" data-index="' + index + '">' +
                    '<div>' +
                        '<strong>' + escapeHtml(stream.filename) + '</strong>' +
                        '<span>' + escapeHtml(stream.provider) + ' · ' + escapeHtml(stream.format || "-") + ' · ' + formatBytes(stream.size) + ' · ' + (stream.width || "-") + 'x' + (stream.height || "-") + '</span>' +
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
                el("searchPanel").classList.add("hidden");
                showStatus("Vybrané streamy byly zařazeny do sbírky.", "success");
                return loadCatalog().then(function () {
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
                    '</div>' +
                '</div>' +
            '</div>' +
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
                    '<div>' +
                        '<strong>' + escapeHtml(stream.filename) + '</strong>' +
                        '<span>' + escapeHtml(stream.provider) + ' · ' + escapeHtml(stream.format || "-") + ' · ' + formatBytes(stream.size) + ' · ' + (stream.width || "-") + 'x' + (stream.height || "-") + ' · ' + formatDuration(stream.duration) + '</span>' +
                        '<span>Stav: ' + (pending ? "označeno k vyřazení" : "aktivní") + (stream.last_checked_at ? " · kontrola " + escapeHtml(stream.last_checked_at) : "") + '</span>' +
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
        if (!confirm("Vyřadit všechny streamy označené ke smazání?")) return;
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
