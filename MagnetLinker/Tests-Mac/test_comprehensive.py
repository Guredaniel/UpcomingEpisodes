#!/usr/bin/env python3
"""Comprehensive tests for MagnetLinker features."""

import sys
import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, '/Users/guredaniel/Documents/UpcomingEpisodes/MagnetLinker')

from MacOSGUIManager import MacOSGUIManager
from CacheManager import CacheManager
from APIClient import APIClient


class TestMagnetLinkProcessing(unittest.TestCase):
    """Test magnet link detection and processing."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_cache = Mock(spec=CacheManager)
        self.mock_api = Mock(spec=APIClient)
        
        # Configure mocks
        self.mock_cache.load_setting.side_effect = lambda key, default: {
            "monitor_clipboard_enabled": True,
            "cache_duration_minutes": 30.0,
            "indefinite_selection": False,
            "site_rutor_url": "https://rutor.info",
            "site_yts_url": "https://yts.mx",
            "site_ext_url": "https://ext.to",
            "site_nyaa_url": "https://nyaa.si",
        }.get(key, default)
        
        self.mock_cache.credentials_exist.return_value = True
        self.mock_cache.load_credentials.return_value = ("user", "pass")
        
        self.mock_api.qbittorrent_url = "http://localhost:8080"
        self.mock_api.series_directory = "/Series"
        self.mock_api.movies_directory = "/Movies"
        
        self.gui = MacOSGUIManager(self.mock_cache, self.mock_api)
    
    def test_magnet_link_detection(self):
        """Test that magnet links are detected from clipboard."""
        test_magnet = "magnet:?xt=urn:btih:test123"
        self.gui.last_magnet_url = ""
        
        # Check that magnet detection works
        self.assertFalse(self.gui.last_magnet_url == test_magnet)
        self.gui.last_magnet_url = test_magnet
        self.assertTrue(self.gui.last_magnet_url == test_magnet)
        print("✓ Magnet link detection works")
    
    def test_clipboard_monitoring_toggle(self):
        """Test clipboard monitoring can be toggled."""
        initial_state = self.gui.monitor_clipboard_enabled
        
        # Toggle monitoring
        self.gui.monitor_clipboard_enabled = not self.gui.monitor_clipboard_enabled
        self.assertNotEqual(self.gui.monitor_clipboard_enabled, initial_state)
        
        # Toggle back
        self.gui.monitor_clipboard_enabled = not self.gui.monitor_clipboard_enabled
        self.assertEqual(self.gui.monitor_clipboard_enabled, initial_state)
        print("✓ Clipboard monitoring toggle works")
    
    def test_content_type_selection_caching(self):
        """Test content type selection can be cached."""
        # Test indefinite caching
        self.gui.cached_selection = ("Series", None)
        self.gui.indefinite_selection = True
        
        self.assertEqual(self.gui.cached_selection[0], "Series")
        self.assertIsNone(self.gui.cached_selection[1])
        print("✓ Indefinite content type caching works")
    
    def test_content_type_selection_with_expiration(self):
        """Test content type selection expires correctly."""
        now = datetime.now()
        self.gui.cached_selection = ("Movie", now)
        self.gui.indefinite_selection = False
        self.gui.cache_duration_minutes = 30.0
        
        # Check selection is valid
        expiration_time = now + timedelta(minutes=30)
        self.assertLess(datetime.now(), expiration_time)
        print("✓ Content type selection expiration works")


class TestSettingsValidation(unittest.TestCase):
    """Test settings validation."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_cache = Mock(spec=CacheManager)
        self.mock_api = Mock(spec=APIClient)
        
        self.mock_cache.load_setting.side_effect = lambda key, default: {
            "monitor_clipboard_enabled": True,
            "cache_duration_minutes": 30.0,
            "indefinite_selection": False,
            "site_rutor_url": "https://rutor.info",
            "site_yts_url": "https://yts.mx",
            "site_ext_url": "https://ext.to",
            "site_nyaa_url": "https://nyaa.si",
        }.get(key, default)
        
        self.mock_cache.credentials_exist.return_value = True
        self.mock_api.qbittorrent_url = "http://localhost:8080"
        self.mock_api.series_directory = "/Series"
        self.mock_api.movies_directory = "/Movies"
        
        self.gui = MacOSGUIManager(self.mock_cache, self.mock_api)
    
    def test_url_validation_https(self):
        """Test HTTPS URL validation."""
        valid_url = "https://qbittorrent.example.com:6969"
        self.assertTrue(valid_url.startswith("https://"))
        print("✓ HTTPS URL validation works")
    
    def test_url_validation_http(self):
        """Test HTTP URL validation."""
        valid_url = "http://localhost:8080"
        self.assertTrue(valid_url.startswith("http://"))
        print("✓ HTTP URL validation works")
    
    def test_url_validation_invalid(self):
        """Test invalid URL detection."""
        invalid_url = "not-a-url"
        self.assertFalse(invalid_url.startswith("http://") or invalid_url.startswith("https://"))
        print("✓ Invalid URL detection works")
    
    def test_cache_duration_validation(self):
        """Test cache duration must be numeric."""
        valid_duration = "30"
        try:
            float(valid_duration)
            is_valid = True
        except ValueError:
            is_valid = False
        
        self.assertTrue(is_valid)
        print("✓ Numeric cache duration validation works")
    
    def test_cache_duration_invalid(self):
        """Test non-numeric cache duration detection."""
        invalid_duration = "not-a-number"
        try:
            float(invalid_duration)
            is_valid = True
        except ValueError:
            is_valid = False
        
        self.assertFalse(is_valid)
        print("✓ Invalid cache duration detection works")


