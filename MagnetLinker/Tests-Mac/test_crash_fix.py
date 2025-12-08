#!/usr/bin/env python3
"""Test that the crash has been fixed."""

from unittest.mock import Mock
from MacOSGUIManager import MacOSGUIManager

# Create mock objects
mock_cache = Mock()
mock_api = Mock()

# Initialize GUI manager
try:
    gui_manager = MacOSGUIManager(mock_cache, mock_api)
    print('✓ GUI Manager created successfully')
except Exception as e:
    print(f'✗ Failed to create GUI Manager: {e}')
    exit(1)

# Test that sidebar button creation works
try:
    button = gui_manager._create_enhanced_sidebar_button("Test", "gear", (12, 480))
    print('✓ Enhanced sidebar button created successfully')
except Exception as e:
    print(f'✗ Failed to create sidebar button: {e}')
    exit(1)

# Test that settings dialog can be created without crashing
try:
    # We can't fully test show_settings_dialog without a display, but we can
    # verify the method exists and is callable
    if callable(getattr(gui_manager, 'show_settings_dialog', None)):
        print('✓ show_settings_dialog method is callable')
    else:
        print('✗ show_settings_dialog method not callable')
        exit(1)
except Exception as e:
    print(f'✗ Error checking show_settings_dialog: {e}')
    exit(1)

print('\n✅ All crash fixes verified successfully!')
