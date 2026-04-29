const API_URL = "api";

let catalogItems = [];
let currentSearch = null;
let selectedMediaId = null;

function $(id) {
    return document.getElementById(id);
}

function showStatus(message, type = "info") {
    const node = $("status");
    node.textContent = message || "";
    node.className = message ? `status ${type}` : "status hidden";
}

async function fetchJson(url, options = {}) {
    const response = await fetch(url, options);
    if (!response.ok) {
        const text = await response.text();
        throw new Error(text || `HTTP ${response.status}`);
    }
    return response.json();
}

function formatBytes(value) {
    const bytes = Number(value || 0);
    if (!bytes) return "-";
    const units = ["B", "KB", "MB", "GB", "TB"];
    let size = bytes;
    let index = 0;
    while (size >= 1024 && index < units.length - 1) {
        size /= 1024;
        index += 1;
    }
    return `${size.toFixed(index ? 1 : 0)} ${units[index]}`;
}

function formatDuration(value) {
    const seconds = Number(value || 0);
    if (!seconds) return "-";
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    return hours ? `${hours} h ${minutes} min` : `${minutes} min`;
}

function escapeHtml(value) {
    return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}

async function loadCatalog() {
    const q = $("catalogFilter")?.value.trim() || "";
    const mediaType = $("typeFilter")?.value || "all";
    const params = new URLSearchParams({ media_type: mediaType });
    if (q) params.set("q", q);

    try {
        const data = await fetchJson(`${API_URL}/catalog?${params.toString()}`);
        catalogItems = data.data || [];
        renderCatalog();
        if (!selectedMediaId && catalogItems.length) {
            showDetail(catalogItems[0]._id);
        }
    } catch (error) {
        console.error(error);
        showStatus("Nepodařilo se načíst katalog.", "error");
    }
}

function renderCatalog() {
    const container = $("catalogList");
    if (!catalogItems.length) {
        container.innerHTML = `<div class="empty-list">Katalog je prázdný.</div>`;
        return;
    }

    container.innerHTML = catalogItems.map((item) => {
        const active = item._id === selectedMediaId ? "active" : "";
        const poster = item.poster || "";
        const typeLabel = item.type === "tvshow" ? "Seriál" : "Film";
        return `
            <button class="catalog-item ${active}" onclick="showDetail('${escapeHtml(item._id)}')">
                <div class="thumb">${poster ? `<img src="${escapeHtml(poster)}" alt="">` : ""}</div>
                <div>
                    <strong>${escapeHtml(item.title)}</strong>
                    <span>${typeLabel} · ${item.year || "-"} · ${item.stream_count || 0} streamů</span>
                </div>
            </button>
        `;
    }).join("");
}

async function searchMedia() {
    const query = $("searchInput").value.trim();
    if (!query) return;

    showStatus("Vyhledávám streamy a metadata...", "info");
    $("searchPanel").classList.add("hidden");
    $("searchPanel").innerHTML = "";

    try {
        currentSearch = await fetchJson(`${API_URL}/search?q=${encodeURIComponent(query)}`);
        renderSearchResults();
        showStatus("", "info");
    } catch (error) {
        console.error(error);
        showStatus("Vyhledávání selhalo. Zkontroluj log add-onu.", "error");
    }
}

function renderSearchResults() {
    const panel = $("searchPanel");
    const metadata = currentSearch?.metadata;
    const streams = currentSearch?.streams || [];
    if (!metadata) {
        panel.innerHTML = "";
        panel.classList.add("hidden");
        return;
    }

    const poster = metadata.poster || "";
    panel.innerHTML = `
        <div class="search-header">
            <div class="poster-small">${poster ? `<img src="${escapeHtml(poster)}" alt="">` : ""}</div>
            <div>
                <h2>${escapeHtml(metadata.title)}</h2>
                <p>${metadata.year || "-"} · ${metadata.type === "tvshow" ? "Seriál" : "Film"} · ${metadata.rating || 0}% · ${metadata.source.toUpperCase()}</p>
                <p>${escapeHtml(metadata.plot || "Bez popisu.")}</p>
            </div>
        </div>
        <div class="stream-actions">
            <label><input type="checkbox" id="selectAllStreams" onchange="toggleSearchStreams(this.checked)"> Vybrat vše</label>
            <button type="button" onclick="saveSelectedStreams()">Zařadit vybrané do sbírky</button>
        </div>
        <div class="stream-table">${renderSearchStreamRows(streams)}</div>
    `;
    panel.classList.remove("hidden");
}

