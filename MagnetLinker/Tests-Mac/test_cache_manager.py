#!/usr/bin/env python3
"""Comprehensive tests for CacheManager functionality."""

import sys
import unittest
import os
import json
import tempfile
import shutil
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

# Ensure project root is on sys.path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from CacheManager import CacheManager


class TestCacheManagerKeyManagement(unittest.TestCase):
    """Test encryption key generation and management."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_cache_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        """Clean up test fixtures."""
        if os.path.exists(self.test_cache_dir):
            shutil.rmtree(self.test_cache_dir)
    
    def test_key_generation(self):
        """Test that encryption key is generated."""
        cache_mgr = CacheManager()
        
        # Verify key exists and is valid
        self.assertIsNotNone(cache_mgr.key)
        self.assertGreater(len(cache_mgr.key), 0)
        print("✓ Encryption key generation works")
    
    def test_key_persistence(self):
        """Test that encryption key persists between instances."""
        cache_mgr1 = CacheManager()
        key1 = cache_mgr1.key
        
        # Create new instance
        cache_mgr2 = CacheManager()
        key2 = cache_mgr2.key
        
        # Keys should be the same (loaded from cache)
        self.assertEqual(key1, key2)
        print("✓ Encryption key persistence works")
    
    def test_cache_directory_creation(self):
        """Test that cache directory is created."""
        cache_mgr = CacheManager()
        cache_dir = cache_mgr.get_cache_directory()
        
        # Verify directory exists
        self.assertTrue(os.path.exists(cache_dir))
        print("✓ Cache directory creation works")


class TestCacheManagerCredentials(unittest.TestCase):
    """Test credential encryption and storage."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.cache_mgr = CacheManager()
        # Clear any existing credentials
        self.cache_mgr.clear_credentials()
    
    def tearDown(self):
        """Clean up test fixtures."""
        self.cache_mgr.clear_credentials()
    
    def test_save_and_load_credentials(self):
        """Test saving and loading encrypted credentials."""
        username = "testuser"
        password = "testpass123"
        
        self.cache_mgr.save_credentials(username, password)
        loaded_user, loaded_pass = self.cache_mgr.load_credentials()
        
        self.assertEqual(loaded_user, username)
        self.assertEqual(loaded_pass, password)
        print("✓ Save and load credentials works")
    
    def test_credentials_encrypted(self):
        """Test that credentials are actually encrypted."""
        username = "testuser"
        password = "testpass123"
        
        self.cache_mgr.save_credentials(username, password)
        
        # Read raw file
        creds_path = os.path.join(
            self.cache_mgr.get_cache_directory(),
            "qbittorrent_credentials.json"
        )
        with open(creds_path, 'r') as f:
            raw_creds = json.load(f)
        
        # Encrypted values should not match plaintext
        self.assertNotEqual(raw_creds['username'], username)
        self.assertNotEqual(raw_creds['password'], password)
        print("✓ Credentials encryption works")
    
    def test_credentials_exist_true(self):
        """Test credentials_exist returns True when credentials exist."""
        self.cache_mgr.save_credentials("user", "pass")
        self.assertTrue(self.cache_mgr.credentials_exist())
        print("✓ credentials_exist returns True when credentials exist")
    
    def test_credentials_exist_false(self):
        """Test credentials_exist returns False when credentials don't exist."""
        self.cache_mgr.clear_credentials()
        self.assertFalse(self.cache_mgr.credentials_exist())
        print("✓ credentials_exist returns False when no credentials")
    
    def test_clear_credentials(self):
        """Test clearing credentials."""
        self.cache_mgr.save_credentials("user", "pass")
        self.assertTrue(self.cache_mgr.credentials_exist())
        
        self.cache_mgr.clear_credentials()
        
        self.assertFalse(self.cache_mgr.credentials_exist())
        print("✓ Clear credentials works")
    
    def test_load_nonexistent_credentials(self):
        """Test loading credentials when none exist."""
        self.cache_mgr.clear_credentials()
        user, password = self.cache_mgr.load_credentials()
        
        self.assertIsNone(user)
        self.assertIsNone(password)
        print("✓ Loading nonexistent credentials returns None")