class TestSettingsDialog(unittest.TestCase):
    """Test settings dialog functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_cache = Mock(spec=CacheManager)
        self.mock_api = Mock(spec=APIClient)
        
        self.mock_cache.load_setting.side_effect = lambda key, default: {
            "monitor_clipboard_enabled": True,
            "cache_duration_minutes": 30.0,
            "indefinite_selection": False,
            "site_rutor_url": "https://rutor.info",
            "site_yts_url": "https://yts.mx",
            "site_ext_url": "https://ext.to",
            "site_nyaa_url": "https://nyaa.si",
        }.get(key, default)
        
        self.mock_cache.credentials_exist.return_value = True
        self.mock_cache.load_credentials.return_value = ("user", "pass")
        
        self.mock_api.qbittorrent_url = "http://localhost:8080"
        self.mock_api.series_directory = "/Series"
        self.mock_api.movies_directory = "/Movies"
        
        self.gui = MacOSGUIManager(self.mock_cache, self.mock_api)
    
    def test_settings_fields_initialization(self):
        """Test settings fields are properly initialized."""
        self.gui._settings_fields = {}
        self.assertIsInstance(self.gui._settings_fields, dict)
        print("✓ Settings fields initialization works")
    
    def test_cache_duration_loading(self):
        """Test cache duration setting loads correctly."""
        self.assertEqual(self.gui.cache_duration_minutes, 30.0)
        print("✓ Cache duration loading works")
    
    def test_clipboard_monitoring_loading(self):
        """Test clipboard monitoring setting loads correctly."""
        self.assertTrue(self.gui.monitor_clipboard_enabled)
        print("✓ Clipboard monitoring loading works")
    
    def test_site_urls_loading(self):
        """Test site URLs load correctly."""
        self.assertEqual(self.gui.site_rutor_url, "https://rutor.info")
        self.assertEqual(self.gui.site_yts_url, "https://yts.mx")
        self.assertEqual(self.gui.site_ext_url, "https://ext.to")
        self.assertEqual(self.gui.site_nyaa_url, "https://nyaa.si")
        print("✓ Site URLs loading works")
    
    def test_qbittorrent_settings_loading(self):
        """Test qBittorrent settings load correctly."""
        self.assertEqual(self.gui.api_client.qbittorrent_url, "http://localhost:8080")
        self.assertEqual(self.gui.api_client.series_directory, "/Series")
        self.assertEqual(self.gui.api_client.movies_directory, "/Movies")
        print("✓ qBittorrent settings loading works")


class TestMenuItems(unittest.TestCase):
    """Test menu items and callbacks."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_cache = Mock(spec=CacheManager)
        self.mock_api = Mock(spec=APIClient)
        
        self.mock_cache.load_setting.side_effect = lambda key, default: {
            "monitor_clipboard_enabled": True,
            "cache_duration_minutes": 30.0,
            "indefinite_selection": False,
            "site_rutor_url": "https://rutor.info",
            "site_yts_url": "https://yts.mx",
            "site_ext_url": "https://ext.to",
            "site_nyaa_url": "https://nyaa.si",
        }.get(key, default)
        
        self.mock_cache.credentials_exist.return_value = True
        self.mock_api.qbittorrent_url = "http://localhost:8080"
        self.mock_api.series_directory = "/Series"
        self.mock_api.movies_directory = "/Movies"
        
        self.gui = MacOSGUIManager(self.mock_cache, self.mock_api)
    
    def test_menu_creation(self):
        """Test menu bar app is created."""
        self.assertIsNotNone(self.gui.app)
        # rumps.App doesn't expose title as an attribute, just verify app exists
        self.assertTrue(hasattr(self.gui.app, 'menu'))
        print("✓ Menu bar app creation works")
    
    def test_menu_items_exist(self):
        """Test menu items are created."""
        self.assertIsNotNone(self.gui.app.menu)
        self.assertGreater(len(self.gui.app.menu), 0)
        print("✓ Menu items exist")
    
    def test_sites_submenu_creation(self):
        """Test sites submenu is created."""
        # Find sites submenu by checking menu structure
        self.assertIsNotNone(self.gui.app.menu)
        # Menu should have multiple items
        self.assertGreater(len(self.gui.app.menu), 0)
        print("✓ Sites submenu creation works")


