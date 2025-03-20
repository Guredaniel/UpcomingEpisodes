import os
import re
import json
import time
from cryptography.fernet import Fernet

# ---------------------------
# Constants
# ---------------------------
CACHE_TIMEOUT = 86400  # seconds, e.g. 1 hour

class CacheManager:
    def __init__(self):
        self.cache_timeout = CACHE_TIMEOUT
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
        """Ensure a cache directory exists inside your %LOCALAPPDATA% folder."""
        appdata = os.path.expanduser("~\\AppData\\Local")
        cache_dir = os.path.join(appdata, "UpcomingEpisodes")
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)
        return cache_dir

    def get_cache_file_path(self, show_name):
        """Generate a safe filename for the given show."""
        safe_show = re.sub(r"[^\w\-]", "_", show_name)
        cache_dir = self.get_cache_directory()
        return os.path.join(cache_dir, f"{safe_show}.json")

    def get_cached_data(self, filepath):
        """Return cached data if it exists and hasn't expired; otherwise, return None."""
        try:
            with open(filepath, "r") as f:
                data = json.load(f)
            timestamp = data.get("timestamp", 0)
            if time.time() - timestamp < self.cache_timeout:
                return data.get("data")
        except Exception:
            pass
        return None

    def set_cached_data(self, filepath, data_from_api):
        """Cache the API response along with a timestamp."""
        data = {"timestamp": time.time(), "data": data_from_api}
        try:
            with open(filepath, "w") as f:
                json.dump(data, f)
        except Exception as e:
            print("Error saving cache:", e)

    def delete_cache_file(self, show_name):
        """Delete the cache file for the given show."""
        cache_file = self.get_cache_file_path(show_name)
        if os.path.exists(cache_file):
            os.remove(cache_file)

    def save_credentials(self, username, password):
        """Save encrypted qBittorrent credentials."""
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
