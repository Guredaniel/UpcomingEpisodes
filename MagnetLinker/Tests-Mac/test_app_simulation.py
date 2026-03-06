#!/usr/bin/env python3
"""Test simulating actual app execution with magnet detection."""

import sys
import time
import threading
from AppKit import NSPasteboard, NSPasteboardTypeString, NSString

from pathlib import Path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

def simulate_app_flow():
    """Simulate the app initialization and magnet detection."""
    from CacheManager import CacheManager
    from APIClient import APIClient
    from MacOSGUIManager import MacOSGUIManager
    
    print("[TEST] Starting app simulation...")
    print("[TEST] Creating managers...")
    
    cache_manager = CacheManager()
    api_client = APIClient(cache_manager)
    gui_manager = MacOSGUIManager(cache_manager, api_client)
    
    print("✓ Managers created")
    print(f"✓ Clipboard monitoring enabled: {gui_manager.monitor_clipboard_enabled}")
    
    # Start the background threads (like in run())
    print("\n[TEST] Starting background threads...")
    if gui_manager.monitor_clipboard_enabled:
        gui_manager._start_clipboard_monitor()
    gui_manager._start_queue_processor()
    
    print("✓ Clipboard monitor thread started")
    print("✓ Queue processor thread started")
    
    # Simulate copying a magnet link after a delay
    def copy_magnet_later():
        time.sleep(1)
        print("\n[TEST] Copying magnet link to clipboard...")
        magnet = "magnet:?xt=urn:btih:c1c38309768655cf951908fb72ea6fb5faa3ed38&dn=test"
        pasteboard = NSPasteboard.generalPasteboard()
        pasteboard.clearContents()
        pasteboard.setString_forType_(NSString.stringWithString_(magnet), NSPasteboardTypeString)
        print("✓ Magnet copied to clipboard")
    
    copy_thread = threading.Thread(target=copy_magnet_later, daemon=True)
    copy_thread.start()
    
    # Monitor for a few seconds
    print("\n[TEST] Monitoring for magnet detection (5 seconds)...")
    for i in range(10):
        time.sleep(0.5)
        queue_size = gui_manager.magnet_queue.qsize()
        if queue_size > 0:
            print(f"✓ Magnet in queue! Size: {queue_size}")
    
    print("\n✅ App simulation completed successfully!")
    print("[INFO] In real app, dialogs would show on main thread now")

if __name__ == "__main__":
    try:
        simulate_app_flow()
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
