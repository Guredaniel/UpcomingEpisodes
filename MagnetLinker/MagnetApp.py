import sys
from customtkinter import CTk
from CacheManager import CacheManager
from APIClient import APIClient
from GUIManager import GUIManager

def main():
    cache_manager = CacheManager()
    api_client = APIClient(cache_manager)

    root = CTk()
    root.withdraw()  # Hide the window immediately
    
    # Prevent the root window from ever being shown
    root.overrideredirect(True)
    root.attributes('-alpha', 0)  # Make it fully transparent
    
    if sys.platform == "darwin":
        # Hide dock icon on macOS
        try:
            from AppKit import NSApp
            NSApp().setActivationPolicy_(1)  # NSApplicationActivationPolicyAccessory
        except ImportError:
            pass
            
    # Initialize GUI manager
    gui_manager = GUIManager(root, cache_manager, api_client)
    
    # Start the event loop
    root.mainloop()

if __name__ == "__main__":
    main()
