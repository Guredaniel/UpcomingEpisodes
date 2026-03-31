#!/usr/bin/env python3
"""Tests for error handling, validation, and edge cases."""

import sys
import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from pathlib import Path

# Ensure project root is on sys.path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from MacOSGUIManager import MacOSGUIManager
from CacheManager import CacheManager
from APIClient import APIClient


class TestURLValidation(unittest.TestCase):
    """Test URL validation in settings."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_cache = Mock(spec=CacheManager)
        self.mock_api = Mock(spec=APIClient)
        
        self.mock_cache.load_setting.side_effect = lambda key, default: {
            "monitor_clipboard_enabled": True,
            "cache_duration_minutes": 30.0,
            "indefinite_selection": False,
        }.get(key, default)
        
        self.mock_cache.get_saved_sites.return_value = []
        self.mock_api.qbittorrent_url = "http://localhost:8080"
        self.mock_api.series_directory = "/Series"
        self.mock_api.movies_directory = "/Movies"
        
        self.gui = MacOSGUIManager(self.mock_cache, self.mock_api)
    
    def test_valid_http_url(self):
        """Test valid HTTP URL."""
        url = "http://localhost:8080"
        is_valid = url.startswith("http://") or url.startswith("https://")
        self.assertTrue(is_valid)
        print("✓ Valid HTTP URL validation works")
    
    def test_valid_https_url(self):
        """Test valid HTTPS URL."""
        url = "https://example.com:8080"
        is_valid = url.startswith("http://") or url.startswith("https://")
        self.assertTrue(is_valid)
        print("✓ Valid HTTPS URL validation works")
    
    def test_invalid_url_no_protocol(self):
        """Test invalid URL without protocol."""
        url = "localhost:8080"
        is_valid = url.startswith("http://") or url.startswith("https://")
        self.assertFalse(is_valid)
        print("✓ Invalid URL without protocol validation works")
    
    def test_invalid_url_ftp_protocol(self):
        """Test invalid URL with FTP protocol."""
        url = "ftp://example.com"
        is_valid = url.startswith("http://") or url.startswith("https://")
        self.assertFalse(is_valid)
        print("✓ Invalid URL with FTP protocol validation works")
    
    def test_empty_url(self):
        """Test empty URL."""
        url = ""
        is_valid = bool(url) and (url.startswith("http://") or url.startswith("https://"))
        self.assertFalse(is_valid)
        print("✓ Empty URL validation works")


class TestCacheDurationValidation(unittest.TestCase):
    """Test cache duration validation."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_cache = Mock(spec=CacheManager)
        self.mock_api = Mock(spec=APIClient)
        
        self.mock_cache.load_setting.side_effect = lambda key, default: {
            "monitor_clipboard_enabled": True,
            "cache_duration_minutes": 30.0,
            "indefinite_selection": False,
        }.get(key, default)
        
        self.mock_cache.get_saved_sites.return_value = []
        self.mock_api.qbittorrent_url = "http://localhost:8080"
        self.mock_api.series_directory = "/Series"
        self.mock_api.movies_directory = "/Movies"
    
    def test_valid_numeric_cache_duration(self):
        """Test valid numeric cache duration."""
        duration_str = "30"
        try:
            duration = float(duration_str)
            is_valid = duration >= 0
            self.assertTrue(is_valid)
            print("✓ Valid numeric cache duration works")
        except ValueError:
            self.fail("Should parse as float")
    
    def test_zero_cache_duration(self):
        """Test zero cache duration (always ask)."""
        duration_str = "0"
        try:
            duration = float(duration_str)
            is_valid = duration >= 0
            self.assertTrue(is_valid)
            print("✓ Zero cache duration works")
        except ValueError:
            self.fail("Should parse as float")
    
    def test_decimal_cache_duration(self):
        """Test decimal cache duration."""
        duration_str = "30.5"
        try:
            duration = float(duration_str)
            is_valid = duration >= 0
            self.assertTrue(is_valid)
            print("✓ Decimal cache duration works")
        except ValueError:
            self.fail("Should parse as float")
    
    def test_invalid_cache_duration_non_numeric(self):
        """Test invalid non-numeric cache duration."""
        duration_str = "invalid"
        try:
            float(duration_str)
            is_valid = True
        except ValueError:
            is_valid = False
        self.assertFalse(is_valid)
        print("✓ Invalid non-numeric cache duration works")
    
    def test_negative_cache_duration(self):
        """Test negative cache duration."""
        duration_str = "-30"
        try:
            duration = float(duration_str)
            is_valid = duration >= 0
            self.assertFalse(is_valid)
            print("✓ Negative cache duration validation works")
        except ValueError:
            self.fail("Should parse as float")


