const API_URL = "api";

function setLoading(isLoading) {
    document.getElementById("loading").classList.toggle("hidden", !isLoading);
}

function showError(message) {
    const error = document.getElementById("error");
    error.textContent = message || "";
    error.classList.toggle("hidden", !message);
}

async function fetchJson(url) {
    const response = await fetch(url);
    if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
    }
    return response.json();
}

async function searchMedia() {
    const query = document.getElementById("searchInput").value.trim();
    if (!query) {
        return;
    }

    setLoading(true);
    showError("");
    document.getElementById("results").innerHTML = "";

    try {
        await fetchJson(`${API_URL}/search_manual?q=${encodeURIComponent(query)}`);
        const listData = await fetchJson(
            `${API_URL}/media/movies/filter/titleOrActor/${encodeURIComponent(query)}/`
        );
        renderResults(listData.data || []);
    } catch (error) {
        console.error("Search failed:", error);
        showError("Chyba pri komunikaci s API. Zkontroluj log add-onu.");
    } finally {
        setLoading(false);
    }
}

function renderResults(items) {
    const container = document.getElementById("results");

    if (!items.length) {
        container.innerHTML = "<p>Nebylo nic nalezeno.</p>";
        return;
    }

    for (const item of items) {
        const card = document.createElement("div");
        card.className = "media-card";

        const streams = item.streams || [];
        const wsCount = streams.filter((s) => s.ident.startsWith("webshare:")).length;
        const fsCount = streams.filter((s) => s.ident.startsWith("fastshare:")).length;
        const posterUrl = item.art?.poster || "https://via.placeholder.com/200x300?text=No+Poster";
        const title = item.info_labels?.title || "Bez nazvu";
        const year = item.info_labels?.year || "";
        const rating = item.info_labels?.rating || 0;

        card.innerHTML = `
            <img src="${posterUrl}" class="media-poster" alt="">
            <div class="media-info">
                <div class="media-title" title="${title}">${title}</div>
                <div class="media-meta">
                    <span>${year}</span>
                    <span>* ${rating}</span>
                </div>
                <div class="provider-row">
                    ${wsCount ? `<span class="provider-badge badge-ws">WS: ${wsCount}</span>` : ""}
                    ${fsCount ? `<span class="provider-badge badge-fs">FS: ${fsCount}</span>` : ""}
                </div>
            </div>
        `;

        card.addEventListener("click", () => showDetail(item));
        container.appendChild(card);
    }
}

function showDetail(item) {
    const title = item.info_labels?.title || "Bez nazvu";
    const streams = item.streams || [];
    alert(`Vybran: ${title}\nPocet streamu: ${streams.length}`);
}

document.getElementById("searchInput").addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
        searchMedia();
    }
});
