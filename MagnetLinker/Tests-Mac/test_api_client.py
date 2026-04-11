#!/usr/bin/env python3
"""Comprehensive tests for APIClient functionality."""

import sys
import unittest
from unittest.mock import Mock, patch, MagicMock, mock_open
from pathlib import Path

# Ensure project root is on sys.path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from APIClient import APIClient
from CacheManager import CacheManager


class TestAPIClientInitialization(unittest.TestCase):
    """Test APIClient initialization."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_cache = Mock(spec=CacheManager)
        self.mock_cache.load_setting.side_effect = lambda key, default: {
            "qbittorrent_url": "http://localhost:8080",
            "series_directory": "/Series",
            "movies_directory": "/Movies",
        }.get(key, default)
    
    def test_initialization(self):
        """Test APIClient initializes correctly."""
        client = APIClient(self.mock_cache)
        
        self.assertIsNotNone(client)
        self.assertEqual(client.cache_manager, self.mock_cache)
        print("✓ APIClient initialization works")
    
    def test_loads_qbittorrent_url(self):
        """Test APIClient loads qBittorrent URL from cache."""
        client = APIClient(self.mock_cache)
        
        self.assertEqual(client.qbittorrent_url, "http://localhost:8080")
        print("✓ qBittorrent URL loading works")
    
    def test_loads_directories(self):
        """Test APIClient loads directories from cache."""
        client = APIClient(self.mock_cache)
        
        self.assertEqual(client.series_directory, "/Series")
        self.assertEqual(client.movies_directory, "/Movies")
        print("✓ Directory loading works")
    
    def test_default_values(self):
        """Test APIClient uses defaults when settings not found."""
        self.mock_cache.load_setting.return_value = None
        client = APIClient(self.mock_cache)
        
        # Should have loaded defaults
        self.assertIsNotNone(client.qbittorrent_url)
        self.assertIsNotNone(client.series_directory)
        self.assertIsNotNone(client.movies_directory)
        print("✓ Default values loading works")


class TestAPIClientMagnetLink(unittest.TestCase):
    """Test magnet link handling."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_cache = Mock(spec=CacheManager)
        self.mock_cache.load_setting.side_effect = lambda key, default: {
            "qbittorrent_url": "http://localhost:8080",
            "series_directory": "/Series",
            "movies_directory": "/Movies",
        }.get(key, default)
        self.mock_cache.load_credentials.return_value = ("testuser", "testpass")
        
        self.client = APIClient(self.mock_cache)
    
    @patch('APIClient.requests.Session')
    def test_open_magnet_movie(self, mock_session_class):
        """Test sending movie magnet link."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        
        # Mock login response
        mock_login_resp = Mock()
        mock_login_resp.status_code = 200
        
        # Mock add torrent response
        mock_add_resp = Mock()
        mock_add_resp.status_code = 200
        
        mock_session.post.side_effect = [mock_login_resp, mock_add_resp]
        
        magnet_url = "magnet:?xt=urn:btih:test123"
        self.client.open_qbittorrent_with_magnet(magnet_url, is_series=False)
        
        # Verify calls
        self.assertEqual(mock_session.post.call_count, 2)
        print("✓ Open magnet movie works")
    
    @patch('APIClient.requests.Session')
    def test_open_magnet_series(self, mock_session_class):
        """Test sending series magnet link."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        
        # Mock responses
        mock_login_resp = Mock()
        mock_login_resp.status_code = 200
        
        mock_add_resp = Mock()
        mock_add_resp.status_code = 200
        
        mock_session.post.side_effect = [mock_login_resp, mock_add_resp]
        
        magnet_url = "magnet:?xt=urn:btih:test123"
        self.client.open_qbittorrent_with_magnet(magnet_url, is_series=True)
        
        # Verify calls
        self.assertEqual(mock_session.post.call_count, 2)
        print("✓ Open magnet series works")
    
    @patch('APIClient.requests.Session')
    def test_magnet_failed_login(self, mock_session_class):
        """Test magnet link handling with failed login."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        
        # Mock failed login response
        mock_login_resp = Mock()
        mock_login_resp.status_code = 401
        mock_login_resp.text = "Unauthorized"
        
        mock_session.post.return_value = mock_login_resp
        
        magnet_url = "magnet:?xt=urn:btih:test123"
        
        with self.assertRaises(Exception) as context:
            self.client.open_qbittorrent_with_magnet(magnet_url, is_series=False)
        
        self.assertIn("login", str(context.exception).lower())
        print("✓ Magnet failed login handling works")
    
    @patch('APIClient.requests.Session')
    def test_magnet_no_credentials(self, mock_session_class):
        """Test magnet link with missing credentials."""
        self.mock_cache.load_credentials.return_value = (None, None)
        self.client = APIClient(self.mock_cache)
        
        magnet_url = "magnet:?xt=urn:btih:test123"
        
        with self.assertRaises(Exception) as context:
            self.client.open_qbittorrent_with_magnet(magnet_url, is_series=False)
        
        self.assertIn("credentials", str(context.exception).lower())
        print("✓ Magnet no credentials handling works")

    @patch('APIClient.requests.Session')
    def test_open_magnet_with_url_missing_trailing_slash(self, mock_session_class):
        """Test qBittorrent URL missing trailing slash is normalized."""
        self.mock_cache.load_setting.side_effect = lambda key, default: {
            "qbittorrent_url": "http://localhost:8080",
            "series_directory": "/Series",
            "movies_directory": "/Movies",
        }.get(key, default)
        self.mock_cache.load_credentials.return_value = ("testuser", "testpass")
        self.client = APIClient(self.mock_cache)

        mock_session = Mock()
        mock_session_class.return_value = mock_session
        mock_login_resp = Mock()
        mock_login_resp.status_code = 200
        mock_add_resp = Mock()
        mock_add_resp.status_code = 200
        mock_session.post.side_effect = [mock_login_resp, mock_add_resp]

        magnet_url = "magnet:?xt=urn:btih:test123"
        self.client.open_qbittorrent_with_magnet(magnet_url, is_series=False)

        self.assertEqual(mock_session.post.call_count, 2)
        first_call_url = mock_session.post.call_args_list[0].args[0]
        self.assertEqual(first_call_url, "http://localhost:8080/api/v2/auth/login")
        second_call_url = mock_session.post.call_args_list[1].args[0]
        self.assertEqual(second_call_url, "http://localhost:8080/api/v2/torrents/add")
        print("✓ Magnet URL missing trailing slash normalization works")


class TestAPIClientTorrentFile(unittest.TestCase):
    """Test torrent file handling."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_cache = Mock(spec=CacheManager)
        self.mock_cache.load_setting.side_effect = lambda key, default: {
            "qbittorrent_url": "http://localhost:8080",
            "series_directory": "/Series",
            "movies_directory": "/Movies",
        }.get(key, default)
        self.mock_cache.load_credentials.return_value = ("testuser", "testpass")
        
        self.client = APIClient(self.mock_cache)
    
    @patch('builtins.open', new_callable=mock_open, read_data=b"torrent data")
    @patch('APIClient.requests.Session')
    def test_open_torrent_movie(self, mock_session_class, mock_file):
        """Test sending movie torrent file."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        
        # Mock responses
        mock_login_resp = Mock()
        mock_login_resp.status_code = 200
        
        mock_add_resp = Mock()
        mock_add_resp.status_code = 200
        
        mock_session.post.side_effect = [mock_login_resp, mock_add_resp]
        
        self.client.open_qbittorrent_with_torrent_file("/path/to/file.torrent", is_series=False)
        
        # Verify calls
        self.assertEqual(mock_session.post.call_count, 2)
        print("✓ Open torrent movie works")
    
    @patch('builtins.open', new_callable=mock_open, read_data=b"torrent data")
    @patch('APIClient.requests.Session')
    def test_open_torrent_series(self, mock_session_class, mock_file):
        """Test sending series torrent file."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        
        # Mock responses
        mock_login_resp = Mock()
        mock_login_resp.status_code = 200
        
        mock_add_resp = Mock()
        mock_add_resp.status_code = 200
        
        mock_session.post.side_effect = [mock_login_resp, mock_add_resp]
        
        self.client.open_qbittorrent_with_torrent_file("/path/to/file.torrent", is_series=True)
        
        # Verify calls
        self.assertEqual(mock_session.post.call_count, 2)
        print("✓ Open torrent series works")
    
    @patch('APIClient.requests.Session')
    def test_torrent_failed_login(self, mock_session_class):
        """Test torrent file handling with failed login."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        
        # Mock failed login response
        mock_login_resp = Mock()
        mock_login_resp.status_code = 401
        mock_login_resp.text = "Unauthorized"
        
        mock_session.post.return_value = mock_login_resp
        
        with self.assertRaises(Exception) as context:
            self.client.open_qbittorrent_with_torrent_file("/path/to/file.torrent", is_series=False)
        
        self.assertIn("login", str(context.exception).lower())
        print("✓ Torrent failed login handling works")
    
    @patch('APIClient.requests.Session')
    def test_torrent_no_credentials(self, mock_session_class):
        """Test torrent file with missing credentials."""
        self.mock_cache.load_credentials.return_value = (None, None)
        self.client = APIClient(self.mock_cache)
        
        with self.assertRaises(Exception) as context:
            self.client.open_qbittorrent_with_torrent_file("/path/to/file.torrent", is_series=False)
        
        self.assertIn("credentials", str(context.exception).lower())
        print("✓ Torrent no credentials handling works")


class TestAPIClientWeb(unittest.TestCase):
    """Test web interface opening."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_cache = Mock(spec=CacheManager)
        self.mock_cache.load_setting.side_effect = lambda key, default: {
            "qbittorrent_url": "http://localhost:8080",
            "series_directory": "/Series",
            "movies_directory": "/Movies",
        }.get(key, default)
        
        self.client = APIClient(self.mock_cache)
    
    @patch('APIClient.webbrowser.open')
    def test_open_qbittorrent_web(self, mock_browser):
        """Test opening qBittorrent web interface."""
        self.client.open_qbittorrent_web()
        
        mock_browser.assert_called_once_with("http://localhost:8080")
        print("✓ Open qBittorrent web works")
    
    @patch('APIClient.webbrowser.open')
    def test_open_web_with_custom_url(self, mock_browser):
        """Test opening web with custom URL."""
        self.client.qbittorrent_url = "https://custom.url:9999"
        self.client.open_qbittorrent_web()
        
        mock_browser.assert_called_once_with("https://custom.url:9999")
        print("✓ Open web with custom URL works")
    
    @patch('APIClient.webbrowser.open')
    def test_open_web_failure(self, mock_browser):
        """Test web opening failure handling."""
        mock_browser.side_effect = Exception("Browser not available")
        
        with self.assertRaises(Exception):
            self.client.open_qbittorrent_web()
        
        print("✓ Web opening failure handling works")


