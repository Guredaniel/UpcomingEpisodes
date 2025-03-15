import requests
import webbrowser
from CacheManager import CacheManager
from bs4 import BeautifulSoup

# ---------------------------
# Constants
# ---------------------------
TVMAZE_SINGLESEARCH_URL = "http://api.tvmaze.com/singlesearch/shows?q="
TVMAZE_LOOKUP_URL = "http://api.tvmaze.com/lookup/shows?imdb="
TVMAZE_SEARCH_URL = "http://api.tvmaze.com/search/shows?q="
TMDB_POPULAR_TV_URL = "https://www.themoviedb.org/tv"
NYAA_RSS_URL = "https://nyaa.si/?page=rss"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept-Language': 'en-GB,en;q=0.9',
}

class APIClient:
    def __init__(self, cache_manager):
        self.cache_manager = cache_manager
        self.qbittorrent_url = self.cache_manager.load_setting("qbittorrent_url", "http://192.168.1.113:8080/")
        self.series_directory = self.cache_manager.load_setting("series_directory", "/media/external/Series")
        self.movies_directory = self.cache_manager.load_setting("movies_directory", "/media/external/Movies")

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
                    # Use the correct show name for caching
                    correct_show_name = data.get("name", show_name)
                    correct_cache_file = self.cache_manager.get_cache_file_path(correct_show_name)
                    self.cache_manager.set_cached_data(correct_cache_file, data)
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
        
        show_name = data.get("name", show_name)  # Use the full show name from the API
        
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

    def open_qbittorrent_with_magnet(self, magnet_url, is_series=False):
        """Send the magnet URL to the qBittorrent web interface with authentication and optional save path."""
        try:
            # Retrieve authentication details from cache
            username, password = self.cache_manager.load_credentials()
            if not username or not password:
                raise Exception("qBittorrent credentials not found in cache.")
            
            # Authentication details
            qbittorrent_url = f"{self.qbittorrent_url}api/v2/torrents/add"
            
            # Login to qBittorrent
            login_url = f"{self.qbittorrent_url}api/v2/auth/login"
            login_data = {"username": username, "password": password}
            session = requests.Session()
            login_response = session.post(login_url, data=login_data)
            
            if login_response.status_code != 200:
                raise Exception(f"Failed to login to qBittorrent: {login_response.text}")
            
            # Determine save path
            save_path = self.series_directory if is_series else self.movies_directory
            
            # Prepare data payload
            data = {"urls": magnet_url}
            if save_path:
                data["savepath"] = save_path
            
            # Send the magnet URL to the qBittorrent web interface
            response = session.post(qbittorrent_url, data=data)
            
            if response.status_code != 200:
                raise Exception(f"Failed to add torrent: {response.text}")
        except Exception as e:
            raise Exception(f"Failed to open qBittorrent: {e}")

    def open_qbittorrent_web(self):
        """Open the qBittorrent web interface."""
        try:
            webbrowser.open(self.qbittorrent_url)
        except Exception as e:
            raise Exception(f"Failed to open qBittorrent web interface: {e}")

    def search_torrent(self, show_name, episode, site):
        """
        Search for a torrent using the provided show name, episode number, and site.
        Returns the magnet link if found, otherwise returns None.
        """
        # Decrement the episode number by 1
        if episode.startswith("S") and "E" in episode:
            season, ep_num = episode[1:].split("E")
            try:
                ep_num = int(ep_num) - 1
                if ep_num < 1:
                    search_query = f"{show_name} S{season}E01"  # Handle edge case for episode 1
                else:
                    search_query = f"{show_name} S{season}E{ep_num:02d}"
            except ValueError:
                search_query = f"{show_name} {episode}"
        else:
            search_query = f"{show_name} {episode}"

        if site == "rutor":
            search_url = f"https://rutor.info/search/{search_query.replace(' ', '%20')}"
        elif site == "ext":
            search_url = f"https://ext.to/browse/?q={search_query.replace(' ', '+')}"
        elif site == "nyaa":
            search_url = f"https://nyaa.si/?f=0&c=1_2&q={search_query.replace(' ', '+')}"
        else:
            raise ValueError("Unsupported site")

        response = requests.get(search_url, headers=HEADERS)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            magnet_link = None
            if site == "rutor":
                magnet_link = soup.find('a', href=True, text='Magnet link')['href']
            elif site == "ext":
                magnet_link = soup.find('a', href=True, text='Magnet link')['href']
            elif site == "nyaa":
                magnet_link = soup.find('a', href=True, text='Magnet link')['href']
            return magnet_link
        else:
            return None

    def check_qbittorrent_connection(self):
        """Check the connection to the qBittorrent web interface."""
        try:
            response = requests.get(self.qbittorrent_url, timeout=5)
            if response.status_code == 200 and "qBittorrent" in response.text:
                return True, "Connection successful"
            else:
                return False, f"Connection failed: {response.status_code} {response.reason}"
        except requests.exceptions.RequestException as e:
            return False, f"Connection failed: {e}"
