import os
import re
import json
import time
import sys
from cryptography.fernet import Fernet

class CacheManager:
    CACHE_VERSION = "1.0"  # Increment this when cache format changes
    
    def __init__(self):
        self.check_cache_version()
        self.key = self.load_or_generate_key()

    def check_cache_version(self):
        """Check cache version and update if necessary. Cache is always preserved."""
        version_path = os.path.join(self.get_cache_directory(), "version.txt")
        try:
            # Always write current version (cache is preserved across versions)
            with open(version_path, "w") as f:
                f.write(self.CACHE_VERSION)
        except Exception as e:
            # If we can't write version, silently continue
            print(f"Warning: Could not write cache version: {e}")
            pass

    def clear_all_cache(self):
        """Clear all cache files."""
        cache_dir = self.get_cache_directory()
        if os.path.exists(cache_dir):
            for filename in os.listdir(cache_dir):
                file_path = os.path.join(cache_dir, filename)
                try:
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                except Exception as e:
                    print(f"Warning: Failed to remove cache file {filename}: {e}")

    def load_or_generate_key(self):
        """Load or generate an encryption key."""
        key_path = os.path.join(self.get_cache_directory(), "key.key")
        if os.path.exists(key_path):
            with open(key_path, "rb") as key_file:
                return key_file.read()
        else:
            key = Fernet.generate_key()
            with open(key_path, "wb") as key_file:
                key_file.write(key)
            return key
        
    def get_cache_directory(self):
        """Ensure a cache directory exists in the appropriate location for the platform."""
        if sys.platform == "darwin":
            # Use ~/Library/Application Support for macOS
            appdata = os.path.expanduser("~/Library/Application Support")
        elif sys.platform.startswith("win32"):
            # Use %LOCALAPPDATA% for Windows
            appdata = os.path.expanduser("~\\AppData\\Local")
        else:
            # Use ~/.local/share for Linux/Unix
            appdata = os.path.expanduser("~/.local/share")
            
        cache_dir = os.path.join(appdata, "MagnetLinker")
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)
        return cache_dir

    def save_credentials(self, username, password):
        """Save encrypted qBittorrent credentials."""
        try:
            self.key = self.load_or_generate_key()
            cipher_suite = Fernet(self.key)
            encrypted_username = cipher_suite.encrypt(username.encode())
            encrypted_password = cipher_suite.encrypt(password.encode())
            credentials = {
                "username": encrypted_username.decode(),
                "password": encrypted_password.decode()
            }
            credentials_path = os.path.join(self.get_cache_directory(), "qbittorrent_credentials.json")
            with open(credentials_path, "w") as f:
                json.dump(credentials, f)
        except Exception as e:
            Exception(f"An error occurred while saving credentials: {e}")

    def load_credentials(self):
        """Load and decrypt qBittorrent credentials."""
        credentials_path = os.path.join(self.get_cache_directory(), "qbittorrent_credentials.json")
        if not os.path.exists(credentials_path):
            return None, None
        with open(credentials_path, "r") as f:
            credentials = json.load(f)
        cipher_suite = Fernet(self.key)
        username = cipher_suite.decrypt(credentials["username"].encode()).decode()
        password = cipher_suite.decrypt(credentials["password"].encode()).decode()
        return username, password

    def delete_login_cache(self):
        """Delete the qBittorrent credentials and key cache."""
        credentials_path = os.path.join(self.get_cache_directory(), "qbittorrent_credentials.json")
        key_path = os.path.join(self.get_cache_directory(), "key.key")
        files_deleted = False  # Tracks whether any files were deleted

        try:
            if os.path.exists(credentials_path):
                os.remove(credentials_path)
                files_deleted = True
        except Exception as e:
            print(f"An error occurred while deleting the credentials cache: {e}")

        try:  
            if os.path.exists(key_path):
                os.remove(key_path)
                files_deleted = True
        except Exception as e:
            print(f"An error occurred while deleting the cache: {e}")

        return files_deleted
    
    def credentials_exist(self):
        """Check if qBittorrent credentials exist."""
        credentials_path = os.path.join(self.get_cache_directory(), "qbittorrent_credentials.json")
        return os.path.exists(credentials_path)
    
    def clear_credentials(self):
        """Clear saved qBittorrent credentials. Alias for delete_login_cache."""
        return self.delete_login_cache()
    
    def save_setting(self, key, value):
        """Save a setting to the cache."""
        settings_path = os.path.join(self.get_cache_directory(), "settings.json")
        settings = {}
        if os.path.exists(settings_path):
            try:
                with open(settings_path, "r") as f:
                    settings = json.load(f)
            except (json.JSONDecodeError, IOError):
                # If settings file is corrupted, start with empty settings
                settings = {}
        settings[key] = value
        try:
            with open(settings_path, "w") as f:
                json.dump(settings, f)
        except IOError:
            # If we can't write, silently fail
            pass

    def load_setting(self, key, default=None):
        """Load a setting from the cache."""
        settings_path = os.path.join(self.get_cache_directory(), "settings.json")
        if not os.path.exists(settings_path):
            return default
        try:
            with open(settings_path, "r") as f:
                settings = json.load(f)
        except (json.JSONDecodeError, IOError):
            # If settings file is corrupted, return default
            return default
        return settings.get(key, default)
    
    def get_saved_sites(self):
        """Get the list of saved torrent sites."""
        default_sites = [
            {"name": "nyaa.si", "url": "https://nyaa.si"},
            {"name": "ext.to", "url": "https://ext.to"},
            {"name": "rutor.info", "url": "https://rutor.info"},
            {"name": "ktuvit.me", "url": "https://www.ktuvit.me"}
        ]
        return self.load_setting("saved_sites", default_sites)

    def save_sites(self, sites):
        """Save the list of torrent sites."""
        self.save_setting("saved_sites", sites)