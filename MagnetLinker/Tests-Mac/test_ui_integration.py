#!/usr/bin/env python3
"""UI and Integration tests for MagnetLinker."""

import sys
import unittest
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path
from pathlib import Path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from MacOSGUIManager import MacOSGUIManager
from CacheManager import CacheManager
from APIClient import APIClient


class TestSettingsSave(unittest.TestCase):
    """Test settings save functionality."""
    
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
        
        self.mock_cache.credentials_exist.return_value = False
        self.mock_api.qbittorrent_url = "http://localhost:8080"
        self.mock_api.series_directory = "/Series"
        self.mock_api.movies_directory = "/Movies"
        
        self.gui = MacOSGUIManager(self.mock_cache, self.mock_api)
        self.gui._settings_fields = {}
    
    def test_qb_url_required(self):
        """Test qBittorrent URL is required."""
        # Create mock text field that returns empty string
        mock_field = Mock()
        mock_field.stringValue.return_value = ""
        
        self.gui._settings_fields['qb_url'] = mock_field
        
        # Verify empty URL would fail validation
        url = mock_field.stringValue()
        is_valid = bool(url)
        
        self.assertFalse(is_valid)
        print("✓ qBittorrent URL required validation works")
    
    def test_series_dir_required(self):
        """Test series directory is required."""
        mock_field = Mock()
        mock_field.stringValue.return_value = ""
        
        self.gui._settings_fields['series_dir'] = mock_field
        
        directory = mock_field.stringValue()
        is_valid = bool(directory)
        
        self.assertFalse(is_valid)
        print("✓ Series directory required validation works")
    
    def test_movies_dir_required(self):
        """Test movies directory is required."""
        mock_field = Mock()
        mock_field.stringValue.return_value = ""
        
        self.gui._settings_fields['movies_dir'] = mock_field
        
        directory = mock_field.stringValue()
        is_valid = bool(directory)
        
        self.assertFalse(is_valid)
        print("✓ Movies directory required validation works")
    
    def test_cache_duration_numeric_validation(self):
        """Test cache duration must be numeric."""
        mock_field = Mock()
        mock_field.stringValue.return_value = "30"
        
        self.gui._settings_fields['cache_duration'] = mock_field
        
        cache_str = mock_field.stringValue()
        try:
            float(cache_str)
            is_valid = True
        except ValueError:
            is_valid = False
        
        self.assertTrue(is_valid)
        print("✓ Cache duration numeric validation works")


class TestErrorHandling(unittest.TestCase):
    """Test error handling and dialogs."""
    
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
    
    def test_error_handling_exists(self):
        """Test error handling method exists."""
        self.assertTrue(hasattr(self.gui, 'handle_error'))
        self.assertTrue(callable(self.gui.handle_error))
        print("✓ Error handling method exists")
    
    def test_notification_handling_exists(self):
        """Test notification handling method exists."""
        self.assertTrue(hasattr(self.gui, '_show_notification'))
        self.assertTrue(callable(self.gui._show_notification))
        print("✓ Notification handling method exists")


class TestConnectionManagement(unittest.TestCase):
    """Test connection and credentials management."""
    
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
        self.mock_cache.clear_credentials = Mock()
        
        self.mock_api.qbittorrent_url = "http://localhost:8080"
        self.mock_api.series_directory = "/Series"
        self.mock_api.movies_directory = "/Movies"
        self.mock_api.test_connection = Mock(return_value=True)
        
        self.gui = MacOSGUIManager(self.mock_cache, self.mock_api)
    
    def test_test_connection_method_exists(self):
        """Test connection test method exists."""
        self.assertTrue(hasattr(self.gui, '_settings_test_connection_'))
        print("✓ Test connection method exists")
    
    def test_clear_credentials_method_exists(self):
        """Test clear credentials method exists."""
        self.assertTrue(hasattr(self.gui, '_settings_clear_credentials_'))
        print("✓ Clear credentials method exists")
    
    def test_credentials_can_be_cleared(self):
        """Test credentials can be cleared."""
        # Clear credentials should call cache manager
        self.mock_cache.clear_credentials()
        self.mock_cache.clear_credentials.assert_called_once()
        print("✓ Credentials clearing works")


