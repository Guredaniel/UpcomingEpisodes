import os
import json
from CacheManager import CacheManager

class WatchlistManager:
    def __init__(self, cache_manager):
        self.cache_manager = cache_manager
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
        """Add a show to the watchlist if it is not already present."""
        if show_name not in self.watchlist:
            self.watchlist.append(show_name)
            self.watchlist = self.remove_duplicates(self.watchlist)
            self.save_watchlist()

    def remove_show(self, show_name):
        """Remove a show from the watchlist and delete its cache file."""
        if show_name in self.watchlist:
            self.watchlist.remove(show_name)
            self.save_watchlist()
            self.cache_manager.delete_cache_file(show_name)
