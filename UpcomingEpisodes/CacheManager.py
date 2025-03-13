import os
import re
import json
import time

# ---------------------------
# Constants
# ---------------------------
CACHE_TIMEOUT = 86400  # seconds, e.g. 1 hour

class CacheManager:
    def __init__(self):
        self.cache_timeout = CACHE_TIMEOUT

    def get_cache_directory(self):
        """Ensure a cache directory exists inside your %LOCALAPPDATA% folder."""
        appdata = os.environ.get("LOCALAPPDATA", ".")
        cache_dir = os.path.join(appdata, "UpcomingReleasesCache")
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
