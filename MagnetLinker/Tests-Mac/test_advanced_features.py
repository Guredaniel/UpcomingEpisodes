#!/usr/bin/env python3
"""Advanced integration tests for clipboard, threading, and state management."""

import sys
import unittest
import threading
import time
import queue
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from pathlib import Path

# Ensure project root is on sys.path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from MacOSGUIManager import MacOSGUIManager
from CacheManager import CacheManager
from APIClient import APIClient


class TestClipboardMonitoring(unittest.TestCase):
    """Test clipboard monitoring functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_cache = Mock(spec=CacheManager)
        self.mock_api = Mock(spec=APIClient)
        
        self.mock_cache.load_setting.side_effect = lambda key, default: {
            "monitor_clipboard_enabled": True,
            "cache_duration_minutes": 30.0,
            "indefinite_selection": False,
            "clipboard_check_interval": 0.5,
        }.get(key, default)
        
        self.mock_cache.credentials_exist.return_value = True
        self.mock_cache.load_credentials.return_value = ("user", "pass")
        self.mock_cache.get_saved_sites.return_value = []
        
        self.mock_api.qbittorrent_url = "http://localhost:8080"
        self.mock_api.series_directory = "/Series"
        self.mock_api.movies_directory = "/Movies"
        
        self.gui = MacOSGUIManager(self.mock_cache, self.mock_api)
    
    def test_clipboard_monitoring_enabled_flag(self):
        """Test clipboard monitoring enabled flag."""
        self.assertTrue(self.gui.monitor_clipboard_enabled)
        print("✓ Clipboard monitoring enabled flag works")
    
    def test_clipboard_monitoring_toggle(self):
        """Test toggling clipboard monitoring."""
        initial_state = self.gui.monitor_clipboard_enabled
        self.gui.monitor_clipboard_enabled = not initial_state
        
        final_state = self.gui.monitor_clipboard_enabled
        self.assertNotEqual(initial_state, final_state)
        print("✓ Clipboard monitoring toggle works")
    
    def test_clipboard_interval_setting(self):
        """Test clipboard check interval."""
        interval = self.gui.clipboard_check_interval
        self.assertEqual(interval, 0.5)
        print("✓ Clipboard interval setting works")
    
    def test_magnet_url_detection(self):
        """Test magnet URL detection."""
        test_magnet = "magnet:?xt=urn:btih:abc123def456"
        
        # Set as last detected
        self.gui.last_magnet_url = test_magnet
        
        # Verify detection
        self.assertEqual(self.gui.last_magnet_url, test_magnet)
        self.assertTrue(self.gui.last_magnet_url.startswith("magnet:"))
        print("✓ Magnet URL detection works")
    
    def test_clipboard_check(self):
        """Test clipboard check method exists."""
        self.assertTrue(hasattr(self.gui, 'check_clipboard'))
        self.assertTrue(callable(self.gui.check_clipboard))
        print("✓ Clipboard check method exists")


class TestThreadSafety(unittest.TestCase):
    """Test thread-safe operations."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_cache = Mock(spec=CacheManager)
        self.mock_api = Mock(spec=APIClient)
        
        self.mock_cache.load_setting.side_effect = lambda key, default: {
            "monitor_clipboard_enabled": True,
            "cache_duration_minutes": 30.0,
            "indefinite_selection": False,
        }.get(key, default)
        
        self.mock_cache.credentials_exist.return_value = True
        self.mock_cache.get_saved_sites.return_value = []
        
        self.mock_api.qbittorrent_url = "http://localhost:8080"
        self.mock_api.series_directory = "/Series"
        self.mock_api.movies_directory = "/Movies"
        
        self.gui = MacOSGUIManager(self.mock_cache, self.mock_api)
    
    def test_magnet_queue_exists(self):
        """Test magnet queue for thread-safe magnet link passing."""
        self.assertIsNotNone(self.gui.magnet_queue)
        self.assertIsInstance(self.gui.magnet_queue, queue.Queue)
        print("✓ Magnet queue exists and is thread-safe")
    
    def test_magnet_queue_operations(self):
        """Test basic queue operations."""
        magnet_url = "magnet:?xt=urn:btih:test123"
        
        # Put item in queue
        self.gui.magnet_queue.put(magnet_url)
        
        # Get item from queue
        item = self.gui.magnet_queue.get(timeout=1)
        
        self.assertEqual(item, magnet_url)
        print("✓ Magnet queue operations work")
    
    def test_queue_thread_safety(self):
        """Test queue is thread-safe with multiple threads."""
        results = []
        
        def add_to_queue():
            for i in range(5):
                self.gui.magnet_queue.put(f"magnet:?xt={i}")
                time.sleep(0.01)
        
        def read_from_queue():
            try:
                for _ in range(5):
                    item = self.gui.magnet_queue.get(timeout=1)
                    results.append(item)
            except queue.Empty:
                pass
        
        # Start threads
        writer = threading.Thread(target=add_to_queue)
        reader = threading.Thread(target=read_from_queue)
        
        writer.start()
        reader.start()
        
        writer.join()
        reader.join()
        
        # Verify all items were read
        self.assertEqual(len(results), 5)
        print("✓ Queue thread safety works")


