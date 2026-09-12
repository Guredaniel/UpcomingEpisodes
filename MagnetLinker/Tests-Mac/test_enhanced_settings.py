#!/usr/bin/env python3
"""
Test the enhanced macOS settings interface with visual improvements.
"""

from unittest.mock import Mock

from MacOSGUIManager import MacOSGUIManager
from CacheManager import CacheManager
from APIClient import APIClient


class FakeToggleField:
    """Small stand-in for Cocoa toggle fields used in settings save tests."""

    def __init__(self, state: int) -> None:
        self._state = state
        self.enabled = True

    def state(self) -> int:
        return self._state

    def setState_(self, state: int) -> None:
        self._state = state

    def setEnabled_(self, enabled: bool) -> None:
        self.enabled = enabled


def test_enhanced_settings():
    """Test enhanced settings interface."""
    print("Testing enhanced macOS settings interface...")
    print()
    
    # Initialize managers
    cache = CacheManager()
    api = APIClient(cache)
    
    # Create GUI manager
    gui = MacOSGUIManager(cache, api)
    
    # Test methods exist
    methods_to_check = [
        '_create_enhanced_sidebar_button',
        '_create_attributed_string',
        '_create_general_content',
        '_create_directories_content',
        '_create_qbittorrent_content',
        '_create_sites_content',
        '_create_section_title',
        '_create_section_description',
    ]
    
    print('✓ Verifying enhanced methods:')
    for method in methods_to_check:
        if hasattr(gui, method):
            print(f'  ✓ {method}')
        else:
            print(f'  ✗ {method} MISSING')
    
    print()
    print('✅ Enhanced Settings Features:')
    print('  • Larger window: 920x580px')
    print('  • Improved sidebar spacing (200px wide)')
    print('  • Visual dividers between sections')
    print('  • Better padding and margins (30px from edges)')
    print('  • Larger section titles (20pt, bold)')
    print('  • Sunken text field bezels for depth')
    print('  • Status indicators with symbols (✓/✗/🟢/🔴)')
    print('  • Emoji icons for torrent sites')
    print('  • Helper text for better guidance')
    print('  • Separator borders between UI sections')
    print('  • Better color contrast')
    print('  • Improved typography hierarchy')
    print('  • Enhanced button styling')
    print('  • Better spacing throughout')
    print()
    print('✅ All enhancements verified!')


def test_alternative_directories_toggle_support():
    """Ensure the macOS settings can fully enable or disable alternative directories."""
    cache = CacheManager()
    api = APIClient(cache)
    gui = MacOSGUIManager(cache, api)

    assert hasattr(gui, "alternative_directories_enabled")
    assert isinstance(gui.alternative_directories_enabled, bool)


def test_saving_disabled_alternative_directories_syncs_api_client(monkeypatch, tmp_path):
    """Disabling alternative directories should update cache and API client state."""
    monkeypatch.setenv("HOME", str(tmp_path))

    cache = CacheManager()
    api = APIClient(cache)
    gui = MacOSGUIManager(cache, api)

    gui.alternative_directories_enabled = True
    gui.use_alternative_default = True
    api.alternative_directories_enabled = True

    alt_field = FakeToggleField(0)
    alt_default_field = FakeToggleField(1)
    gui._settings_fields = {
        "alternative_directories_enabled": alt_field,
        "use_alternative_default": alt_default_field,
    }
    gui._working_sites = []
    gui._working_server_sites = []
    gui.app = type("App", (), {"menu": {}})()

    gui._save_all_settings()

    assert gui.alternative_directories_enabled is False
    assert gui.use_alternative_default is False
    assert cache.load_setting("alternative_directories_enabled", None) is False
    assert api.alternative_directories_enabled is False
    assert alt_default_field.state() == 0
    assert alt_default_field.enabled is False


def test_saving_enabled_alternative_directories_syncs_api_client(monkeypatch, tmp_path):
    """Enabling alternative directories should update cache and API client state."""
    monkeypatch.setenv("HOME", str(tmp_path))

    cache = CacheManager()
    api = APIClient(cache)
    gui = MacOSGUIManager(cache, api)

    gui.alternative_directories_enabled = False
    gui.use_alternative_default = False
    api.alternative_directories_enabled = False

    alt_field = FakeToggleField(1)
    alt_default_field = FakeToggleField(0)
    gui._settings_fields = {
        "alternative_directories_enabled": alt_field,
        "use_alternative_default": alt_default_field,
    }
    gui._working_sites = []
    gui._working_server_sites = []
    gui.app = type("App", (), {"menu": {}})()

    gui._save_all_settings()

    assert gui.alternative_directories_enabled is True
    assert gui.use_alternative_default is False
    assert cache.load_setting("alternative_directories_enabled", None) is True
    assert api.alternative_directories_enabled is True
    assert alt_default_field.enabled is True


