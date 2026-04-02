"""Main application entry point for MagnetLinker."""

from __future__ import annotations

import sys
import logging

from customtkinter import CTk

from CacheManager import CacheManager
from APIClient import APIClient
from GUIManager import GUIManager

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def main() -> None:
    """Initialize and run the application."""
    cache_manager = CacheManager()
    api_client = APIClient(cache_manager)

    if sys.platform == "darwin":
        # Use native macOS GUI with rumps menu bar
        try:
            from MacOSGUIManager import MacOSGUIManager

            gui_manager = MacOSGUIManager(cache_manager, api_client)
            gui_manager.run()
        except ImportError as e:
            # Fall back to regular GUI if MacOSGUIManager is not available
            logger.warning(f"MacOSGUIManager not available, using fallback GUI: {e}")
            root = CTk()
            root.withdraw()
            root.overrideredirect(True)
            root.attributes("-alpha", 0)
            root.attributes("-topmost", True)
            
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
        root.attributes("-alpha", 0)
        root.attributes("-topmost", True)
        
        gui_manager = GUIManager(root, cache_manager, api_client)
        root.mainloop()


if __name__ == "__main__":
    main()
