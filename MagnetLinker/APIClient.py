from __future__ import annotations

import logging
import webbrowser
from typing import TYPE_CHECKING

import requests

if TYPE_CHECKING:
    from CacheManager import CacheManager

logger = logging.getLogger(__name__)


class APIClient:
    """Client for communicating with qBittorrent API and managing torrents."""

    def __init__(self, cache_manager: CacheManager) -> None:
        """Initialize the API client.
        
        Args:
            cache_manager: CacheManager instance for loading settings.
        """
        self.cache_manager = cache_manager
        self.qbittorrent_url = self.cache_manager.load_setting(
            "qbittorrent_url", "http://192.168.1.111:8080/"
        )
        self.series_directory = self.cache_manager.load_setting(
            "series_directory", "/media/elements/Series"
        )
        self.movies_directory = self.cache_manager.load_setting(
            "movies_directory", "/media/elements/Movies"
        )

    def _qbittorrent_api_url(self, endpoint: str) -> str:
        """Construct a qBittorrent API URL from the configured base URL."""
        base_url = self.qbittorrent_url.strip()
        if not base_url.endswith("/"):
            base_url += "/"
        return f"{base_url}{endpoint.lstrip('/')}"

    def open_qbittorrent_with_magnet(self, magnet_url: str, is_series: bool = False) -> None:
        """Send the magnet URL to qBittorrent with authentication and optional save path.
        
        Args:
            magnet_url: The magnet link URL to send.
            is_series: If True, save to series directory; otherwise save to movies directory.
            
        Raises:
            Exception: If login fails or torrent cannot be added.
        """
        try:
            # Retrieve authentication details from cache
            username, password = self.cache_manager.load_credentials()
            if not username or not password:
                msg = "qBittorrent credentials not found in cache."
                raise ValueError(msg)
            
            qbittorrent_url = self._qbittorrent_api_url("api/v2/torrents/add")
            
            # Login to qBittorrent
            login_url = self._qbittorrent_api_url("api/v2/auth/login")
            login_data = {"username": username, "password": password}
            session = requests.Session()
            login_response = session.post(login_url, data=login_data, timeout=10)
            
            if login_response.status_code != 200:
                msg = f"Failed to login to qBittorrent: {login_response.text}"
                raise requests.RequestException(msg)
            
            # Determine save path
            save_path = self.series_directory if is_series else self.movies_directory
            
            # Prepare data payload
            data = {"urls": magnet_url}
            if save_path:
                data["savepath"] = save_path
            
            # Send the magnet URL to qBittorrent
            response = session.post(qbittorrent_url, data=data, timeout=10)
            
            if response.status_code != 200:
                msg = f"Failed to add torrent: {response.text}"
                raise requests.RequestException(msg)
        except (requests.RequestException, ValueError) as e:
            logger.exception("Failed to open qBittorrent")
            raise Exception(f"Failed to open qBittorrent: {e}") from e
        
    def open_qbittorrent_with_torrent_file(
        self, torrent_file_path: str, is_series: bool = False
    ) -> None:
        """Send a torrent file to qBittorrent with authentication and optional save path.
        
        Args:
            torrent_file_path: The path to the torrent file.
            is_series: If True, save to series directory; otherwise save to movies directory.
            
        Raises:
            Exception: If login fails or torrent cannot be added.
        """
        try:
            # Retrieve authentication details from cache
            username, password = self.cache_manager.load_credentials()
            if not username or not password:
                msg = "qBittorrent credentials not found in cache."
                raise ValueError(msg)
            
            add_torrent_url = self._qbittorrent_api_url("api/v2/torrents/add")
            
            # Login to qBittorrent
            login_url = self._qbittorrent_api_url("api/v2/auth/login")
            login_data = {"username": username, "password": password}
            session = requests.Session()
            login_response = session.post(login_url, data=login_data, timeout=10)
            
            if login_response.status_code != 200:
                msg = f"Failed to login to qBittorrent: {login_response.text}"
                raise requests.RequestException(msg)
            
            # Determine save path
            save_path = self.series_directory if is_series else self.movies_directory
            
            # Prepare data payload
            data = {}
            if save_path:
                data["savepath"] = save_path
            
            # Open the torrent file in binary mode and send it as multipart data
            with open(torrent_file_path, "rb") as torrent_file:
                files = {"torrents": torrent_file}
                response = session.post(add_torrent_url, data=data, files=files, timeout=20)
            
            if response.status_code != 200:
                msg = f"Failed to add torrent: {response.text}"
                raise requests.RequestException(msg)
        except (requests.RequestException, ValueError, OSError) as e:
            logger.exception("Failed to open qBittorrent with torrent file")
            raise Exception(f"Failed to open qBittorrent with torrent file: {e}") from e

    def open_qbittorrent_web(self) -> None:
        """Open the qBittorrent web interface."""
        try:
            webbrowser.open(self.qbittorrent_url)
        except Exception as e:
            logger.exception("Failed to open qBittorrent web interface")
            raise Exception(f"Failed to open qBittorrent web interface: {e}") from e

    def check_qbittorrent_connection(self) -> tuple[bool, str]:
        """Check the connection to the qBittorrent web interface.
        
        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            response = requests.get(self.qbittorrent_url, timeout=5)
            if response.status_code == 200 and "qBittorrent" in response.text:
                return True, "Connection successful"
            return False, f"Connection failed: {response.status_code} {response.reason}"
        except requests.exceptions.RequestException as e:
            return False, f"Connection failed: {e}"
    
    def test_connection(
        self, url: str, username: str | None = None, password: str | None = None
    ) -> bool:
        """Test connection to qBittorrent with optional custom credentials.
        
        Args:
            url: The qBittorrent URL to test.
            username: Optional username (uses cached if None).
            password: Optional password (uses cached if None).
            
        Returns:
            bool: True if connection successful, False otherwise.
            
        Raises:
            Exception: If connection test fails.
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
                msg = f"Authentication failed: {login_response.status_code}"
                raise requests.RequestException(msg)
            
            # Test basic connection
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                return True
            msg = f"Connection failed: {response.status_code}"
            raise requests.RequestException(msg)
        except requests.RequestException as e:
            logger.exception("Connection test failed")
            raise Exception(str(e)) from e