function renderSearchStreamRows(streams) {
    if (!streams.length) {
        return `<div class="empty-list">Nebyly nalezeny žádné streamy.</div>`;
    }

    return streams.map((stream, index) => `
        <label class="stream-row selectable">
            <input type="checkbox" class="search-stream-check" data-index="${index}">
            <div>
                <strong>${escapeHtml(stream.filename)}</strong>
                <span>${escapeHtml(stream.provider)} · ${escapeHtml(stream.format || "-")} · ${formatBytes(stream.size)} · ${stream.width || "-"}x${stream.height || "-"}</span>
                ${stream.season && stream.episode ? `<span>S${stream.season} E${stream.episode}</span>` : ""}
            </div>
        </label>
    `).join("");
}

function toggleSearchStreams(checked) {
    document.querySelectorAll(".search-stream-check").forEach((node) => {
        node.checked = checked;
    });
}

async function saveSelectedStreams() {
    const checks = [...document.querySelectorAll(".search-stream-check:checked")];
    const streams = checks.map((node) => currentSearch.streams[Number(node.dataset.index)]);
    if (!streams.length) {
        showStatus("Vyber alespoň jeden stream.", "error");
        return;
    }

    try {
        const media = await fetchJson(`${API_URL}/media`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ metadata: currentSearch.metadata, streams }),
        });
        selectedMediaId = media._id;
        $("searchPanel").classList.add("hidden");
        showStatus("Vybrané streamy byly zařazeny do sbírky.", "success");
        await loadCatalog();
        await showDetail(media._id);
    } catch (error) {
        console.error(error);
        showStatus("Uložení vybraných streamů selhalo.", "error");
    }
}

async function showDetail(mediaId) {
    selectedMediaId = mediaId;
    renderCatalog();
    try {
        const item = await fetchJson(`${API_URL}/media/${encodeURIComponent(mediaId)}`);
        renderDetail(item);
    } catch (error) {
        console.error(error);
        showStatus("Detail se nepodařilo načíst.", "error");
    }
}

function renderDetail(item) {
    const poster = item.poster || "";
    const genres = (item.genres || []).join(", ");
    $("detailPanel").innerHTML = `
        <div class="detail-head">
            <div class="poster">${poster ? `<img src="${escapeHtml(poster)}" alt="">` : ""}</div>
            <div class="detail-meta">
                <div class="detail-title-row">
                    <div>
                        <h2>${escapeHtml(item.title)}</h2>
                        <p>${item.year || "-"} · ${item.type === "tvshow" ? "Seriál" : "Film"} · ${escapeHtml(genres)}</p>
                    </div>
                    <strong class="rating">${item.rating || 0}%</strong>
                </div>
                <p class="plot">${escapeHtml(item.plot || "Bez popisu.")}</p>
                <div class="detail-actions">
                    <button type="button" onclick="checkMediaStreams('${escapeHtml(item._id)}')">Kontrola</button>
                    <button type="button" class="danger" onclick="deletePendingStreams('${escapeHtml(item._id)}')">Vyřadit označené</button>
                </div>
            </div>
        </div>
        ${item.type === "tvshow" ? renderSeasons(item) : renderStreams(item.streams || [])}
    `;
}

