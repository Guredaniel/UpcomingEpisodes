import requests
from CacheManager import CacheManager
from bs4 import BeautifulSoup

# ---------------------------
# Constants
# ---------------------------
TVMAZE_SINGLESEARCH_URL = "http://api.tvmaze.com/singlesearch/shows?q="
TVMAZE_LOOKUP_URL = "http://api.tvmaze.com/lookup/shows?imdb="
TVMAZE_SEARCH_URL = "http://api.tvmaze.com/search/shows?q="
TMDB_POPULAR_TV_URL = "https://www.themoviedb.org/tv"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9',
}

class APIClient:
    def __init__(self, cache_manager):
        self.cache_manager = cache_manager

    def get_next_episode(self, show_name):
        """
        Fetch the details for the next episode of a given show.
        Uses cached data if available and retrieves the IMDb id.
        Returns a dictionary with show details.
        """
        cache_file = self.cache_manager.get_cache_file_path(show_name)
        cached_data = self.cache_manager.get_cached_data(cache_file)
        
        if cached_data is not None:
            data = cached_data
        else:
            try:
                url = f"{TVMAZE_SINGLESEARCH_URL}{show_name}&embed=nextepisode"
                response = requests.get(url)
                if response.status_code == 200:
                    data = response.json()
                    self.cache_manager.set_cached_data(cache_file, data)
                else:
                    data = None
            except Exception:
                data = None

        imdb_id = data.get("externals", {}).get("imdb") if data else None
        
        if data is None:
            return {
                "show": show_name,
                "episode": "N/A",
                "title": "Failed to fetch info",
                "airdate": "N/A",
                "imdb": imdb_id
            }
        
        if "_embedded" in data and "nextepisode" in data["_embedded"]:
            ep = data["_embedded"]["nextepisode"]
            ep_title = ep.get("name", "Unknown")
            airdate = ep.get("airdate", "Unknown")
            season = ep.get("season", "")
            number = ep.get("number", "")
            if season and number:
                try:
                    # Ensure two-digit formatting for season and episode.
                    season_int = int(season)
                    number_int = int(number)
                    episode_code = f"S{season_int:02d}E{number_int:02d}"
                except Exception:
                    episode_code = f"S{season}E{number}"
            else:
                episode_code = "TBD"
            return {
                "show": show_name,
                "episode": episode_code,
                "title": ep_title,
                "airdate": airdate,
                "imdb": imdb_id
            }
        else:
            return {
                "show": show_name,
                "episode": "N/A",
                "title": "No upcoming episode",
                "airdate": "N/A",
                "imdb": imdb_id
            }

    def lookup_show_by_imdb(self, imdb_id):
        """
        Look up a show using its IMDb ID via TVmaze API.
        Returns the JSON data if found, otherwise returns None.
        """
        try:
            url = f"{TVMAZE_LOOKUP_URL}{imdb_id}"
            response = requests.get(url)
            if response.status_code == 200:
                return response.json()
            else:
                return None
        except Exception:
            return None

    def search_shows(self, query):
        """
        Search for shows using the TVmaze API.
        Returns the JSON data if found, otherwise returns None.
        """
        try:
            url = f"{TVMAZE_SEARCH_URL}{query}"
            response = requests.get(url)
            if response.status_code == 200:
                return response.json()
            else:
                return None
        except Exception:
            return None

    def fetch_latest_shows(self):
        """
        Fetch the latest popular shows from TMDB.
        Returns a list of show titles if found, otherwise returns an error message.
        """
        try:
            response = requests.get(TMDB_POPULAR_TV_URL, headers=HEADERS)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find the TV show cards on the page
            show_cards = soup.find_all('div', class_='card style_1')[:12]  # Limit to top 10
            
            # Extract the show titles
            popular_shows = [card.find('h2').text.strip() for card in show_cards]
            return popular_shows
        except requests.exceptions.RequestException as e:
            print(f"Failed to fetch data: {e}")
            return ["Error fetching data"]