class TestCacheManagerSettings(unittest.TestCase):
    """Test settings save and load functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.cache_mgr = CacheManager()
        # Clear settings
        settings_path = os.path.join(
            self.cache_mgr.get_cache_directory(),
            "settings.json"
        )
        if os.path.exists(settings_path):
            os.remove(settings_path)
    
    def tearDown(self):
        """Clean up test fixtures."""
        settings_path = os.path.join(
            self.cache_mgr.get_cache_directory(),
            "settings.json"
        )
        if os.path.exists(settings_path):
            os.remove(settings_path)
    
    def test_save_and_load_string_setting(self):
        """Test saving and loading string settings."""
        self.cache_mgr.save_setting("test_key", "test_value")
        loaded = self.cache_mgr.load_setting("test_key")
        
        self.assertEqual(loaded, "test_value")
        print("✓ Save and load string setting works")
    
    def test_save_and_load_numeric_setting(self):
        """Test saving and loading numeric settings."""
        self.cache_mgr.save_setting("numeric_key", 42)
        loaded = self.cache_mgr.load_setting("numeric_key")
        
        self.assertEqual(loaded, 42)
        print("✓ Save and load numeric setting works")
    
    def test_save_and_load_boolean_setting(self):
        """Test saving and loading boolean settings."""
        self.cache_mgr.save_setting("bool_key", True)
        loaded = self.cache_mgr.load_setting("bool_key")
        
        self.assertEqual(loaded, True)
        print("✓ Save and load boolean setting works")
    
    def test_save_and_load_dict_setting(self):
        """Test saving and loading dictionary settings."""
        test_dict = {"nested": "value", "count": 10}
        self.cache_mgr.save_setting("dict_key", test_dict)
        loaded = self.cache_mgr.load_setting("dict_key")
        
        self.assertEqual(loaded, test_dict)
        print("✓ Save and load dict setting works")
    
    def test_save_and_load_list_setting(self):
        """Test saving and loading list settings."""
        test_list = ["item1", "item2", "item3"]
        self.cache_mgr.save_setting("list_key", test_list)
        loaded = self.cache_mgr.load_setting("list_key")
        
        self.assertEqual(loaded, test_list)
        print("✓ Save and load list setting works")
    
    def test_load_nonexistent_setting_returns_default(self):
        """Test loading nonexistent setting returns default value."""
        default = "default_value"
        loaded = self.cache_mgr.load_setting("nonexistent", default)
        
        self.assertEqual(loaded, default)
        print("✓ Load nonexistent setting returns default")
    
    def test_multiple_settings(self):
        """Test saving and loading multiple settings."""
        self.cache_mgr.save_setting("key1", "value1")
        self.cache_mgr.save_setting("key2", "value2")
        self.cache_mgr.save_setting("key3", "value3")
        
        loaded1 = self.cache_mgr.load_setting("key1")
        loaded2 = self.cache_mgr.load_setting("key2")
        loaded3 = self.cache_mgr.load_setting("key3")
        
        self.assertEqual(loaded1, "value1")
        self.assertEqual(loaded2, "value2")
        self.assertEqual(loaded3, "value3")
        print("✓ Multiple settings persistence works")
    
    def test_overwrite_setting(self):
        """Test overwriting an existing setting."""
        self.cache_mgr.save_setting("key", "value1")
        self.cache_mgr.save_setting("key", "value2")
        
        loaded = self.cache_mgr.load_setting("key")
        self.assertEqual(loaded, "value2")
        print("✓ Overwrite setting works")


class TestCacheManagerSites(unittest.TestCase):
    """Test saved sites management."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.cache_mgr = CacheManager()
        # Clear settings
        settings_path = os.path.join(
            self.cache_mgr.get_cache_directory(),
            "settings.json"
        )
        if os.path.exists(settings_path):
            os.remove(settings_path)
    
    def tearDown(self):
        """Clean up test fixtures."""
        settings_path = os.path.join(
            self.cache_mgr.get_cache_directory(),
            "settings.json"
        )
        if os.path.exists(settings_path):
            os.remove(settings_path)
    
    def test_get_default_sites(self):
        """Test getting default sites."""
        sites = self.cache_mgr.get_saved_sites()
        
        self.assertIsInstance(sites, list)
        self.assertGreater(len(sites), 0)
        # Check structure
        for site in sites:
            self.assertIn("name", site)
            self.assertIn("url", site)
        print("✓ Get default sites works")
    
    def test_save_and_load_sites(self):
        """Test saving and loading custom sites."""
        custom_sites = [
            {"name": "Site 1", "url": "https://site1.com"},
            {"name": "Site 2", "url": "https://site2.com"}
        ]
        
        self.cache_mgr.save_sites(custom_sites)
        loaded = self.cache_mgr.get_saved_sites()
        
        self.assertEqual(loaded, custom_sites)
        print("✓ Save and load sites works")
    
    def test_save_empty_sites(self):
        """Test saving empty sites list."""
        self.cache_mgr.save_sites([])
        loaded = self.cache_mgr.get_saved_sites()
        
        self.assertEqual(loaded, [])
        print("✓ Save empty sites works")

    def test_save_and_load_server_sites(self):
        """Test saving and loading custom server shortcuts."""
        custom_servers = [
            {"name": "OpenMediaVault", "url": "http://192.168.1.152/"},
            {"name": "Sonarr", "url": "http://192.168.1.152:8989"},
        ]

        self.cache_mgr.save_server_sites(custom_servers)
        loaded = self.cache_mgr.get_saved_server_sites()

        self.assertEqual(loaded, custom_servers)
        print("✓ Save and load server sites works")


