import requests
from CacheManager import CacheManager

# ---------------------------
# Constants
# ---------------------------
TVMAZE_SINGLESEARCH_URL = "http://api.tvmaze.com/singlesearch/shows?q="
TVMAZE_LOOKUP_URL = "http://api.tvmaze.com/lookup/shows?imdb="

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
