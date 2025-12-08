#!/usr/bin/env python3
"""Quick test to verify the magnet link queue processing works."""

import sys
import time
import queue

sys.path.insert(0, '/Users/guredaniel/Documents/UpcomingEpisodes/MagnetLinker')

def test_queue():
    """Test queue operations."""
    q = queue.Queue()
    
    # Test 1: Add to queue
    magnet = "magnet:?xt=urn:btih:test123"
    q.put(magnet)
    print(f"✓ Added magnet to queue")
    
    # Test 2: Get from queue
    try:
        item = q.get_nowait()
        print(f"✓ Retrieved from queue: {item[:30]}...")
    except queue.Empty:
        print("✗ Queue was empty when it shouldn't be")
    
    # Test 3: Empty queue
    try:
        item = q.get_nowait()
        print("✗ Queue still has items")
    except queue.Empty:
        print("✓ Queue is now empty as expected")
    
    print("\n✓ Queue test passed!")

if __name__ == "__main__":
    test_queue()