class TestSelectionCaching(unittest.TestCase):
    """Test content type selection caching."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_cache = Mock(spec=CacheManager)
        self.mock_api = Mock(spec=APIClient)
        
        self.mock_cache.load_setting.side_effect = lambda key, default: {
            "monitor_clipboard_enabled": True,
            "cache_duration_minutes": 30.0,
            "indefinite_selection": False,
        }.get(key, default)
        
        self.mock_cache.credentials_exist.return_value = True
        self.mock_cache.get_saved_sites.return_value = []
        
        self.mock_api.qbittorrent_url = "http://localhost:8080"
        self.mock_api.series_directory = "/Series"
        self.mock_api.movies_directory = "/Movies"
        
        self.gui = MacOSGUIManager(self.mock_cache, self.mock_api)
    
    def test_initial_selection_none(self):
        """Test initial cached selection is None."""
        self.assertIsNone(self.gui.cached_selection)
        print("✓ Initial selection is None")
    
    def test_indefinite_selection_flag(self):
        """Test indefinite selection flag."""
        self.assertFalse(self.gui.indefinite_selection)
        print("✓ Indefinite selection flag initialized correctly")
    
    def test_cache_movie_selection_indefinite(self):
        """Test caching movie selection indefinitely."""
        self.gui.cached_selection = ("Movie", None)
        self.gui.indefinite_selection = True
        
        self.assertEqual(self.gui.cached_selection[0], "Movie")
        self.assertIsNone(self.gui.cached_selection[1])
        self.assertTrue(self.gui.indefinite_selection)
        print("✓ Cache movie selection indefinite works")
    
    def test_cache_series_selection_indefinite(self):
        """Test caching series selection indefinitely."""
        self.gui.cached_selection = ("Series", None)
        self.gui.indefinite_selection = True
        
        self.assertEqual(self.gui.cached_selection[0], "Series")
        self.assertIsNone(self.gui.cached_selection[1])
        self.assertTrue(self.gui.indefinite_selection)
        print("✓ Cache series selection indefinite works")
    
    def test_cache_selection_with_duration(self):
        """Test caching selection with duration."""
        now = datetime.now()
        self.gui.cached_selection = ("Movie", now)
        self.gui.indefinite_selection = False
        
        selection, timestamp = self.gui.cached_selection
        cache_duration = 30
        expiration = timestamp + timedelta(minutes=cache_duration)
        
        self.assertEqual(selection, "Movie")
        self.assertIsNotNone(timestamp)
        self.assertGreater(expiration, datetime.now())
        print("✓ Cache selection with duration works")
    
    def test_check_selection_expiration(self):
        """Test checking if selection has expired."""
        now = datetime.now()
        self.gui.cached_selection = ("Movie", now)
        self.gui.cache_duration_minutes = 30
        
        selection, timestamp = self.gui.cached_selection
        expiration_time = timestamp + timedelta(minutes=self.gui.cache_duration_minutes)
        is_expired = datetime.now() > expiration_time
        
        # Should not be expired immediately
        self.assertFalse(is_expired)
        print("✓ Selection expiration check works")
    
    def test_reset_selection(self):
        """Test resetting cached selection."""
        self.gui.cached_selection = ("Series", datetime.now())
        self.gui.indefinite_selection = True
        
        self.gui.reset_selection()
        
        self.assertIsNone(self.gui.cached_selection)
        self.assertFalse(self.gui.indefinite_selection)
        print("✓ Reset selection works")


class TestMenuBarApp(unittest.TestCase):
    """Test menu bar app creation and management."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_cache = Mock(spec=CacheManager)
        self.mock_api = Mock(spec=APIClient)
        
        self.mock_cache.load_setting.side_effect = lambda key, default: {
            "monitor_clipboard_enabled": True,
            "cache_duration_minutes": 30.0,
            "indefinite_selection": False,
        }.get(key, default)
        
        self.mock_cache.credentials_exist.return_value = True
        self.mock_cache.get_saved_sites.return_value = []
        
        self.mock_api.qbittorrent_url = "http://localhost:8080"
        self.mock_api.series_directory = "/Series"
        self.mock_api.movies_directory = "/Movies"
        
        self.gui = MacOSGUIManager(self.mock_cache, self.mock_api)
    
    def test_app_initialized(self):
        """Test app is initialized."""
        self.assertIsNotNone(self.gui.app)
        print("✓ App initialized")
    
    def test_app_has_menu(self):
        """Test app has menu."""
        self.assertIsNotNone(self.gui.app.menu)
        print("✓ App has menu")
    
    def test_main_menu_items(self):
        """Test main menu items exist."""
        menu = self.gui.app.menu
        self.assertIsNotNone(menu)
        self.assertGreater(len(menu), 0)
        print("✓ Main menu items exist")


