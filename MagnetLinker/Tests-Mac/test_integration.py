#!/usr/bin/env python3
"""Integration test for magnet link detection."""

import sys
import time
import threading
from AppKit import NSPasteboard, NSPasteboardTypeString, NSString

# Add the project to path
from pathlib import Path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

def copy_to_clipboard(text):
    """Copy text to clipboard."""
    pasteboard = NSPasteboard.generalPasteboard()
    pasteboard.clearContents()
    pasteboard.setString_forType_(NSString.stringWithString_(text), NSPasteboardTypeString)
    print(f"[TEST] Copied to clipboard: {text[:50]}...")

def test_clipboard_detection():
    """Test the clipboard detection."""
    from CacheManager import CacheManager
    from APIClient import APIClient
    from MacOSGUIManager import MacOSGUIManager
    
    print("[TEST] Starting clipboard detection test...")
    
    cache_manager = CacheManager()
    api_client = APIClient(cache_manager)
    gui_manager = MacOSGUIManager(cache_manager, api_client)
    
    print(f"[TEST] Clipboard monitoring enabled: {gui_manager.monitor_clipboard_enabled}")
    print(f"[TEST] Starting manual clipboard monitor thread...")
    
    # Start monitoring in a separate thread
    def monitor_for_test():
        for i in range(20):  # Check for 10 seconds (0.5s * 20)
            try:
                gui_manager.check_clipboard()
                if i % 2 == 0:
                    print(f"[TEST] Checking clipboard... ({i*0.5}s)")
                time.sleep(0.5)
            except Exception as e:
                print(f"[TEST] Error during monitoring: {e}")
                import traceback
                traceback.print_exc()
    
    monitor_thread = threading.Thread(target=monitor_for_test, daemon=True)
    monitor_thread.start()
    
    # Give it a moment to start
    time.sleep(1)
    
    # Copy a magnet link to clipboard
    magnet_link = "magnet:?xt=urn:btih:c1c38309768655cf951908fb72ea6fb5faa3ed38&dn=rutor.info_test"
    print(f"[TEST] About to copy magnet link to clipboard...")
    copy_to_clipboard(magnet_link)
    print(f"[TEST] Magnet link copied. Waiting for detection...")
    
    # Wait for thread to complete
    monitor_thread.join(timeout=15)
    print("[TEST] Test completed!")

if __name__ == "__main__":
    try:
        test_clipboard_detection()
    except Exception as e:
        print(f"[TEST] Test failed with error: {e}")
        import traceback
        traceback.print_exc()