class TestCacheManagerEdgeCases(unittest.TestCase):
    """Test edge cases and error conditions."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.cache_mgr = CacheManager()
    
    def tearDown(self):
        """Clean up test fixtures."""
        settings_path = os.path.join(
            self.cache_mgr.get_cache_directory(),
            "settings.json"
        )
        if os.path.exists(settings_path):
            os.remove(settings_path)
        self.cache_mgr.clear_credentials()
    
    def test_special_characters_in_credentials(self):
        """Test credentials with special characters."""
        username = "user@domain.com"
        password = "p@ss!w0rd#$%special"
        
        self.cache_mgr.save_credentials(username, password)
        loaded_user, loaded_pass = self.cache_mgr.load_credentials()
        
        self.assertEqual(loaded_user, username)
        self.assertEqual(loaded_pass, password)
        print("✓ Special characters in credentials works")
    
    def test_unicode_in_credentials(self):
        """Test credentials with Unicode characters."""
        username = "用户"
        password = "密码🔐"
        
        self.cache_mgr.save_credentials(username, password)
        loaded_user, loaded_pass = self.cache_mgr.load_credentials()
        
        self.assertEqual(loaded_user, username)
        self.assertEqual(loaded_pass, password)
        print("✓ Unicode in credentials works")
    
    def test_empty_setting_values(self):
        """Test saving empty string settings."""
        self.cache_mgr.save_setting("empty", "")
        loaded = self.cache_mgr.load_setting("empty")
        
        self.assertEqual(loaded, "")
        print("✓ Empty setting values work")
    
    def test_very_long_setting_values(self):
        """Test saving very long setting values."""
        long_value = "x" * 10000
        self.cache_mgr.save_setting("long", long_value)
        loaded = self.cache_mgr.load_setting("long")
        
        self.assertEqual(loaded, long_value)
        print("✓ Very long setting values work")


if __name__ == "__main__":
    unittest.main(verbosity=2)