function renderSeasons(item) {
    if (!item.seasons?.length) {
        return `
            <h3>Streamy</h3>
            ${renderStreams(item.streams || [])}
        `;
    }

    const looseStreams = (item.streams || []).filter((stream) => !stream.season || !stream.episode);
    return `
        <h3>Série a díly</h3>
        <div class="seasons">
            ${item.seasons.map((season) => `
                <details open>
                    <summary>Série ${season.season}</summary>
                    ${season.episodes.map((episode) => `
                        <div class="episode-block">
                            <h4>Díl ${episode.episode}</h4>
                            ${renderStreams(episode.streams)}
                        </div>
                    `).join("")}
                </details>
            `).join("")}
        </div>
        ${looseStreams.length ? `<h3>Nezařazené streamy</h3>${renderStreams(looseStreams)}` : ""}
    `;
}

function renderStreams(streams) {
    if (!streams.length) {
        return `<div class="empty-list">Žádné streamy.</div>`;
    }

    return `
        <div class="stream-table">
            ${streams.map((stream) => `
                <div class="stream-row ${stream.status === "pending_delete" ? "pending" : ""}">
                    <div>
                        <strong>${escapeHtml(stream.filename)}</strong>
                        <span>${escapeHtml(stream.provider)} · ${escapeHtml(stream.format || "-")} · ${formatBytes(stream.size)} · ${stream.width || "-"}x${stream.height || "-"} · ${formatDuration(stream.duration)}</span>
                        <span>Stav: ${stream.status === "pending_delete" ? "označeno k vyřazení" : "aktivní"}${stream.last_checked_at ? ` · kontrola ${escapeHtml(stream.last_checked_at)}` : ""}</span>
                    </div>
                    <div class="row-actions">
                        <button type="button" onclick="checkStream(${stream.id})">Kontrola</button>
                        <button type="button" class="danger" onclick="deleteStream(${stream.id})">Vyřadit</button>
                    </div>
                </div>
            `).join("")}
        </div>
    `;
}

async function checkMediaStreams(mediaId) {
    showStatus("Kontroluji streamy...", "info");
    try {
        await fetchJson(`${API_URL}/media/${encodeURIComponent(mediaId)}/check_streams`, { method: "POST" });
        showStatus("Kontrola dokončena. Chybné streamy jsou označené k vyřazení.", "success");
        await showDetail(mediaId);
    } catch (error) {
        console.error(error);
        showStatus("Kontrola streamů selhala.", "error");
    }
}

async function checkStream(streamId) {
    try {
        await fetchJson(`${API_URL}/streams/${streamId}/check`, { method: "POST" });
        showStatus("Stream byl zkontrolován.", "success");
        await showDetail(selectedMediaId);
    } catch (error) {
        console.error(error);
        showStatus("Kontrola streamu selhala.", "error");
    }
}

async function deleteStream(streamId) {
    if (!confirm("Opravdu vyřadit tento stream?")) return;
    try {
        await fetchJson(`${API_URL}/streams/${streamId}`, { method: "DELETE" });
        showStatus("Stream byl vyřazen.", "success");
        await loadCatalog();
        await showDetail(selectedMediaId);
    } catch (error) {
        console.error(error);
        showStatus("Vyřazení streamu selhalo.", "error");
    }
}

async function deletePendingStreams(mediaId) {
    if (!confirm("Vyřadit všechny streamy označené ke smazání?")) return;
    try {
        const result = await fetchJson(`${API_URL}/media/${encodeURIComponent(mediaId)}/pending_streams`, { method: "DELETE" });
        showStatus(`Vyřazeno streamů: ${result.deleted || 0}.`, "success");
        await loadCatalog();
        await showDetail(mediaId);
    } catch (error) {
        console.error(error);
        showStatus("Vyřazení označených streamů selhalo.", "error");
    }
}

$("searchInput").addEventListener("keydown", (event) => {
    if (event.key === "Enter") searchMedia();
});

loadCatalog();