class TestAPIClientNetworkErrors(unittest.TestCase):
    """Test network error handling."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_cache = Mock(spec=CacheManager)
        self.mock_cache.load_setting.side_effect = lambda key, default: {
            "qbittorrent_url": "http://localhost:8080",
            "series_directory": "/Series",
            "movies_directory": "/Movies",
        }.get(key, default)
        self.mock_cache.load_credentials.return_value = ("testuser", "testpass")
        
        self.client = APIClient(self.mock_cache)
    
    @patch('APIClient.requests.Session')
    def test_connection_timeout(self, mock_session_class):
        """Test handling connection timeout."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        
        # Mock timeout
        mock_session.post.side_effect = Exception("Connection timeout")
        
        magnet_url = "magnet:?xt=urn:btih:test123"
        
        with self.assertRaises(Exception):
            self.client.open_qbittorrent_with_magnet(magnet_url, is_series=False)
        
        print("✓ Connection timeout handling works")
    
    @patch('APIClient.requests.Session')
    def test_http_error_response(self, mock_session_class):
        """Test handling HTTP error responses."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        
        # Mock login success
        mock_login_resp = Mock()
        mock_login_resp.status_code = 200
        
        # Mock error response from add torrent
        mock_error_resp = Mock()
        mock_error_resp.status_code = 500
        mock_error_resp.text = "Internal Server Error"
        
        mock_session.post.side_effect = [mock_login_resp, mock_error_resp]
        
        magnet_url = "magnet:?xt=urn:btih:test123"
        
        with self.assertRaises(Exception):
            self.client.open_qbittorrent_with_magnet(magnet_url, is_series=False)
        
        print("✓ HTTP error response handling works")


class TestAPIClientPathHandling(unittest.TestCase):
    """Test path handling and directory management."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_cache = Mock(spec=CacheManager)
        self.mock_cache.load_setting.side_effect = lambda key, default: {
            "qbittorrent_url": "http://localhost:8080",
            "series_directory": "/path/to/series",
            "movies_directory": "/path/to/movies",
        }.get(key, default)
        self.mock_cache.load_credentials.return_value = ("testuser", "testpass")
        
        self.client = APIClient(self.mock_cache)
    
    def test_series_directory_path(self):
        """Test series directory path is stored correctly."""
        self.assertEqual(self.client.series_directory, "/path/to/series")
        print("✓ Series directory path works")
    
    def test_movies_directory_path(self):
        """Test movies directory path is stored correctly."""
        self.assertEqual(self.client.movies_directory, "/path/to/movies")
        print("✓ Movies directory path works")
    
    @patch('APIClient.requests.Session')
    def test_magnet_with_custom_paths(self, mock_session_class):
        """Test magnet sent with correct directory based on type."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        
        # Mock responses
        mock_login_resp = Mock()
        mock_login_resp.status_code = 200
        
        mock_add_resp = Mock()
        mock_add_resp.status_code = 200
        
        mock_session.post.side_effect = [mock_login_resp, mock_add_resp]
        
        magnet_url = "magnet:?xt=urn:btih:test123"
        
        # Test series
        self.client.open_qbittorrent_with_magnet(magnet_url, is_series=True)
        
        # Check that series path was used
        add_call = mock_session.post.call_args_list[-1]
        self.assertIn("/path/to/series", str(add_call))
        print("✓ Magnet with custom paths works")


if __name__ == "__main__":
    unittest.main(verbosity=2)