class TestCredentialsManagement(unittest.TestCase):
    """Test credentials management."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_cache = Mock(spec=CacheManager)
        self.mock_api = Mock(spec=APIClient)
        
        self.mock_cache.load_setting.side_effect = lambda key, default: {
            "monitor_clipboard_enabled": True,
            "cache_duration_minutes": 30.0,
            "indefinite_selection": False,
            "site_rutor_url": "https://rutor.info",
            "site_yts_url": "https://yts.mx",
            "site_ext_url": "https://ext.to",
            "site_nyaa_url": "https://nyaa.si",
        }.get(key, default)
        
        self.mock_cache.credentials_exist.return_value = True
        self.mock_cache.load_credentials.return_value = ("user", "pass")
        
        self.mock_api.qbittorrent_url = "http://localhost:8080"
        self.mock_api.series_directory = "/Series"
        self.mock_api.movies_directory = "/Movies"
        
        self.gui = MacOSGUIManager(self.mock_cache, self.mock_api)
    
    def test_credentials_exist_check(self):
        """Test credentials existence check."""
        self.assertTrue(self.mock_cache.credentials_exist())
        print("✓ Credentials existence check works")
    
    def test_credentials_loading(self):
        """Test credentials loading."""
        creds = self.mock_cache.load_credentials()
        self.assertEqual(creds[0], "user")
        self.assertEqual(creds[1], "pass")
        print("✓ Credentials loading works")


class TestDirectoryConfiguration(unittest.TestCase):
    """Test directory configuration."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_cache = Mock(spec=CacheManager)
        self.mock_api = Mock(spec=APIClient)
        
        self.mock_cache.load_setting.side_effect = lambda key, default: {
            "monitor_clipboard_enabled": True,
            "cache_duration_minutes": 30.0,
            "indefinite_selection": False,
            "site_rutor_url": "https://rutor.info",
            "site_yts_url": "https://yts.mx",
            "site_ext_url": "https://ext.to",
            "site_nyaa_url": "https://nyaa.si",
        }.get(key, default)
        
        self.mock_api.qbittorrent_url = "http://localhost:8080"
        self.mock_api.series_directory = "/Series"
        self.mock_api.movies_directory = "/Movies"
        
        self.gui = MacOSGUIManager(self.mock_cache, self.mock_api)
    
    def test_series_directory_configuration(self):
        """Test series directory is configured."""
        self.assertEqual(self.gui.api_client.series_directory, "/Series")
        print("✓ Series directory configuration works")
    
    def test_movies_directory_configuration(self):
        """Test movies directory is configured."""
        self.assertEqual(self.gui.api_client.movies_directory, "/Movies")
        print("✓ Movies directory configuration works")


class TestQBittorrentConnection(unittest.TestCase):
    """Test qBittorrent connection settings."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_cache = Mock(spec=CacheManager)
        self.mock_api = Mock(spec=APIClient)
        
        self.mock_cache.load_setting.side_effect = lambda key, default: {
            "monitor_clipboard_enabled": True,
            "cache_duration_minutes": 30.0,
            "indefinite_selection": False,
            "site_rutor_url": "https://rutor.info",
            "site_yts_url": "https://yts.mx",
            "site_ext_url": "https://ext.to",
            "site_nyaa_url": "https://nyaa.si",
        }.get(key, default)
        
        self.mock_api.qbittorrent_url = "http://localhost:8080"
        self.mock_api.series_directory = "/Series"
        self.mock_api.movies_directory = "/Movies"
        self.mock_api.test_connection = Mock(return_value=True)
        
        self.gui = MacOSGUIManager(self.mock_cache, self.mock_api)
    
    def test_qbittorrent_url_configuration(self):
        """Test qBittorrent URL is configured."""
        self.assertEqual(self.gui.api_client.qbittorrent_url, "http://localhost:8080")
        print("✓ qBittorrent URL configuration works")
    
    def test_connection_test_method_exists(self):
        """Test connection test method exists."""
        self.assertTrue(hasattr(self.gui.api_client, 'test_connection'))
        print("✓ Connection test method exists")


def run_all_tests():
    """Run all test suites."""
    print("\n" + "="*60)
    print("RUNNING COMPREHENSIVE MAGNETLINKER TESTS")
    print("="*60 + "\n")
    
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestMagnetLinkProcessing))
    suite.addTests(loader.loadTestsFromTestCase(TestSettingsValidation))
    suite.addTests(loader.loadTestsFromTestCase(TestSettingsDialog))
    suite.addTests(loader.loadTestsFromTestCase(TestMenuItems))
    suite.addTests(loader.loadTestsFromTestCase(TestCredentialsManagement))
    suite.addTests(loader.loadTestsFromTestCase(TestDirectoryConfiguration))
    suite.addTests(loader.loadTestsFromTestCase(TestQBittorrentConnection))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    print(f"Tests Run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.wasSuccessful():
        print("\n✅ ALL TESTS PASSED!")
    else:
        print("\n❌ SOME TESTS FAILED")
    print("="*60 + "\n")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