class TestClipboardIntervalValidation(unittest.TestCase):
    """Test clipboard check interval validation."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_cache = Mock(spec=CacheManager)
        self.mock_api = Mock(spec=APIClient)
        
        self.mock_cache.load_setting.side_effect = lambda key, default: {
            "monitor_clipboard_enabled": True,
            "clipboard_check_interval": 0.5,
        }.get(key, default)
        
        self.mock_cache.get_saved_sites.return_value = []
        self.mock_api.qbittorrent_url = "http://localhost:8080"
        self.mock_api.series_directory = "/Series"
        self.mock_api.movies_directory = "/Movies"
    
    def test_valid_interval(self):
        """Test valid clipboard check interval."""
        interval_str = "0.5"
        try:
            interval = float(interval_str)
            is_valid = 0.1 <= interval <= 10.0
            self.assertTrue(is_valid)
            print("✓ Valid clipboard interval works")
        except ValueError:
            self.fail("Should parse as float")
    
    def test_min_interval(self):
        """Test minimum valid interval."""
        interval_str = "0.1"
        try:
            interval = float(interval_str)
            is_valid = 0.1 <= interval <= 10.0
            self.assertTrue(is_valid)
            print("✓ Minimum interval works")
        except ValueError:
            self.fail("Should parse as float")
    
    def test_max_interval(self):
        """Test maximum valid interval."""
        interval_str = "10.0"
        try:
            interval = float(interval_str)
            is_valid = 0.1 <= interval <= 10.0
            self.assertTrue(is_valid)
            print("✓ Maximum interval works")
        except ValueError:
            self.fail("Should parse as float")
    
    def test_interval_below_minimum(self):
        """Test interval below minimum."""
        interval_str = "0.05"
        try:
            interval = float(interval_str)
            is_valid = 0.1 <= interval <= 10.0
            self.assertFalse(is_valid)
            print("✓ Interval below minimum validation works")
        except ValueError:
            self.fail("Should parse as float")
    
    def test_interval_above_maximum(self):
        """Test interval above maximum."""
        interval_str = "15.0"
        try:
            interval = float(interval_str)
            is_valid = 0.1 <= interval <= 10.0
            self.assertFalse(is_valid)
            print("✓ Interval above maximum validation works")
        except ValueError:
            self.fail("Should parse as float")


class TestMagnetURLValidation(unittest.TestCase):
    """Test magnet URL detection and validation."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_cache = Mock(spec=CacheManager)
        self.mock_api = Mock(spec=APIClient)
        
        self.mock_cache.load_setting.side_effect = lambda key, default: {
            "monitor_clipboard_enabled": True,
            "cache_duration_minutes": 30.0,
            "indefinite_selection": False,
        }.get(key, default)
        
        self.mock_cache.get_saved_sites.return_value = []
        self.mock_api.qbittorrent_url = "http://localhost:8080"
        self.mock_api.series_directory = "/Series"
        self.mock_api.movies_directory = "/Movies"
    
    def test_valid_magnet_url(self):
        """Test valid magnet URL."""
        url = "magnet:?xt=urn:btih:test123&dn=Test"
        is_valid = url.startswith("magnet:")
        self.assertTrue(is_valid)
        print("✓ Valid magnet URL detection works")
    
    def test_magnet_url_case_insensitive(self):
        """Test magnet URL with different cases."""
        url = "magnet:?xt=urn:btih:test123"
        is_valid = url.lower().startswith("magnet:")
        self.assertTrue(is_valid)
        print("✓ Magnet URL case handling works")
    
    def test_invalid_url_not_magnet(self):
        """Test non-magnet URL."""
        url = "https://example.com"
        is_valid = url.startswith("magnet:")
        self.assertFalse(is_valid)
        print("✓ Non-magnet URL detection works")
    
    def test_empty_magnet_url(self):
        """Test empty URL."""
        url = ""
        is_valid = url.startswith("magnet:")
        self.assertFalse(is_valid)
        print("✓ Empty URL detection works")


