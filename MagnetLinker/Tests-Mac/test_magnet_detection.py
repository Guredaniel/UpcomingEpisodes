#!/usr/bin/env python3
"""Test the magnet link detection with the actual MacOSGUIManager."""

import sys
import time
from pathlib import Path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from CacheManager import CacheManager
from APIClient import APIClient
from MacOSGUIManager import MacOSGUIManager

def test_magnet_detection():
    """Test that magnet links are detected from clipboard."""
    print("Initializing MagnetLinker...")
    
    cache_manager = CacheManager()
    api_client = APIClient(cache_manager)
    
    print("Creating MacOSGUIManager...")
    gui_manager = MacOSGUIManager(cache_manager, api_client)
    
    print("Clipboard monitoring enabled:", gui_manager.monitor_clipboard_enabled)
    print("Waiting for magnet link to be copied to clipboard...")
    print("Copy this magnet link:")
    print("magnet:?xt=urn:btih:c1c38309768655cf951908fb72ea6fb5faa3ed38&dn=test")
    print()
    
    # Monitor clipboard for 30 seconds
    for i in range(60):
        try:
            gui_manager.check_clipboard()
            if i % 10 == 0:
                print(f"[{i}s] Monitoring clipboard...")
            time.sleep(0.5)
        except KeyboardInterrupt:
            print("\nStopped.")
            break
        except Exception as e:
            print(f"Error during monitoring: {e}")

if __name__ == "__main__":
    test_magnet_detection()
