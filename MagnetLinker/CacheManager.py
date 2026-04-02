from __future__ import annotations

import os
import sys
import json
import logging
from typing import Any, Optional
from pathlib import Path
from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)


class CacheManager:
    """Manages application cache, settings, and encrypted credentials."""

    CACHE_VERSION: str = "1.0"  # Increment this when cache format changes
    
    def __init__(self) -> None:
        """Initialize the cache manager and load encryption key."""
        self.check_cache_version()
        self.key: bytes = self.load_or_generate_key()

    def check_cache_version(self) -> None:
        """Check cache version and update if necessary. Cache is always preserved."""
        version_path = self.get_cache_directory() / "version.txt"
        try:
            version_path.write_text(self.CACHE_VERSION)
        except OSError as e:
            logger.warning(f"Could not write cache version: {e}")

    def clear_all_cache(self) -> None:
        """Clear all cache files."""
        cache_dir = self.get_cache_directory()
        if cache_dir.exists():
            for file_path in cache_dir.iterdir():
                if file_path.is_file():
                    try:
                        file_path.unlink()
                    except OSError as e:
                        logger.warning(f"Failed to remove cache file {file_path.name}: {e}")

    def load_or_generate_key(self) -> bytes:
        """Load or generate an encryption key.

        Returns:
            bytes: The encryption key for Fernet cipher.
        """
        key_path = self.get_cache_directory() / "key.key"
        if key_path.exists():
            return key_path.read_bytes()
        
        key = Fernet.generate_key()
        key_path.write_bytes(key)
        return key
        
    def get_cache_directory(self) -> Path:
        """Ensure a cache directory exists in the appropriate location for the platform.
        
        Returns:
            Path: The cache directory path.
        """
        if sys.platform == "darwin":
            # Use ~/Library/Application Support for macOS
            appdata = Path.home() / "Library" / "Application Support"
        elif sys.platform.startswith("win32"):
            # Use %LOCALAPPDATA% for Windows
            appdata = Path.home() / "AppData" / "Local"
        else:
            # Use ~/.local/share for Linux/Unix
            appdata = Path.home() / ".local" / "share"

        cache_dir = appdata / "MagnetLinker"
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir

    def save_credentials(self, username: str, password: str) -> None:
        """Save encrypted qBittorrent credentials.
        
        Args:
            username: The qBittorrent username.
            password: The qBittorrent password.
        """
        try:
            self.key = self.load_or_generate_key()
            cipher_suite = Fernet(self.key)
            encrypted_username = cipher_suite.encrypt(username.encode())
            encrypted_password = cipher_suite.encrypt(password.encode())
            credentials = {
                "username": encrypted_username.decode(),
                "password": encrypted_password.decode(),
            }
            credentials_path = self.get_cache_directory() / "qbittorrent_credentials.json"
            credentials_path.write_text(json.dumps(credentials))
        except (OSError, ValueError) as e:
            logger.exception(f"Failed to save credentials: {e}")

    def load_credentials(self) -> tuple[Optional[str], Optional[str]]:
        """Load and decrypt qBittorrent credentials.
        
        Returns:
            tuple: (username, password) or (None, None) if credentials don't exist.
        """
        credentials_path = self.get_cache_directory() / "qbittorrent_credentials.json"
        if not credentials_path.exists():
            return None, None
        
        try:
            credentials = json.loads(credentials_path.read_text())
            cipher_suite = Fernet(self.key)
            username = cipher_suite.decrypt(credentials["username"].encode()).decode()
            password = cipher_suite.decrypt(credentials["password"].encode()).decode()
            return username, password
        except (json.JSONDecodeError, ValueError, OSError) as e:
            logger.exception(f"Failed to load credentials: {e}")
            return None, None

    def delete_login_cache(self) -> bool:
        """Delete the qBittorrent credentials and key cache.
        
        Returns:
            bool: True if any files were deleted, False otherwise.
        """
        credentials_path = self.get_cache_directory() / "qbittorrent_credentials.json"
        key_path = self.get_cache_directory() / "key.key"
        files_deleted = False

        for path in [credentials_path, key_path]:
            if path.exists():
                try:
                    path.unlink()
                    files_deleted = True
                except OSError as e:
                    logger.exception(f"Failed to delete {path.name}: {e}")

        return files_deleted
    
    def credentials_exist(self) -> bool:
        """Check if qBittorrent credentials exist.
        
        Returns:
            bool: True if credentials file exists, False otherwise.
        """
        credentials_path = self.get_cache_directory() / "qbittorrent_credentials.json"
        return credentials_path.exists()

    def clear_credentials(self) -> bool:
        """Clear saved qBittorrent credentials. Alias for delete_login_cache.
        
        Returns:
            bool: True if any files were deleted, False otherwise.
        """
        return self.delete_login_cache()
    
    def save_setting(self, key: str, value: Any) -> None:
        """Save a setting to the cache.
        
        Args:
            key: The setting key.
            value: The setting value.
        """
        settings_path = self.get_cache_directory() / "settings.json"
        settings: dict[str, Any] = {}
        
        if settings_path.exists():
            try:
                settings = json.loads(settings_path.read_text())
            except (json.JSONDecodeError, OSError):
                logger.warning("Settings file corrupted, resetting")
                settings = {}
        
        settings[key] = value
        try:
            settings_path.write_text(json.dumps(settings))
        except OSError as e:
            logger.warning(f"Failed to save setting {key}: {e}")

    def load_setting(self, key: str, default: Any = None) -> Any:
        """Load a setting from the cache.
        
        Args:
            key: The setting key.
            default: The default value if setting doesn't exist.
            
        Returns:
            Any: The setting value or default if not found.
        """
        settings_path = self.get_cache_directory() / "settings.json"
        if not settings_path.exists():
            return default
        
        try:
            settings = json.loads(settings_path.read_text())
        except (json.JSONDecodeError, OSError):
            logger.warning("Settings file corrupted, using default")
            return default
        
        return settings.get(key, default)
    
    def get_saved_sites(self) -> list[dict[str, str]]:
        """Get the list of saved torrent sites.
        
        Returns:
            list: List of site dictionaries with 'name' and 'url' keys.
        """
        default_sites = [
            {"name": "nyaa.si", "url": "https://nyaa.si"},
            {"name": "ext.to", "url": "https://ext.to"},
            {"name": "rutor.info", "url": "https://rutor.info"},
            {"name": "ktuvit.me", "url": "https://www.ktuvit.me"},
        ]
        return self.load_setting("saved_sites", default_sites)

    def save_sites(self, sites: list[dict[str, str]]) -> None:
        """Save the list of torrent sites.
        
        Args:
            sites: List of site dictionaries with 'name' and 'url' keys.
        """
        self.save_setting("saved_sites", sites)