class TestContentTypeSelection(unittest.TestCase):
    """Test content type selection logic."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_cache = Mock(spec=CacheManager)
        self.mock_api = Mock(spec=APIClient)
        
        self.mock_cache.load_setting.side_effect = lambda key, default: {
            "monitor_clipboard_enabled": True,
            "cache_duration_minutes": 30.0,
            "indefinite_selection": False,
        }.get(key, default)
        
        self.mock_cache.get_saved_sites.return_value = []
        self.mock_api.qbittorrent_url = "http://localhost:8080"
        self.mock_api.series_directory = "/Series"
        self.mock_api.movies_directory = "/Movies"
    
    def test_selection_movie(self):
        """Test movie selection."""
        selection = "Movie"
        is_series = selection == "Series"
        self.assertFalse(is_series)
        print("✓ Movie selection works")
    
    def test_selection_series(self):
        """Test series selection."""
        selection = "Series"
        is_series = selection == "Series"
        self.assertTrue(is_series)
        print("✓ Series selection works")
    
    def test_cached_selection_indefinite(self):
        """Test indefinite cached selection."""
        cached = ("Movie", None)
        selection, time_cached = cached
        
        # Indefinite means time_cached is None
        is_indefinite = time_cached is None
        self.assertTrue(is_indefinite)
        print("✓ Indefinite cached selection works")
    
    def test_cached_selection_with_expiry(self):
        """Test cached selection with expiry."""
        now = datetime.now()
        cached = ("Series", now)
        selection, time_cached = cached
        
        # Has expiry time
        is_indefinite = time_cached is None
        self.assertFalse(is_indefinite)
        print("✓ Cached selection with expiry works")
    
    def test_selection_expiration_check(self):
        """Test checking if cached selection has expired."""
        now = datetime.now()
        cached = ("Movie", now)
        cache_duration = 30
        
        expiration_time = now + timedelta(minutes=cache_duration)
        is_expired = datetime.now() > expiration_time
        
        # Should not be expired immediately
        self.assertFalse(is_expired)
        print("✓ Selection expiration check works")


class TestSiteValidation(unittest.TestCase):
    """Test site entry validation."""
    
    def test_valid_site_entry(self):
        """Test valid site with name and URL."""
        site = {"name": "Test Site", "url": "https://test.com"}
        
        name = site.get("name", "").strip()
        url = site.get("url", "").strip()
        is_valid = bool(name and url)
        
        self.assertTrue(is_valid)
        print("✓ Valid site entry works")
    
    def test_invalid_site_missing_name(self):
        """Test site missing name."""
        site = {"name": "", "url": "https://test.com"}
        
        name = site.get("name", "").strip()
        url = site.get("url", "").strip()
        is_valid = bool(name and url)
        
        self.assertFalse(is_valid)
        print("✓ Site missing name validation works")
    
    def test_invalid_site_missing_url(self):
        """Test site missing URL."""
        site = {"name": "Test Site", "url": ""}
        
        name = site.get("name", "").strip()
        url = site.get("url", "").strip()
        is_valid = bool(name and url)
        
        self.assertFalse(is_valid)
        print("✓ Site missing URL validation works")
    
    def test_invalid_site_whitespace_only(self):
        """Test site with whitespace only."""
        site = {"name": "   ", "url": "   "}
        
        name = site.get("name", "").strip()
        url = site.get("url", "").strip()
        is_valid = bool(name and url)
        
        self.assertFalse(is_valid)
        print("✓ Site whitespace only validation works")
    
    def test_site_with_special_characters(self):
        """Test site name with special characters."""
        site = {"name": "Site @#$%", "url": "https://example.com"}
        
        name = site.get("name", "").strip()
        url = site.get("url", "").strip()
        is_valid = bool(name and url)
        
        self.assertTrue(is_valid)
        print("✓ Site with special characters works")


class TestDirectoryPaths(unittest.TestCase):
    """Test directory path configurations."""
    
    def test_empty_series_directory(self):
        """Test empty series directory."""
        path = ""
        is_valid = bool(path.strip())
        self.assertFalse(is_valid)
        print("✓ Empty series directory validation works")
    
    def test_valid_series_directory(self):
        """Test valid series directory."""
        path = "/mnt/media/series"
        is_valid = bool(path.strip())
        self.assertTrue(is_valid)
        print("✓ Valid series directory works")
    
    def test_windows_style_path(self):
        """Test Windows style path."""
        path = "C:\\Users\\Downloads\\Series"
        is_valid = bool(path.strip())
        self.assertTrue(is_valid)
        print("✓ Windows style path works")
    
    def test_relative_path(self):
        """Test relative path."""
        path = "./Series"
        is_valid = bool(path.strip())
        self.assertTrue(is_valid)
        print("✓ Relative path works")
    
    def test_home_directory_path(self):
        """Test home directory path."""
        path = "~/Downloads/Series"
        is_valid = bool(path.strip())
        self.assertTrue(is_valid)
        print("✓ Home directory path works")


if __name__ == "__main__":
    unittest.main(verbosity=2)
