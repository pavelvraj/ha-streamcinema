import requests
from bs4 import BeautifulSoup
import re

class CSFDScraper:
    BASE_URL = "https://www.csfd.cz"
    HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}

    def search_movie(self, query):
        try:
            r = requests.get(f"{self.BASE_URL}/hledat/", params={"q": query}, headers=self.HEADERS, timeout=10)
            soup = BeautifulSoup(r.content, "lxml")
            
            # Hledáme první relevantní výsledek ve filmech
            # ČSFD struktura se mění, aktuálně:
            article = soup.select_one(".box-content article")
            if not article: return None

            link = article.select_one("a.film-title-name")
            if not link: return None
            
            url = link['href']
            csfd_id = re.search(r"/film/(\d+)", url).group(1)
            
            return self.get_movie_details(csfd_id)
        except Exception as e:
            print(f"CSFD Search Error: {e}")
            return None

    def get_movie_details(self, csfd_id):
        try:
            url = f"{self.BASE_URL}/film/{csfd_id}/prehled/"
            r = requests.get(url, headers=self.HEADERS, timeout=10)
            soup = BeautifulSoup(r.content, "lxml")
            
            title = soup.select_one("h1").text.strip().split("(")[0].strip()
            
            # Rok
            year_span = soup.select_one(".film-title-info span")
            year = int(year_span.text.strip("()")) if year_span else 0
            
            # Hodnocení
            rating_div = soup.select_one(".film-rating-average")
            rating = float(rating_div.text.replace("%", "").strip()) if rating_div else 0.0
            
            # Poster
            poster_img = soup.select_one(".film-poster")
            poster = poster_img['src'] if poster_img else None
            if poster and poster.startswith("//"): poster = "https:" + poster
            
            # Děj
            plot_div = soup.select_one(".plot-full p") or soup.select_one(".plot-preview p")
            plot = plot_div.text.strip() if plot_div else ""
            
            # Žánry
            genres = [g.text for g in soup.select(".genres a")]
            
            return {
                "csfd_id": csfd_id,
                "title": title,
                "year": year,
                "rating": rating,
                "poster": poster,
                "plot": plot,
                "genres": genres
            }
        except Exception as e:
            print(f"CSFD Detail Error: {e}")
            return None
