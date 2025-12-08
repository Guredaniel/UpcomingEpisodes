#!/usr/bin/env python3
"""Test that the SettingsWindowDelegate stops the modal session when the window closes."""

from unittest.mock import Mock
import MacOSGUIManager as mgr


def test_delegate_stops_modal():
    # Replace NSApp with a mock that records calls
    mock_app = Mock()
    mgr.NSApp = lambda: mock_app

    delegate = mgr.SettingsWindowDelegate.alloc().init()

    # Simulate windowWillClose_ notification
    delegate.windowWillClose_(None)

    assert mock_app.stopModalWithCode_.called, "Delegate did not call stopModalWithCode_()"


if __name__ == "__main__":
    test_delegate_stops_modal()
    print("✓ SettingsWindowDelegate stops modal as expected")