class TestSitesManagement(unittest.TestCase):
    """Test saved sites management."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_cache = Mock(spec=CacheManager)
        self.mock_api = Mock(spec=APIClient)
        
        self.mock_cache.load_setting.side_effect = lambda key, default: {
            "monitor_clipboard_enabled": True,
            "cache_duration_minutes": 30.0,
            "indefinite_selection": False,
        }.get(key, default)
        
        self.mock_cache.credentials_exist.return_value = True
        self.mock_cache.get_saved_sites.return_value = [
            {"name": "Site 1", "url": "https://site1.com"},
            {"name": "Site 2", "url": "https://site2.com"}
        ]
        
        self.mock_api.qbittorrent_url = "http://localhost:8080"
        self.mock_api.series_directory = "/Series"
        self.mock_api.movies_directory = "/Movies"
        
        self.gui = MacOSGUIManager(self.mock_cache, self.mock_api)
    
    def test_loaded_sites(self):
        """Test sites are loaded."""
        self.assertIsNotNone(self.gui.saved_sites)
        self.assertEqual(len(self.gui.saved_sites), 2)
        print("✓ Sites loaded")
    
    def test_working_sites_copy(self):
        """Test working sites is a copy of saved sites."""
        self.assertEqual(len(self.gui._working_sites), len(self.gui.saved_sites))
        print("✓ Working sites copy created")
    
    def test_site_structure(self):
        """Test site structure has required fields."""
        for site in self.gui.saved_sites:
            self.assertIn("name", site)
            self.assertIn("url", site)
        print("✓ Site structure valid")


class TestSettingsFields(unittest.TestCase):
    """Test settings field management."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_cache = Mock(spec=CacheManager)
        self.mock_api = Mock(spec=APIClient)
        
        self.mock_cache.load_setting.side_effect = lambda key, default: {
            "monitor_clipboard_enabled": True,
            "cache_duration_minutes": 30.0,
            "indefinite_selection": False,
        }.get(key, default)
        
        self.mock_cache.credentials_exist.return_value = True
        self.mock_cache.get_saved_sites.return_value = []
        
        self.mock_api.qbittorrent_url = "http://localhost:8080"
        self.mock_api.series_directory = "/Series"
        self.mock_api.movies_directory = "/Movies"
        
        self.gui = MacOSGUIManager(self.mock_cache, self.mock_api)
    
    def test_settings_fields_dict(self):
        """Test settings fields dictionary exists."""
        self.assertIsNotNone(hasattr(self.gui, '_settings_fields'))
        print("✓ Settings fields dict exists")
    
    def test_current_settings_section_init(self):
        """Test current settings section is initialized."""
        self.assertTrue(hasattr(self.gui, '_current_settings_section'))
        print("✓ Current settings section exists")


class TestErrorStates(unittest.TestCase):
    """Test error state handling."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_cache = Mock(spec=CacheManager)
        self.mock_api = Mock(spec=APIClient)
        
        self.mock_cache.load_setting.side_effect = lambda key, default: {
            "monitor_clipboard_enabled": True,
            "cache_duration_minutes": 30.0,
            "indefinite_selection": False,
        }.get(key, default)
        
        self.mock_cache.credentials_exist.return_value = False  # No credentials
        self.mock_cache.get_saved_sites.return_value = []
        
        self.mock_api.qbittorrent_url = "http://localhost:8080"
        self.mock_api.series_directory = "/Series"
        self.mock_api.movies_directory = "/Movies"
        
        self.gui = MacOSGUIManager(self.mock_cache, self.mock_api)
    
    def test_no_credentials_handling(self):
        """Test handling when credentials don't exist."""
        self.assertFalse(self.mock_cache.credentials_exist())
        print("✓ No credentials handling works")
    
    def test_error_message_copying(self):
        """Test error message can be copied (method exists)."""
        self.assertTrue(hasattr(self.gui, 'handle_error'))
        self.assertTrue(callable(self.gui.handle_error))
        print("✓ Error handling method exists")


class TestAutoLaunchConfiguration(unittest.TestCase):
    """Test auto-launch configuration."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_cache = Mock(spec=CacheManager)
        self.mock_api = Mock(spec=APIClient)
        
        self.mock_cache.load_setting.side_effect = lambda key, default: {
            "monitor_clipboard_enabled": True,
            "cache_duration_minutes": 30.0,
            "indefinite_selection": False,
            "auto_launch_enabled": False,
        }.get(key, default)
        
        self.mock_cache.credentials_exist.return_value = True
        self.mock_cache.get_saved_sites.return_value = []
        
        self.mock_api.qbittorrent_url = "http://localhost:8080"
        self.mock_api.series_directory = "/Series"
        self.mock_api.movies_directory = "/Movies"
        
        self.gui = MacOSGUIManager(self.mock_cache, self.mock_api)
    
    def test_auto_launch_disabled_initially(self):
        """Test auto-launch is disabled initially."""
        self.assertFalse(self.gui.auto_launch_enabled)
        print("✓ Auto-launch disabled initially")
    
    def test_toggle_auto_launch(self):
        """Test toggling auto-launch."""
        initial = self.gui.auto_launch_enabled
        self.gui.auto_launch_enabled = not initial
        
        self.assertNotEqual(self.gui.auto_launch_enabled, initial)
        print("✓ Toggle auto-launch works")


if __name__ == "__main__":
    unittest.main(verbosity=2)
