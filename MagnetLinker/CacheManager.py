import os
import re
import json
import time
import sys
from cryptography.fernet import Fernet
class CacheManager:
    def __init__(self):
        self.key = self.load_or_generate_key()

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
            with open(settings_path, "r") as f:
                settings = json.load(f)
        settings[key] = value
        with open(settings_path, "w") as f:
            json.dump(settings, f)

    def load_setting(self, key, default=None):
        """Load a setting from the cache."""
        settings_path = os.path.join(self.get_cache_directory(), "settings.json")
        if not os.path.exists(settings_path):
            return default
        with open(settings_path, "r") as f:
            settings = json.load(f)
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