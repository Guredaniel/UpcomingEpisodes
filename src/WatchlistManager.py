import os
import json
from CacheManager import CacheManager
from APIClient import APIClient  # Import APIClient

class WatchlistManager:
    def __init__(self, cache_manager):
        self.cache_manager = cache_manager
        self.api_client = APIClient(cache_manager)  # Pass cache_manager to APIClient
        self.watchlist_file = os.path.join(self.cache_manager.get_cache_directory(), "watchlist.json")
        self.watchlist = self.load_watchlist()

    def remove_duplicates(self, watchlist):
        """Remove duplicates from the watchlist."""
        return list(dict.fromkeys(watchlist))

    def load_watchlist(self):
        """Load the watchlist from the file, removing duplicates. Return a default list if the file does not exist."""
        try:
            with open(self.watchlist_file, "r") as f:
                watchlist = json.load(f)
                return self.remove_duplicates(watchlist)
        except Exception:
            # Default watchlist if the file does not exist.
            return self.remove_duplicates(["Squid Game"])

    def save_watchlist(self):
        """Save the current watchlist to the file."""
        try:
            with open(self.watchlist_file, "w") as f:
                json.dump(self.watchlist, f)
        except Exception as e:
            print("Error saving watchlist:", e)

    def add_show(self, show_name):
        """Add a show to the watchlist if it is not already present and exists in the API."""
        if show_name not in self.watchlist:
            # Validate show existence using APIClient
            show_info = self.api_client.get_next_episode(show_name)
            if show_info["title"] != "Failed to fetch info":
                full_show_name = show_info["show"]  # Use the full show name from the API
                self.watchlist.append(full_show_name)
                self.watchlist = self.remove_duplicates(self.watchlist)
                self.save_watchlist()
                # Delete the incorrect cache file if it exists
                incorrect_cache_file = self.cache_manager.get_cache_file_path(show_name)
                if os.path.exists(incorrect_cache_file):
                    os.remove(incorrect_cache_file)
            else:
                raise ValueError(f"Show '{show_name}' does not exist.")

    def remove_show(self, show_name):
        """Remove a show from the watchlist and delete its cache file."""
        for show in self.watchlist:
            if show.lower() == show_name.lower():
                self.watchlist.remove(show)
                self.save_watchlist()
                self.cache_manager.delete_cache_file(show)
                break
