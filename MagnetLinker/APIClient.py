from CacheManager import CacheManager
import requests
import webbrowser

class APIClient:
    def __init__(self, cache_manager):
        self.cache_manager = cache_manager
        self.qbittorrent_url = self.cache_manager.load_setting("qbittorrent_url", "http://192.168.1.113:8080/")
        self.series_directory = self.cache_manager.load_setting("series_directory", "/media/external/Series")
        self.movies_directory = self.cache_manager.load_setting("movies_directory", "/media/external/Movies")

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
            # Add timeout to login request
            login_response = session.post(login_url, data=login_data, timeout=10)
            
            if login_response.status_code != 200:
                raise Exception(f"Failed to login to qBittorrent: {login_response.text}")
            
            # Determine save path
            save_path = self.series_directory if is_series else self.movies_directory
            
            # Prepare data payload
            data = {"urls": magnet_url}
            if save_path:
                data["savepath"] = save_path
            
            # Send the magnet URL to the qBittorrent web interface with timeout
            response = session.post(qbittorrent_url, data=data, timeout=10)
            
            if response.status_code != 200:
                raise Exception(f"Failed to add torrent: {response.text}")
        except Exception as e:
            raise Exception(f"Failed to open qBittorrent: {e}")
        
    def open_qbittorrent_with_torrent_file(self, torrent_file_path, is_series=False):
        """Send a torrent file to the qBittorrent web interface with authentication and optional save path.
        
        Parameters:
            torrent_file_path (str): The path to the torrent file.
            is_series (bool): Determines which save directory to use (series or movies).
        """
        try:
            # Retrieve authentication details from cache
            username, password = self.cache_manager.load_credentials()
            if not username or not password:
                raise Exception("qBittorrent credentials not found in cache.")
            
            # Authentication details
            add_torrent_url = f"{self.qbittorrent_url}api/v2/torrents/add"
            
            # Login to qBittorrent
            login_url = f"{self.qbittorrent_url}api/v2/auth/login"
            login_data = {"username": username, "password": password}
            session = requests.Session()
            # Add timeout to login request
            login_response = session.post(login_url, data=login_data, timeout=10)
            
            if login_response.status_code != 200:
                raise Exception(f"Failed to login to qBittorrent: {login_response.text}")
            
            # Determine save path
            save_path = self.series_directory if is_series else self.movies_directory
            
            # Prepare data payload
            data = {}
            if save_path:
                data["savepath"] = save_path
            
            # Open the torrent file in binary mode and send it as multipart data
            with open(torrent_file_path, "rb") as torrent_file:
                files = {"torrents": torrent_file}
                # Add timeout to torrent upload request
                response = session.post(add_torrent_url, data=data, files=files, timeout=20)
            
            if response.status_code != 200:
                raise Exception(f"Failed to add torrent: {response.text}")
        except Exception as e:
            raise Exception(f"Failed to open qBittorrent with torrent file: {e}")

    def open_qbittorrent_web(self):
        """Open the qBittorrent web interface."""
        try:
            webbrowser.open(self.qbittorrent_url)
        except Exception as e:
            raise Exception(f"Failed to open qBittorrent web interface: {e}")

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
    
    def test_connection(self, url, username=None, password=None):
        """Test connection to qBittorrent with optional custom credentials.
        
        Args:
            url: The qBittorrent URL to test
            username: Optional username (uses cached if None)
            password: Optional password (uses cached if None)
            
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            # If credentials provided, test with those
            if username and password:
                login_url = f"{url}api/v2/auth/login"
                login_data = {"username": username, "password": password}
                session = requests.Session()
                login_response = session.post(login_url, data=login_data, timeout=10)
                
                if login_response.status_code == 200:
                    return True
                else:
                    raise Exception(f"Authentication failed: {login_response.status_code}")
            else:
                # Test basic connection
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    return True
                else:
                    raise Exception(f"Connection failed: {response.status_code}")
        except Exception as e:
            raise Exception(str(e))
