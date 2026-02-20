const API_URL = "/api";

async function searchMedia() {
    const query = document.getElementById('searchInput').value;
    if (!query) return;

    document.getElementById('loading').classList.remove('hidden');
    document.getElementById('results').innerHTML = '';

    try {
        // Zavoláme manuální search, který spustí scrapery
        const response = await fetch(`${API_URL}/search_manual?q=${encodeURIComponent(query)}`);
        const data = await response.json();

        // Teď načteme výsledky z DB (protože search_manual vrací jen status)
        // Voláme standardní filter endpoint, který vrací formátovaná data
        const listResponse = await fetch(`${API_URL}/media/movies/filter/titleOrActor/${encodeURIComponent(query)}/`);
        const listData = await listResponse.json();

        renderResults(listData.data);
    } catch (error) {
        console.error("Chyba při hledání:", error);
        alert("Chyba při komunikaci s API");
    } finally {
        document.getElementById('loading').classList.add('hidden');
    }
}

function renderResults(items) {
    const container = document.getElementById('results');
    
    if (items.length === 0) {
        container.innerHTML = '<p>Nebylo nic nalezeno.</p>';
        return;
    }

    items.forEach(item => {
        const card = document.createElement('div');
        card.className = 'media-card';
        
        // Získáme streamy pro badge
        const wsCount = item.streams.filter(s => s.ident.startsWith('webshare')).length;
        const fsCount = item.streams.filter(s => s.ident.startsWith('fastshare')).length;

        const posterUrl = item.art.poster || 'https://via.placeholder.com/200x300?text=No+Poster';

        card.innerHTML = `
            <img src="${posterUrl}" class="media-poster" alt="${item.info_labels.title}">
            <div class="media-info">
                <div class="media-title" title="${item.info_labels.title}">${item.info_labels.title}</div>
                <div class="media-meta">
                    <span>${item.info_labels.year || ''}</span>
                    <span>★ ${item.info_labels.rating || 0}</span>
                </div>
                <div style="margin-top: 10px;">
                    ${wsCount > 0 ? `<span class="provider-badge badge-ws">WS: ${wsCount}</span>` : ''}
                    ${fsCount > 0 ? `<span class="provider-badge badge-fs">FS: ${fsCount}</span>` : ''}
                </div>
            </div>
        `;
        
        // Po kliknutí by se mohl otevřít detail (to můžeme dodělat příště)
        card.onclick = () => showDetail(item);
        
        container.appendChild(card);
    });
}

function showDetail(item) {
    console.log("Kliknuto na:", item);
    // Zde můžeš implementovat modální okno s detaily streamů, možností smazat, atd.
    alert(`Vybrán: ${item.info_labels.title}\nPočet streamů: ${item.streams.length}`);
}

// Spustit hledání po stisku Enter
document.getElementById('searchInput').addEventListener('keypress', function (e) {
    if (e.key === 'Enter') {
        searchMedia();
    }
});
