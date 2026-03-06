#!/usr/bin/env python3
"""Test the complete magnet link flow."""

import sys
import time
import threading
import queue

from pathlib import Path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from AppKit import NSPasteboard, NSPasteboardTypeString, NSString

def copy_to_clipboard(text):
    """Copy text to clipboard."""
    pasteboard = NSPasteboard.generalPasteboard()
    pasteboard.clearContents()
    pasteboard.setString_forType_(NSString.stringWithString_(text), NSPasteboardTypeString)
    print(f"✓ Copied to clipboard")

def test_queue_processing():
    """Test that queue processing works."""
    test_queue = queue.Queue()
    results = []
    
    def processor():
        """Process items from queue."""
        for i in range(5):
            try:
                item = test_queue.get(timeout=1)
                print(f"✓ Processing item: {item}")
                results.append(item)
            except queue.Empty:
                print(f"  Queue empty at iteration {i}")
    
    # Start processor thread
    processor_thread = threading.Thread(target=processor, daemon=True)
    processor_thread.start()
    
    # Add items to queue
    for i in range(3):
        test_queue.put(f"magnet_{i}")
        time.sleep(0.1)
    
    # Wait for processor
    processor_thread.join(timeout=2)
    
    print(f"\n✓ Processed {len(results)} items: {results}")
    assert len(results) == 3, "Should have processed 3 items"
    print("✓ Queue processing test passed!")

def test_clipboard_detection():
    """Test clipboard detection."""
    from CacheManager import CacheManager
    from APIClient import APIClient
    from MacOSGUIManager import MacOSGUIManager
    
    print("\n[TEST] Initializing MacOSGUIManager...")
    cache_manager = CacheManager()
    api_client = APIClient(cache_manager)
    gui_manager = MacOSGUIManager(cache_manager, api_client)
    
    print(f"✓ Manager initialized")
    print(f"✓ Clipboard monitoring enabled: {gui_manager.monitor_clipboard_enabled}")
    
    # Test clipboard detection manually
    print(f"\n[TEST] Testing clipboard detection...")
    magnet = "magnet:?xt=urn:btih:test123&dn=test"
    copy_to_clipboard(magnet)
    
    # Manually trigger detection
    gui_manager.check_clipboard()
    
    # Check if magnet was added to queue
    try:
        queued_magnet = gui_manager.magnet_queue.get_nowait()
        print(f"✓ Magnet added to queue: {queued_magnet[:40]}...")
        print("✓ Clipboard detection test passed!")
    except queue.Empty:
        print("✗ Magnet was not added to queue")
        return False
    
    return True

if __name__ == "__main__":
    try:
        print("=" * 50)
        print("Testing Queue Processing")
        print("=" * 50)
        test_queue_processing()
        
        print("\n" + "=" * 50)
        print("Testing Clipboard Detection")
        print("=" * 50)
        if test_clipboard_detection():
            print("\n✅ All tests passed!")
        else:
            print("\n❌ Tests failed")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
