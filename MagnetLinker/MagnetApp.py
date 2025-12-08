import sys
from customtkinter import CTk
from CacheManager import CacheManager
from APIClient import APIClient
from GUIManager import GUIManager

def main():
    cache_manager = CacheManager()
    api_client = APIClient(cache_manager)

    if sys.platform == "darwin":
        # Use native macOS GUI with rumps menu bar
        try:
            from MacOSGUIManager import MacOSGUIManager
            gui_manager = MacOSGUIManager(cache_manager, api_client)
            gui_manager.run()
        except ImportError:
            # Fall back to regular GUI if MacOSGUIManager is not available
            print("Warning: MacOSGUIManager not available, using fallback GUI")
            root = CTk()
            root.withdraw()
            root.overrideredirect(True)
            root.attributes('-alpha', 0)
            root.attributes('-topmost', True)
            
            try:
                from AppKit import NSApp
                NSApp().setActivationPolicy_(1)
            except ImportError:
                pass
            
            gui_manager = GUIManager(root, cache_manager, api_client)
            root.mainloop()
    else:
        # Use cross-platform GUI for Windows/Linux
        root = CTk()
        root.withdraw()
        root.overrideredirect(True)
        root.attributes('-alpha', 0)
        root.attributes('-topmost', True)
        
        gui_manager = GUIManager(root, cache_manager, api_client)
        root.mainloop()

if __name__ == "__main__":
    main()