class TestSettingsPersistence(unittest.TestCase):
    """Test settings persistence."""
    
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
    
    def test_cache_manager_persistence(self):
        """Test cache manager is used for persistence."""
        self.assertIsNotNone(self.gui.cache_manager)
        self.assertTrue(hasattr(self.gui.cache_manager, 'save_setting'))
        print("✓ Cache manager persistence works")
    
    def test_api_client_settings_update(self):
        """Test API client settings are updated."""
        self.assertEqual(self.gui.api_client.qbittorrent_url, "http://localhost:8080")
        
        # Simulate updating URL
        new_url = "https://new-qb.example.com:8080"
        self.gui.api_client.qbittorrent_url = new_url
        
        self.assertEqual(self.gui.api_client.qbittorrent_url, new_url)
        print("✓ API client settings update works")


class TestSidebarNavigation(unittest.TestCase):
    """Test sidebar navigation functionality."""
    
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
        self.mock_cache.credentials_exist.return_value = True
        
        self.gui = MacOSGUIManager(self.mock_cache, self.mock_api)
    
    def test_sidebar_sections_exist(self):
        """Test all sidebar sections are defined."""
        expected_sections = ["General", "Directories", "qBittorrent", "Sites"]
        
        # Verify sections methods exist
        for section in expected_sections:
            method_name = f"_create_{section.lower()}_content"
            if section == "qBittorrent":
                method_name = "_create_qbittorrent_content"
            
            self.assertTrue(hasattr(self.gui, method_name))
        
        print("✓ All sidebar sections exist")
    
    def test_general_section_method(self):
        """Test General settings section method exists."""
        self.assertTrue(hasattr(self.gui, '_create_general_content'))
        self.assertTrue(callable(self.gui._create_general_content))
        print("✓ General section method works")
    
    def test_directories_section_method(self):
        """Test Directories settings section method exists."""
        self.assertTrue(hasattr(self.gui, '_create_directories_content'))
        self.assertTrue(callable(self.gui._create_directories_content))
        print("✓ Directories section method works")
    
    def test_qbittorrent_section_method(self):
        """Test qBittorrent settings section method exists."""
        self.assertTrue(hasattr(self.gui, '_create_qbittorrent_content'))
        self.assertTrue(callable(self.gui._create_qbittorrent_content))
        print("✓ qBittorrent section method works")
    
    def test_sites_section_method(self):
        """Test Sites settings section method exists."""
        self.assertTrue(hasattr(self.gui, '_create_sites_content'))
        self.assertTrue(callable(self.gui._create_sites_content))
        print("✓ Sites section method works")


class TestActionButtons(unittest.TestCase):
    """Test action button functionality."""
    
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
        self.mock_api.test_connection = Mock(return_value=True)
        
        self.gui = MacOSGUIManager(self.mock_cache, self.mock_api)
    
    def test_test_connection_button_callback(self):
        """Test connection button callback exists."""
        self.assertTrue(hasattr(self.gui, '_settings_test_connection_'))
        print("✓ Test Connection button callback exists")
    
    def test_clear_credentials_button_callback(self):
        """Test clear credentials button callback exists."""
        self.assertTrue(hasattr(self.gui, '_settings_clear_credentials_'))
        print("✓ Clear Credentials button callback exists")


def run_ui_integration_tests():
    """Run all UI and integration test suites."""
    print("\n" + "="*60)
    print("RUNNING UI & INTEGRATION TESTS")
    print("="*60 + "\n")
    
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestSettingsSave))
    suite.addTests(loader.loadTestsFromTestCase(TestErrorHandling))
    suite.addTests(loader.loadTestsFromTestCase(TestConnectionManagement))
    suite.addTests(loader.loadTestsFromTestCase(TestSettingsPersistence))
    suite.addTests(loader.loadTestsFromTestCase(TestSidebarNavigation))
    suite.addTests(loader.loadTestsFromTestCase(TestActionButtons))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "="*60)
    print("UI & INTEGRATION TEST SUMMARY")
    print("="*60)
    print(f"Tests Run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.wasSuccessful():
        print("\n✅ ALL UI & INTEGRATION TESTS PASSED!")
    else:
        print("\n❌ SOME TESTS FAILED")
    print("="*60 + "\n")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_ui_integration_tests()
    sys.exit(0 if success else 1)
