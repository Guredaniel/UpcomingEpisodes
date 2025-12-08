#!/usr/bin/env python3
"""Test script to verify clipboard monitoring."""

import time
from AppKit import NSPasteboard, NSPasteboardTypeString

def check_clipboard():
    """Monitor clipboard for magnet links."""
    last_magnet = ""
    try:
        pasteboard = NSPasteboard.generalPasteboard()
        clipboard_content = pasteboard.stringForType_(NSPasteboardTypeString)
        
        if clipboard_content:
            clipboard_str = str(clipboard_content)
            print(f"[DEBUG] Clipboard content: {clipboard_str[:80]}...")
            if (clipboard_str.startswith("magnet:") and 
                clipboard_str != last_magnet):
                print(f"[DEBUG] NEW MAGNET LINK DETECTED!")
                last_magnet = clipboard_str
                return True
    except Exception as e:
        print(f"[ERROR] {e}")
    return False

if __name__ == "__main__":
    print("Clipboard monitor test - waiting for magnet links...")
    print("Copy a magnet link to your clipboard and the script will detect it.")
    print()
    
    try:
        while True:
            check_clipboard()
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nStopped.")