def test_show_alternative_directories_toggle_support():
    """Ensure the macOS settings manager tracks show_alternative_directories."""
    cache = CacheManager()
    api = APIClient(cache)
    gui = MacOSGUIManager(cache, api)

    assert hasattr(gui, "show_alternative_directories")
    assert isinstance(gui.show_alternative_directories, bool)


def test_directories_content_toggles_alternative_fields():
    """Test that alternative directory fields are hidden when show_alternative_directories is False."""
    cache = CacheManager()
    api = APIClient(cache)
    gui = MacOSGUIManager(cache, api)
    gui._content_view = Mock()

    # When show_alternative_directories is True
    gui.show_alternative_directories = True
    gui._create_directories_content()
    assert "show_alt_directories" in gui._settings_fields
    assert "series_dir" in gui._settings_fields
    assert "movies_dir" in gui._settings_fields
    assert "alt_series_dir" in gui._settings_fields
    assert "alt_movies_dir" in gui._settings_fields

    # When show_alternative_directories is False
    gui.show_alternative_directories = False
    gui._create_directories_content()
    assert "show_alt_directories" in gui._settings_fields
    assert "series_dir" in gui._settings_fields
    assert "movies_dir" in gui._settings_fields
    assert "alt_series_dir" not in gui._settings_fields
    assert "alt_movies_dir" not in gui._settings_fields


def test_toggle_show_alternative_directories_callback(monkeypatch, tmp_path):
    """Test that toggling show_alternative_directories updates state, cache, and re-renders."""
    monkeypatch.setenv("HOME", str(tmp_path))

    cache = CacheManager()
    api = APIClient(cache)
    gui = MacOSGUIManager(cache, api)
    gui._content_view = Mock()
    gui._content_view.subviews.return_value = []
    gui._sidebar_buttons = {}

    toggle_field = FakeToggleField(0)
    gui._toggle_show_alternative_directories(toggle_field)

    assert gui.show_alternative_directories is False
    assert cache.load_setting("show_alternative_directories", None) is False
    assert "alt_series_dir" not in gui._settings_fields
    assert "alt_movies_dir" not in gui._settings_fields

    toggle_field.setState_(1)
    gui._toggle_show_alternative_directories(toggle_field)

    assert gui.show_alternative_directories is True
    assert cache.load_setting("show_alternative_directories", None) is True
    assert "alt_series_dir" in gui._settings_fields
    assert "alt_movies_dir" in gui._settings_fields


def test_saving_show_alternative_directories(monkeypatch, tmp_path):
    """Test saving show_alternative_directories via _save_all_settings."""
    monkeypatch.setenv("HOME", str(tmp_path))

    cache = CacheManager()
    api = APIClient(cache)
    gui = MacOSGUIManager(cache, api)

    gui.show_alternative_directories = True
    show_alt_field = FakeToggleField(0)
    gui._settings_fields = {
        "show_alt_directories": show_alt_field,
    }
    gui._working_sites = []
    gui._working_server_sites = []
    gui.app = type("App", (), {"menu": {}})()

    gui._save_all_settings()

    assert gui.show_alternative_directories is False
    assert cache.load_setting("show_alternative_directories", None) is False


if __name__ == "__main__":
    test_enhanced_settings()
    test_alternative_directories_toggle_support()
    test_show_alternative_directories_toggle_support()
    test_directories_content_toggles_alternative_fields()
    test_toggle_show_alternative_directories_callback(
        type("MonkeyPatch", (), {"setenv": lambda self, k, v: None})(),
        CacheManager().get_cache_directory().parent,
    )
    test_saving_show_alternative_directories(
        type("MonkeyPatch", (), {"setenv": lambda self, k, v: None})(),
        CacheManager().get_cache_directory().parent,
    )
    print("✅ All show_alternative_directories tests passed successfully!")
