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
            "qbittorrent_url", "http://192.168.1.152:8080/"
        )
        self.series_directory = self.cache_manager.load_setting(
            "series_directory", "/tv"
        )
        self.alt_series_directory = self.cache_manager.load_setting(
            "alt_series_directory", ""
        )
        self.movies_directory = self.cache_manager.load_setting(
            "movies_directory", "/movies"
        )
        self.alt_movies_directory = self.cache_manager.load_setting(
            "alt_movies_directory", ""
        )
        self.alternative_directories_enabled = self.cache_manager.load_setting(
            "alternative_directories_enabled", True
        )

    def _qbittorrent_api_url(self, endpoint: str, base_url: str | None = None) -> str:
        """Construct a qBittorrent API URL from the configured base URL.

        Args:
            endpoint: The API endpoint to append.
            base_url: Optional base URL to use instead of the configured one.
        """
        if base_url is None:
            base_url = self.qbittorrent_url
        base_url = base_url.strip()
        if not base_url.endswith("/"):
            base_url += "/"
        return f"{base_url}{endpoint.lstrip('/')}"

    def _is_success_response(self, response: requests.Response) -> bool:
        """Return True for successful API responses (2xx status codes)."""
        return 200 <= response.status_code < 300

    def _format_response_error(self, response: requests.Response, action: str) -> str:
        """Format an HTTP response error message for logging and display."""
        body = response.text.strip() or "<no response body>"
        return f"{action}: {response.status_code} {response.reason}: {body}"

    def open_qbittorrent_with_magnet(
        self,
        magnet_url: str,
        is_series: bool = False,
        use_alternative: bool = False,
    ) -> None:
        """Send the magnet URL to qBittorrent with authentication and optional save path.
        
        Args:
            magnet_url: The magnet link URL to send.
            is_series: If True, save to series directory; otherwise save to movies directory.
            use_alternative: If True, save to the alternative directory for the selected type.
            
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
            
            if not self._is_success_response(login_response):
                body = login_response.text.strip() or "<no response body>"
                msg = (
                    f"Failed to login to qBittorrent: "
                    f"{login_response.status_code} {login_response.reason}: {body}"
                )
                raise requests.RequestException(msg)
            
            # Determine save path
            if is_series:
                save_path = (
                    self.alt_series_directory
                    if (
                        self.alternative_directories_enabled
                        and use_alternative
                        and self.alt_series_directory
                    )
                    else self.series_directory
                )
            else:
                save_path = (
                    self.alt_movies_directory
                    if (
                        self.alternative_directories_enabled
                        and use_alternative
                        and self.alt_movies_directory
                    )
                    else self.movies_directory
                )
            
            # Prepare data payload
            data = {"urls": magnet_url}
            if save_path:
                data["savepath"] = save_path
            
            # Send the magnet URL to qBittorrent
            response = session.post(qbittorrent_url, data=data, timeout=10)
            
            if not self._is_success_response(response):
                body = response.text.strip() or "<no response body>"
                msg = (
                    f"Failed to add torrent: "
                    f"{response.status_code} {response.reason}: {body}"
                )
                raise requests.RequestException(msg)
        except (requests.RequestException, ValueError) as e:
            logger.exception("Failed to open qBittorrent")
            raise Exception(f"Failed to open qBittorrent: {e}") from e
        
    def open_qbittorrent_with_torrent_file(
        self,
        torrent_file_path: str,
        is_series: bool = False,
        use_alternative: bool = False,
    ) -> None:
        """Send a torrent file to qBittorrent with authentication and optional save path.
        
        Args:
            torrent_file_path: The path to the torrent file.
            is_series: If True, save to series directory; otherwise save to movies directory.
            use_alternative: If True, save to the alternative directory for the selected type.
            
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
            
            if not self._is_success_response(login_response):
                body = login_response.text.strip() or "<no response body>"
                msg = (
                    f"Failed to login to qBittorrent: "
                    f"{login_response.status_code} {login_response.reason}: {body}"
                )
                raise requests.RequestException(msg)
            
            # Determine save path
            if is_series:
                save_path = (
                    self.alt_series_directory
                    if (
                        self.alternative_directories_enabled
                        and use_alternative
                        and self.alt_series_directory
                    )
                    else self.series_directory
                )
            else:
                save_path = (
                    self.alt_movies_directory
                    if (
                        self.alternative_directories_enabled
                        and use_alternative
                        and self.alt_movies_directory
                    )
                    else self.movies_directory
                )
            
            # Prepare data payload
            data = {}
            if save_path:
                data["savepath"] = save_path
            
            # Open the torrent file in binary mode and send it as multipart data
            with open(torrent_file_path, "rb") as torrent_file:
                files = {"torrents": torrent_file}
                response = session.post(add_torrent_url, data=data, files=files, timeout=20)
            
            if not self._is_success_response(response):
                body = response.text.strip() or "<no response body>"
                msg = (
                    f"Failed to add torrent: "
                    f"{response.status_code} {response.reason}: {body}"
                )
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
            username, password = self.cache_manager.load_credentials()
            if username and password:
                session = requests.Session()
                login_url = self._qbittorrent_api_url("api/v2/auth/login")
                login_data = {"username": username, "password": password}
                login_response = session.post(login_url, data=login_data, timeout=10)
                if not self._is_success_response(login_response):
                    return False, self._format_response_error(login_response, "Login failed")

                version_url = self._qbittorrent_api_url("api/v2/app/version")
                response = session.get(version_url, timeout=10)
                if self._is_success_response(response):
                    return True, "Connection successful"
                return False, self._format_response_error(response, "API version check failed")

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
                login_url = self._qbittorrent_api_url("api/v2/auth/login", base_url=url)
                login_data = {"username": username, "password": password}
                session = requests.Session()
                login_response = session.post(login_url, data=login_data, timeout=10)
                
                if self._is_success_response(login_response):
                    return True
                msg = f"Authentication failed: {login_response.status_code}"
                raise requests.RequestException(msg)
            
            # Test basic connection
            response = requests.get(url, timeout=5)
            if self._is_success_response(response):
                return True
            msg = f"Connection failed: {response.status_code}"
            raise requests.RequestException(msg)
        except requests.RequestException as e:
            logger.exception("Connection test failed")
            raise Exception(str(e)) from e
