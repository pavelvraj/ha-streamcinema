import requests
from bs4 import BeautifulSoup
import re

class CSFDScraper:
    BASE = "https://www.csfd.cz"

    def search(self, title, year=None):
        """Vrátí seznam výsledků hledání z ČSFD"""
        params = {"q": title, "origin": "search-top"}
        r = requests.get(f"{self.BASE}/hledat/", params=params,
                         headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(r.text, "lxml")
        results = []
        for item in soup.select(".film-list-content article")[:5]:
            link = item.select_one("a.film-title-name")
            csfd_id = re.search(r"/film/(\d+)", link["href"]).group(1) if link else None
            results.append({
                "csfd_id": csfd_id,
                "title": link.text.strip() if link else "",
                "url": self.BASE + link["href"] if link else ""
            })
        return results

    def get_detail(self, csfd_id):
        """Vrátí detail filmu: rating, poster, plot, žánry"""
        r = requests.get(f"{self.BASE}/film/{csfd_id}/prehled/",
                         headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(r.text, "lxml")

        rating_el = soup.select_one(".film-rating-average")
        poster_el = soup.select_one(".film-poster img")
        plot_el = soup.select_one(".plot-full p")
        genres = [g.text for g in soup.select(".genres a")]

        return {
            "csfd_id": csfd_id,
            "rating": float(rating_el.text.replace("%", "").strip()) if rating_el else None,
            "poster": poster_el["src"] if poster_el else None,
            "plot": plot_el.text.strip() if plot_el else None,
            "genres": genres
        }
