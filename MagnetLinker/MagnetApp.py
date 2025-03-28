from customtkinter import CTk
from CacheManager import CacheManager
from APIClient import APIClient
from GUIManager import GUIManager

if __name__ == "__main__":
    cache_manager = CacheManager()
    api_client = APIClient(cache_manager)      
    
    root = CTk()
    gui_manager = GUIManager(root, cache_manager, api_client)
