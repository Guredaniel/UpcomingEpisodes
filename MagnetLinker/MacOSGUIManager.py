import rumps
import warnings
import threading
import webbrowser
import sys
from datetime import datetime, timedelta
import os
import time
import objc
import queue

# PyObjC imports for native Cocoa dialogs
from AppKit import (
    NSApplication, NSAlert, NSAlertStyleInformational, NSAlertStyleWarning,
    NSAlertStyleCritical, NSOpenPanel, NSFileHandlingPanelOKButton,
    NSSecureTextField, NSTextField, NSButton, NSWindowStyleMaskTitled,
    NSWindowStyleMaskClosable, NSWindowStyleMaskMiniaturizable,
    NSBackingStoreBuffered, NSPasteboard, NSPasteboardTypeString, NSString, NSArray,
    NSView, NSImage, NSApp, NSColor, NSFont, NSPanel, NSWindow, NSScrollView,
    NSVisualEffectView, NSVisualEffectBlendingModeBehindWindow, NSVisualEffectStateActive
)
from Foundation import NSThread, NSOperationQueue, NSBlockOperation, NSObject

# Constants for modern macOS window styling
try:
    from AppKit import NSWindowStyleMaskFullSizeContentView, NSWindowTitleHidden
except ImportError:
    NSWindowStyleMaskFullSizeContentView = 1 << 15
    NSWindowTitleHidden = 1

try:
    from AppKit import NSSwitch
    HAS_NSSWITCH = True
except ImportError:
    HAS_NSSWITCH = False

try:
    from AppKit import NSVisualEffectMaterialSidebar
except ImportError:
    NSVisualEffectMaterialSidebar = 11

try:
    from UserNotifications import (
        UNUserNotificationCenter,
        UNMutableNotificationContent,
        UNNotificationRequest,
        UNAuthorizationOptionAlert,
        UNAuthorizationOptionSound,
    )
    HAS_USER_NOTIFICATIONS = True
except ImportError:
    HAS_USER_NOTIFICATIONS = False

# Suppress PyObjC pointer warnings that occur when passing CGColorRefs
try:
    import objc
    warnings.filterwarnings("ignore", category=objc.ObjCPointerWarning)
except Exception:
    pass


# Module-level delegate to stop modal sessions when the settings window closes.
class SettingsWindowDelegate(NSObject):
    def windowWillClose_(self, notification):
        try:
            NSApp().stopModalWithCode_(0)
        except Exception:
            pass


# Helper class for handling button target/action in Cocoa
# This is needed because Python classes can't be used as Cocoa targets directly
class SettingsActionHandler(NSObject):
    """Objective-C compatible handler for settings button actions."""
    
    def initWithManager_(self, manager):
        self = objc.super(SettingsActionHandler, self).init()
        if self is None:
            return None
        self.manager = manager
        return self
    
    def saveSettingsClicked_(self, sender):
        """Handle save button click."""
        if hasattr(self.manager, '_save_all_settings'):
            self.manager._save_all_settings()
        if hasattr(self.manager, '_close_settings_'):
            self.manager._close_settings_(sender)
    
    def closeSettingsClicked_(self, sender):
        """Handle cancel button click."""
        if hasattr(self.manager, '_close_settings_'):
            self.manager._close_settings_(sender)
            
    def addSiteClicked_(self, sender):
        """Handle add site button click."""
        if hasattr(self.manager, '_add_site'):
            self.manager._add_site(sender)
            
    def removeSiteClicked_(self, sender):
        """Handle remove site button click."""
        if hasattr(self.manager, '_remove_site'):
            self.manager._remove_site(sender)
    
    def sidebarClicked_(self, sender):
        """Handle sidebar item click."""
        if hasattr(self.manager, '_show_settings_section'):
            section_name = sender.title().strip()
            self.manager._show_settings_section(section_name)
    
    def testConnectionClicked_(self, sender):
        """Handle test connection button click."""
        if hasattr(self.manager, '_settings_test_connection_'):
            self.manager._settings_test_connection_(sender)
    
    def clearCredentialsClicked_(self, sender):
        """Handle clear credentials button click."""
        if hasattr(self.manager, '_settings_clear_credentials_'):
            self.manager._settings_clear_credentials_(sender)


class MacOSGUIManager:
    """macOS-native GUI manager using rumps menu bar and PyObjC Cocoa dialogs."""
    
    def __init__(self, cache_manager, api_client):
        """Initialize the macOS GUI manager.
        
        Args:
            cache_manager: CacheManager instance for persistent settings
            api_client: APIClient instance for qBittorrent operations
        """
        self.cache_manager = cache_manager
        self.api_client = api_client
        
        # Load settings from cache
        self.monitor_clipboard_enabled = self.cache_manager.load_setting(
            "monitor_clipboard_enabled", True
        )
        self.cache_duration_minutes = self.cache_manager.load_setting(
            "cache_duration_minutes", 30.0
        )
        self.indefinite_selection = self.cache_manager.load_setting(
            "indefinite_selection", False
        )
        self.auto_launch_enabled = self.cache_manager.load_setting(
            "auto_launch_enabled", False
        )
        self.clipboard_check_interval = self.cache_manager.load_setting(
            "clipboard_check_interval", 0.5
        )
        
        # Site URLs
        self.site_rutor_url = self.cache_manager.load_setting(
            "site_rutor_url", "https://rutor.info"
        )
        self.site_ext_url = self.cache_manager.load_setting(
            "site_ext_url", "https://ext.to"
        )
        self.site_nyaa_url = self.cache_manager.load_setting(
            "site_nyaa_url", "https://nyaa.si"
        )
        self.site_ktuvit_url = self.cache_manager.load_setting(
            "site_ktuvit_url", "https://www.ktuvit.me"
        )
        
        # Dynamic Sites
        self.saved_sites = self.cache_manager.get_saved_sites()
        self._working_sites = list(self.saved_sites)
        
        # Clipboard monitoring
        self.last_magnet_url = ""
        self.cached_selection = None
        self.clipboard_monitor_running = False
        self.magnet_queue = queue.Queue()  # Thread-safe queue for magnet links
        self.clipboard_monitor_thread = None
        
        # Settings UI state
        self._current_settings_section = "General"
        self._settings_fields = {}
        
        # Create the rumps app
        self._create_menu_bar_app()
        
        # Hide from dock - only show in menu bar
        NSApplication.sharedApplication().setActivationPolicy_(1)

        # Set application icon
        icon = self._get_app_icon()
        if icon:
            NSApp().setApplicationIconImage_(icon)
        
        # Setup auto-launch on initialization
        self._setup_auto_launch()
        
        # Request notification permissions
        self._setup_notifications()

    def _setup_notifications(self):
        """Request permission to show macOS banner notifications."""
        if HAS_USER_NOTIFICATIONS:
            try:
                center = UNUserNotificationCenter.currentNotificationCenter()
                options = UNAuthorizationOptionAlert | UNAuthorizationOptionSound
                
                def auth_completion(granted, error):
                    if not granted:
                        print("[DEBUG] Notification permission denied.")
                    if error:
                        print(f"[DEBUG] Notification error: {error}")
                        
                center.requestAuthorizationWithOptions_completionHandler_(options, auth_completion)
            except Exception as e:
                print(f"[DEBUG] Error setting up notifications: {e}")

    def _get_app_icon(self):
        """Get the application icon as NSImage."""
        icon_path = None
        for icon_file in ["icon.icns", "icon.png"]:
            potential_path = os.path.join(os.path.dirname(__file__), icon_file)
            if os.path.exists(potential_path):
                icon_path = potential_path
                break
        
        if icon_path:
            return NSImage.alloc().initWithContentsOfFile_(icon_path)
        return None
        
    def _setup_auto_launch(self):
        """Setup or remove LaunchAgent for auto-launch on login."""
        try:
            if self.auto_launch_enabled:
                self._create_launch_agent()
            else:
                self._remove_launch_agent()
        except Exception as e:
            print(f"[DEBUG] Error setting up auto-launch: {e}")
    
    def _create_launch_agent(self):
        """Create a LaunchAgent to auto-launch the app at login."""
        try:
            import subprocess
            
            # Get the app's Python script path
            app_script = os.path.join(os.path.dirname(__file__), "MagnetApp.py")
            python_executable = sys.executable
            
            # LaunchAgent plist content
            plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.magnetlinker.app</string>
    <key>Program</key>
    <string>{python_executable}</string>
    <key>ProgramArguments</key>
    <array>
        <string>{python_executable}</string>
        <string>{app_script}</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <false/>
</dict>
</plist>"""
            
            # Create LaunchAgents directory if it doesn't exist
            launch_agents_dir = os.path.expanduser("~/Library/LaunchAgents")
            if not os.path.exists(launch_agents_dir):
                os.makedirs(launch_agents_dir, mode=0o755)
            
            # Write plist file
            plist_path = os.path.join(launch_agents_dir, "com.magnetlinker.app.plist")
            with open(plist_path, "w") as f:
                f.write(plist_content)
            
            os.chmod(plist_path, 0o644)
            
            # Load the LaunchAgent
            subprocess.run(
                ["launchctl", "load", plist_path],
                capture_output=True
            )
            
            print(f"[DEBUG] LaunchAgent created at {plist_path}")
        except Exception as e:
            print(f"[DEBUG] Error creating LaunchAgent: {e}")
            raise
    
    def _remove_launch_agent(self):
        """Remove the LaunchAgent to disable auto-launch."""
        try:
            import subprocess
            
            plist_path = os.path.expanduser("~/Library/LaunchAgents/com.magnetlinker.app.plist")
            
            if os.path.exists(plist_path):
                # Unload the LaunchAgent
                subprocess.run(
                    ["launchctl", "unload", plist_path],
                    capture_output=True
                )
                
                # Remove the plist file
                os.remove(plist_path)
                print(f"[DEBUG] LaunchAgent removed")
        except Exception as e:
            print(f"[DEBUG] Error removing LaunchAgent: {e}")
        
    def _create_menu_bar_app(self):
        """Create the rumps menu bar application."""
        # Get icon path
        icon_path = None
        for icon_file in ["icon.icns", "icon.png"]:
            potential_path = os.path.join(os.path.dirname(__file__), icon_file)
            if os.path.exists(potential_path):
                icon_path = potential_path
                break
        
        # Create the app
        self.app = rumps.App(
            "MagnetLinker",
            icon=icon_path,
            template=icon_path is None  # Use template mode if no custom icon
        )
        
        # Main menu items
        self.app.menu = [
            rumps.MenuItem("Open qBittorrent", callback=self._menu_open_qbittorrent),
            rumps.MenuItem("Send Magnet Link", callback=self._menu_magnet_input),
            rumps.MenuItem("Send Torrent File", callback=self._menu_torrent_file),
            None,  # Separator
            self._create_sites_submenu(),
            None,  # Separator
            rumps.MenuItem("Clear Credentials", callback=self._menu_clear_credentials),
            rumps.MenuItem("Reset Selection", callback=self._menu_reset_selection),
            rumps.MenuItem("Preferences...", callback=self._menu_settings),
            None,  # Separator
            rumps.MenuItem("Toggle Clipboard Monitoring", callback=self._menu_toggle_clipboard),
            None,  # Separator
        ]
        
    def _create_sites_submenu(self):
        """Create the Sites submenu with dynamic website shortcuts."""
        sites_menu = rumps.MenuItem("Sites")
        self._populate_sites_menu(sites_menu)
        return sites_menu
        
    def _populate_sites_menu(self, menu_item):
        """Rebuilds the sites items in the menu dynamically."""
        try:
            menu_item.clear()
        except AttributeError:
            # Rumps lazily loads the NSMenu. If it's a new MenuItem, 
            # its internal _menu is None, causing clear() to throw an error.
            # We can safely ignore this because a new menu is already clear.
            pass

        for site in self.saved_sites:
            name = site.get("name", "Unnamed Site")
            url = site.get("url", "")
            if name and url:
                menu_item.add(
                    rumps.MenuItem(
                        name,
                        callback=lambda sender, u=url: self._open_url(u)
                    )
                )
    
    def _open_url(self, url):
        """Open URL in default browser."""
        try:
            webbrowser.open(url)
        except Exception as e:
            self.handle_error(f"Failed to open URL: {e}")
    
    def _menu_open_qbittorrent(self, sender):
        """Menu callback: Open qBittorrent web UI."""
        try:
            self.api_client.open_qbittorrent_web()
        except Exception as e:
            self.handle_error(f"Failed to open qBittorrent: {e}")
    
    def _menu_magnet_input(self, sender):
        """Menu callback: Open magnet link input dialog."""
        self.open_magnet_input_dialog()
    
    def _menu_torrent_file(self, sender):
        """Menu callback: Open torrent file picker."""
        self.open_torrent_file()
    
    def _menu_reset_selection(self, sender):
        """Menu callback: Reset cached selection."""
        self.reset_selection()
        self._show_notification("Selection Reset", "Cached content type selection has been cleared.")
    
    def _menu_settings(self, sender):
        """Menu callback: Open settings dialog."""
        try:
            self.show_settings_dialog()
        except Exception as e:
            print(f"[DEBUG] Error opening settings dialog: {e}")
            import traceback
            traceback.print_exc()
            self.handle_error(f"Failed to open settings dialog: {e}")
    
    def _menu_toggle_clipboard(self, sender):
        """Menu callback: Toggle clipboard monitoring."""
        self.monitor_clipboard_enabled = not self.monitor_clipboard_enabled
        self.cache_manager.save_setting("monitor_clipboard_enabled", self.monitor_clipboard_enabled)
        
        # Start the monitor thread if enabling and not already running
        if self.monitor_clipboard_enabled and not self.clipboard_monitor_running:
            self._start_clipboard_monitor()
        
        status = "enabled" if self.monitor_clipboard_enabled else "disabled"
        self._show_notification("Clipboard Monitoring", f"Clipboard monitoring is now {status}.")
    
    def _menu_clear_credentials(self, sender):
        """Menu callback: Clear saved credentials."""
        alert = NSAlert.alloc().init()
        if self._get_app_icon():
            alert.setIcon_(self._get_app_icon())
        alert.setMessageText_("Clear Credentials?")
        alert.setInformativeText_("Are you sure you want to remove the saved qBittorrent credentials?")
        alert.setAlertStyle_(NSAlertStyleWarning)
        alert.addButtonWithTitle_("Clear")
        alert.addButtonWithTitle_("Cancel")
        
        response = alert.runModal()
        
        if response == 1000:  # Clear
            self.cache_manager.clear_credentials()
            self._show_notification("Credentials Cleared", "Saved qBittorrent credentials have been removed.")
    
    def open_magnet_input_dialog(self):
        """Prompt user for magnet link input using native dialog.
        First checks clipboard for a magnet link, then shows input dialog."""
        # Try to get magnet link from clipboard
        try:
            pasteboard = NSPasteboard.generalPasteboard()
            clipboard_content = pasteboard.stringForType_(NSPasteboardTypeString)
            
            if clipboard_content:
                clipboard_str = str(clipboard_content)
                if clipboard_str.startswith("magnet:"):
                    # Found a magnet link in clipboard, use it directly
                    self.prompt_content_type(clipboard_str, from_clipboard=False)
                    return
        except Exception as e:
            print(f"[DEBUG] Error reading clipboard: {e}")
        
        # No magnet link found in clipboard, check last_magnet_url
        if self.last_magnet_url and self.last_magnet_url.startswith("magnet:"):
            # Use the last detected magnet link
            self.prompt_content_type(self.last_magnet_url, from_clipboard=False)
            return
        
        # No magnet link found, show error
        # Activate app to bring dialog to front
        try:
            NSApp().activateIgnoringOtherApps_(True)
        except Exception:
            pass
        
        alert = NSAlert.alloc().init()
        if self._get_app_icon():
            alert.setIcon_(self._get_app_icon())
        alert.setMessageText_("No Magnet Link Detected")
        alert.setInformativeText_("No magnet link found in clipboard or cache.\n\nPlease copy a magnet link first.")
        alert.setAlertStyle_(NSAlertStyleWarning)
        alert.addButtonWithTitle_("OK")
        alert.runModal()
    
    def prompt_content_type(self, magnet_url, from_clipboard=True):
        """Show dialog to select Movie or Series for magnet link.
        
        Args:
            magnet_url: The magnet link URL
            from_clipboard: Whether the link came from clipboard
        """
        try:
            if not self.cache_manager.credentials_exist():
                print(f"[DEBUG] No credentials found, prompting user")
                if self.prompt_credentials():
                    print(f"[DEBUG] Credentials saved, retrying prompt_content_type")
                    self.prompt_content_type(magnet_url, from_clipboard)
                else:
                    print(f"[DEBUG] User cancelled credential prompt")
                return
            
            print(f"[DEBUG] Credentials exist, showing content type dialog")
            
            # Activate app to bring dialog to front
            try:
                NSApp().activateIgnoringOtherApps_(True)
            except Exception:
                pass
            
            # Check for cached selection
            if self.cached_selection is not None:
                cached_option, cached_time = self.cached_selection
                if self.indefinite_selection:
                    is_series = (cached_option == "Series")
                    self._send_magnet(magnet_url, is_series)
                    return
                elif cached_time is not None:
                    expiration_time = cached_time + timedelta(minutes=self.cache_duration_minutes)
                    if datetime.now() < expiration_time:
                        is_series = (cached_option == "Series")
                        self._send_magnet(magnet_url, is_series)
                        return
                    else:
                        self.cached_selection = None
            
            # Show content type dialog with remember option
            alert = NSAlert.alloc().init()
            if self._get_app_icon():
                alert.setIcon_(self._get_app_icon())
            alert.setMessageText_("Content Type")
            message = (
                "A magnet link was detected in the clipboard.\n"
                if from_clipboard
                else ""
            )
            alert.setInformativeText_(message + "Is this a movie or a series?")
            alert.setAlertStyle_(NSAlertStyleInformational)
            
            # Add buttons - Cancel first to get focus (won't be highlighted)
            alert.addButtonWithTitle_("Cancel")
            alert.addButtonWithTitle_("Movie")
            alert.addButtonWithTitle_("Series")
            
            # Add checkbox for remember selection
            remember_checkbox = NSButton.alloc().initWithFrame_(((0, 0), (300, 18)))
            remember_checkbox.setButtonType_(3)  # NSSwitchButton
            remember_checkbox.setTitle_("Remember this selection")
            remember_checkbox.setState_(0)
            alert.setAccessoryView_(remember_checkbox)
            
            response = alert.runModal()
            
            if response == 1000:  # Cancel
                return
            elif response == 1001:  # Movie
                selection = "Movie"
            elif response == 1002:  # Series
                selection = "Series"
            else:  # Fallback
                return
            
            # Check if user wants to remember
            if remember_checkbox.state() == 1:  # Checkbox is checked
                # Ask for how long to remember
                remember_alert = NSAlert.alloc().init()
                if self._get_app_icon():
                    remember_alert.setIcon_(self._get_app_icon())
                remember_alert.setMessageText_("Remember Selection?")
                remember_alert.setInformativeText_(
                    f"Remember '{selection}' as:"
                )
                remember_alert.setAlertStyle_(NSAlertStyleInformational)
                
                remember_alert.addButtonWithTitle_("Indefinitely")
                remember_alert.addButtonWithTitle_("For 30 Minutes")
                remember_alert.addButtonWithTitle_("Don't Remember")
                
                remember_response = remember_alert.runModal()
                
                if remember_response == 1000:  # Indefinitely
                    self.cached_selection = (selection, None)
                    self.indefinite_selection = True
                    self.cache_manager.save_setting("indefinite_selection", True)
                elif remember_response == 1001:  # For time period
                    self.cached_selection = (selection, datetime.now())
                    self.indefinite_selection = False
                    self.cache_manager.save_setting("indefinite_selection", False)
                else:  # Don't Remember
                    self.cached_selection = None
                    self.indefinite_selection = False
            else:
                # Not checking, don't remember
                self.cached_selection = None
                self.indefinite_selection = False
            
            is_series = (selection == "Series")
            self._send_magnet(magnet_url, is_series)
            
        except Exception as e:
            self.handle_error(f"Error processing magnet link: {e}")
    
    def _send_magnet(self, magnet_url, is_series):
        """Send magnet link to qBittorrent."""
        try:
            self.api_client.open_qbittorrent_with_magnet(magnet_url, is_series)
            # Silently add without showing notification
        except Exception as e:
            error_msg = str(e)
            if any(x in error_msg for x in ["No route to host", "connection", "timeout"]):
                self.handle_error(
                    "Cannot connect to qBittorrent.\n"
                    "Check your network connection and qBittorrent Web UI settings."
                )
            else:
                self.handle_error(f"Failed to add magnet: {e}")
    
    def prompt_credentials(self):
        """Show username/password prompt dialog.
        
        Returns:
            bool: True if credentials were entered, False if cancelled
        """
        # Activate app to bring dialog to front
        try:
            NSApp().activateIgnoringOtherApps_(True)
        except Exception:
            pass
        
        alert = NSAlert.alloc().init()
        if self._get_app_icon():
            alert.setIcon_(self._get_app_icon())
        alert.setMessageText_("qBittorrent Credentials")
        alert.setInformativeText_("Enter your qBittorrent credentials:")
        alert.setAlertStyle_(NSAlertStyleInformational)
        
        # Create username field
        username_field = NSTextField.alloc().initWithFrame_(
            ((0, 0), (300, 24))
        )
        username_field.setPlaceholderString_("Username")
        alert.setAccessoryView_(username_field)
        
        # Add buttons
        alert.addButtonWithTitle_("OK")
        alert.addButtonWithTitle_("Cancel")
        
        response = alert.runModal()
        
        if response == 1000:  # OK
            username = username_field.stringValue()
            
            # Now ask for password
            password_alert = NSAlert.alloc().init()
            if self._get_app_icon():
                password_alert.setIcon_(self._get_app_icon())
            password_alert.setMessageText_("qBittorrent Password")
            password_alert.setInformativeText_("Enter your qBittorrent password:")
            password_alert.setAlertStyle_(NSAlertStyleInformational)
            
            password_field = NSSecureTextField.alloc().initWithFrame_(
                ((0, 0), (300, 24))
            )
            password_field.setPlaceholderString_("Password")
            password_alert.setAccessoryView_(password_field)
            
            password_alert.addButtonWithTitle_("OK")
            password_alert.addButtonWithTitle_("Cancel")
            
            password_response = password_alert.runModal()
            
            if password_response == 1000:  # OK
                password = password_field.stringValue()
                
                if username and password:
                    try:
                        self.cache_manager.save_credentials(username, password)
                        self._show_notification("Credentials Saved", "qBittorrent credentials have been saved.")
                        return True
                    except Exception as e:
                        self.handle_error(f"Failed to save credentials: {e}")
                        return False
                else:
                    self.handle_error("Please enter both username and password.")
                    return False
        
        return False
    
    def open_torrent_file(self):
        """Open file picker for .torrent files and process selection."""
        try:
            if not self.cache_manager.credentials_exist():
                if self.prompt_credentials():
                    self.open_torrent_file()
                return
            
            # Activate app to bring dialog to front
            try:
                NSApp().activateIgnoringOtherApps_(True)
            except Exception:
                pass
            
            # Create file open panel
            panel = NSOpenPanel.openPanel()
            panel.setTitle_("Select Torrent File")
            panel.setCanChooseFiles_(True)
            panel.setCanChooseDirectories_(False)
            panel.setAllowsMultipleSelection_(False)
            panel.setAllowedFileTypes_(NSArray.arrayWithObject_("torrent"))
            
            # Show panel
            if panel.runModal() == NSFileHandlingPanelOKButton:
                file_url = panel.URLs()[0]
                file_path = file_url.path()
                
                # Prompt for content type
                alert = NSAlert.alloc().init()
                if self._get_app_icon():
                    alert.setIcon_(self._get_app_icon())
                alert.setMessageText_("Content Type")
                alert.setInformativeText_("Is this torrent for a movie or a series?")
                alert.setAlertStyle_(NSAlertStyleInformational)
                
                alert.addButtonWithTitle_("Movie")
                alert.addButtonWithTitle_("Series")
                alert.addButtonWithTitle_("Cancel")
                
                response = alert.runModal()
                
                if response == 1000:  # Movie
                    is_series = False
                elif response == 1001:  # Series
                    is_series = True
                else:  # Cancel
                    return
                
                # Send torrent
                try:
                    self.api_client.open_qbittorrent_with_torrent_file(file_path, is_series)
                    # Silently add without showing notification
                except Exception as e:
                    self.handle_error(f"Failed to add torrent: {e}")
        
        except Exception as e:
            self.handle_error(f"Failed to open torrent file: {e}")
    
    def reset_selection(self):
        """Clear the cached content type selection."""
        self.cached_selection = None
        self.indefinite_selection = False
        self.cache_manager.save_setting("indefinite_selection", False)
    
    def show_settings_dialog(self):
        """Show settings dialog with modern macOS System Settings design language."""
        self._settings_fields = {}
        self._current_settings_section = "General"
        
        self._action_handler = SettingsActionHandler.alloc().initWithManager_(self)
        
        # Create a thoroughly modern window (transparent titlebar merging with content)
        window = NSPanel.alloc().initWithContentRect_styleMask_backing_defer_(
            ((100, 100), (800, 600)),
            NSWindowStyleMaskTitled | NSWindowStyleMaskClosable | NSWindowStyleMaskMiniaturizable | NSWindowStyleMaskFullSizeContentView,
            NSBackingStoreBuffered,
            False
        )
        window.setTitlebarAppearsTransparent_(True)
        window.setTitleVisibility_(NSWindowTitleHidden)
        window.setTitle_("Settings")
        window.center()
        
        from AppKit import NSFloatingWindowLevel
        window.setLevel_(NSFloatingWindowLevel)
        
        # Ensure the window is key and frontmost
        window.makeKeyAndOrderFront_(None)
        
        try:
            NSApp().activateIgnoringOtherApps_(True)
        except Exception:
            pass
        
        main_container = NSView.alloc().initWithFrame_(((0, 0), (800, 600)))
        main_container.setWantsLayer_(True)
        main_layer = main_container.layer()
        main_layer.setBackgroundColor_(NSColor.windowBackgroundColor().CGColor())
        
        # Create modern sidebar reaching the top
        sidebar = NSVisualEffectView.alloc().initWithFrame_(((0, 0), (220, 600)))
        sidebar.setMaterial_(NSVisualEffectMaterialSidebar)
        sidebar.setBlendingMode_(NSVisualEffectBlendingModeBehindWindow)
        sidebar.setState_(NSVisualEffectStateActive)
        sidebar.setWantsLayer_(True)
        
        main_container.addSubview_(sidebar)
        
        # Offset sidebar items downwards to avoid window traffic lights
        sidebar_items = [
            ("General", "gear", 520),
            ("Directories", "folder", 480),
            ("qBittorrent", "download", 440),
            ("Sites", "link", 400),
        ]
        
        self._sidebar_buttons = {}
        for item_name, icon_name, y_pos in sidebar_items:
            button = self._create_enhanced_sidebar_button(item_name, icon_name, (15, y_pos))
            sidebar.addSubview_(button)
            self._sidebar_buttons[item_name] = button
            button.setTarget_(self._action_handler)
            button.setAction_("sidebarClicked:")
        
        # Create content area container (right side panel)
        self._content_view = NSView.alloc().initWithFrame_(((220, 50), (580, 550)))
        self._content_view.setWantsLayer_(True)
        content_layer = self._content_view.layer()
        content_layer.setBackgroundColor_(NSColor.windowBackgroundColor().CGColor())
        main_container.addSubview_(self._content_view)
        
        # Create subtle separator line between content and buttons
        separator = NSView.alloc().initWithFrame_(((220, 50), (580, 1)))
        separator.setWantsLayer_(True)
        separator.layer().setBackgroundColor_(NSColor.separatorColor().CGColor())
        main_container.addSubview_(separator)
        
        # Bottom area (Modern macOS usually skips this, but preserving to retain exact flow)
        button_area = NSView.alloc().initWithFrame_(((220, 0), (580, 50)))
        button_area.setWantsLayer_(True)
        btn_layer = button_area.layer()
        btn_layer.setBackgroundColor_(NSColor.windowBackgroundColor().CGColor())
        
        cancel_button = NSButton.alloc().initWithFrame_(((400, 10), (80, 32)))
        cancel_button.setTitle_("Cancel")
        cancel_button.setBezelStyle_(1)  # Rounded rect button
        cancel_button.setFont_(NSFont.systemFontOfSize_weight_(13, 0.23))
        cancel_button.setTarget_(self._action_handler)
        cancel_button.setAction_("closeSettingsClicked:")
        button_area.addSubview_(cancel_button)
        
        save_button = NSButton.alloc().initWithFrame_(((490, 10), (80, 32)))
        save_button.setTitle_("Save")
        save_button.setBezelStyle_(1)  # Rounded rect button
        save_button.setFont_(NSFont.systemFontOfSize_weight_(13, 0.23))
        save_button.setTarget_(self._action_handler)
        save_button.setAction_("saveSettingsClicked:")
        try:
            save_button.setKeyEquivalent_("\r")  # Return key
        except:
            pass
        button_area.addSubview_(save_button)
        
        main_container.addSubview_(button_area)
        
        window.setContentView_(main_container)
        
        self._settings_window = window
        self._sidebar_items = ["General", "Directories", "qBittorrent", "Sites"]
        
        self._show_settings_section("General")
        
        delegate = SettingsWindowDelegate.alloc().init()
        window.setDelegate_(delegate)
        self._settings_window_delegate = delegate

        # Set up Edit menu for keyboard shortcuts in the settings window
        try:
            self._setup_edit_menu()
        except Exception as e:
            print(f"[DEBUG] Failed to setup Edit menu: {e}")

        NSApp().runModalForWindow_(window)
    
    def _create_enhanced_sidebar_button(self, title, icon_name, position):
        """Create an enhanced sidebar button matching the macOS System Settings style."""
        button = NSButton.alloc().initWithFrame_((position, (190, 32)))
        button.setTitle_(f"  {title}")
        button.setBezelStyle_(3)  # Rounded bezel for proper highlighting
        button.setButtonType_(7)  # Toggle button
        button.setAlignment_(0)  # Left-aligned
        
        font = NSFont.systemFontOfSize_weight_(14, 0.0)
        button.setFont_(font)
        
        return button

    def _create_settings_group(self, frame_rect, container):
        """Create a rounded rect container for grouping settings (card UI)."""
        group_view = NSView.alloc().initWithFrame_(frame_rect)
        group_view.setWantsLayer_(True)
        layer = group_view.layer()
        layer.setCornerRadius_(10)
        layer.setBorderWidth_(1)
        layer.setBorderColor_(NSColor.separatorColor().CGColor())
        layer.setBackgroundColor_(NSColor.controlBackgroundColor().CGColor())
        container.addSubview_(group_view)
        return group_view

    def _add_divider(self, container, y_pos, width=500):
        """Add a subtle horizontal divider line within a settings group."""
        divider = NSView.alloc().initWithFrame_(((0, y_pos), (width, 1)))
        divider.setWantsLayer_(True)
        divider.layer().setBackgroundColor_(NSColor.separatorColor().CGColor())
        container.addSubview_(divider)
    
    def _create_section_title(self, title, position):
        """Create an enhanced section title label."""
        label = NSTextField.alloc().initWithFrame_((position, (500, 36)))
        label.setStringValue_(title)
        label.setBezeled_(False)
        label.setDrawsBackground_(False)
        label.setEditable_(False)
        label.setSelectable_(False)
        font = NSFont.systemFontOfSize_weight_(28, 0.3)  # Large, prominent weight
        label.setFont_(font)
        label.setTextColor_(NSColor.labelColor())
        return label
    
    def _create_modern_label(self, text, position):
        """Create a standard macOS style text label."""
        label = NSTextField.alloc().initWithFrame_((position, (460, 20)))
        label.setStringValue_(text)
        label.setBezeled_(False)
        label.setDrawsBackground_(False)
        label.setEditable_(False)
        label.setSelectable_(False)
        font = NSFont.systemFontOfSize_weight_(14, 0.0) 
        label.setFont_(font)
        label.setTextColor_(NSColor.labelColor())
        return label
    
    def _create_secondary_label(self, text, position):
        """Create a secondary text label with smaller font."""
        label = NSTextField.alloc().initWithFrame_((position, (470, 16)))
        label.setStringValue_(text)
        label.setBezeled_(False)
        label.setDrawsBackground_(False)
        label.setEditable_(False)
        label.setSelectable_(False)
        font = NSFont.systemFontOfSize_(12)
        label.setFont_(font)
        label.setTextColor_(NSColor.secondaryLabelColor())
        return label

    def _sidebar_clicked_(self, sender):
        """Handle sidebar item click."""
        section_name = sender.title().strip()
        self._show_settings_section(section_name)
    
    def _show_settings_section(self, section_name):
        """Display the specified settings section."""
        # Save Sites tab state if we are leaving it
        if getattr(self, '_current_settings_section', None) == "Sites" and section_name != "Sites":
            self._save_working_sites_state()
            
        # Clear previous content
        for subview in self._content_view.subviews():
            subview.removeFromSuperview()
        
        # Update sidebar button states
        for item_name, button in self._sidebar_buttons.items():
            button.setState_(1 if item_name == section_name else 0)
        
        # Create appropriate content view
        if section_name == "General":
            self._create_general_content()
        elif section_name == "Directories":
            self._create_directories_content()
        elif section_name == "qBittorrent":
            self._create_qbittorrent_content()
        elif section_name == "Sites":
            self._create_sites_content()
        
        self._current_settings_section = section_name
        
        # Set keyboard focus to the first text field in the section
        self._set_initial_focus(section_name)
    
    def _set_initial_focus(self, section_name):
        """Set keyboard focus to the first text field in the current section."""
        try:
            if section_name == "General" and 'cache_duration' in self._settings_fields:
                self._settings_window.makeFirstResponder_(self._settings_fields['cache_duration'])
            elif section_name == "Directories" and 'series_dir' in self._settings_fields:
                self._settings_window.makeFirstResponder_(self._settings_fields['series_dir'])
            elif section_name == "qBittorrent" and 'qb_url' in self._settings_fields:
                self._settings_window.makeFirstResponder_(self._settings_fields['qb_url'])
            elif section_name == "Sites" and hasattr(self, '_site_rows') and self._site_rows:
                self._settings_window.makeFirstResponder_(self._site_rows[0]['name_field'])
        except Exception as e:
            print(f"[DEBUG] Error setting initial focus: {e}")
    
    def _setup_edit_menu(self):
        """Set up the Edit menu with standard keyboard shortcuts for the settings window."""
        try:
            from AppKit import NSMenu, NSMenuItem
            
            mainMenu = NSApplication.sharedApplication().mainMenu()
            if mainMenu is None:
                mainMenu = NSMenu.alloc().init()
                NSApplication.sharedApplication().setMainMenu_(mainMenu)
            
            # Check if Edit menu already exists
            editMenu = None
            for item in mainMenu.itemArray():
                if item.title() == "Edit":
                    editMenu = item.submenu()
                    break
            
            if editMenu is None:
                editMenu = NSMenu.alloc().initWithTitle_("Edit")
                editItem = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("Edit", None, "")
                editItem.setSubmenu_(editMenu)
                mainMenu.addItem_(editItem)
            
            # Add standard edit items if not present
            if editMenu.numberOfItems() == 0:
                undoItem = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("Undo", "undo:", "z")
                editMenu.addItem_(undoItem)
                
                editMenu.addItem_(NSMenuItem.separatorItem())
                
                cutItem = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("Cut", "cut:", "x")
                editMenu.addItem_(cutItem)
                
                copyItem = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("Copy", "copy:", "c")
                editMenu.addItem_(copyItem)
                
                pasteItem = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("Paste", "paste:", "v")
                editMenu.addItem_(pasteItem)
                
                editMenu.addItem_(NSMenuItem.separatorItem())
                
                selectAllItem = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("Select All", "selectAll:", "a")
                editMenu.addItem_(selectAllItem)
        except Exception as e:
            print(f"[DEBUG] Error setting up Edit menu: {e}")
    
    def _settings_test_connection_(self, sender):
        """Settings callback: Test qBittorrent connection."""
        try:
            result = self.api_client.test_connection(self.api_client.qbittorrent_url)
            if result:
                self._show_notification("Connection Successful", f"Successfully connected to qBittorrent at {self.api_client.qbittorrent_url}")
            else:
                self.handle_error("Failed to connect to qBittorrent.")
        except Exception as e:
            error_msg = str(e)
            if "401" in error_msg or "credentials" in error_msg.lower():
                self.handle_error("Authentication failed.\n\nCheck your username and password in settings.")
            elif "connection" in error_msg.lower():
                self.handle_error("Cannot reach qBittorrent.\n\nCheck the URL and network connection in settings.")
            else:
                self.handle_error(f"Connection test failed:\n\n{error_msg}")
    
    def _settings_clear_credentials_(self, sender):
        """Settings callback: Clear saved credentials."""
        alert = NSAlert.alloc().init()
        alert.setMessageText_("Clear Credentials?")
        alert.setInformativeText_("Are you sure you want to remove the saved qBittorrent credentials?")
        alert.setAlertStyle_(NSAlertStyleWarning)
        alert.addButtonWithTitle_("Clear")
        alert.addButtonWithTitle_("Cancel")
        
        response = alert.runModal()
        
        if response == 1000:  # Clear
            self.cache_manager.clear_credentials()
            self._show_notification("Credentials Cleared", "Saved qBittorrent credentials have been removed.")
            self._show_settings_section("qBittorrent")
    
    def _create_general_content(self):
        """Create General settings content using modern Card UI."""
        container = NSView.alloc().initWithFrame_(((0, 0), (580, 550)))
        
        title = self._create_section_title("General", (40, 480))
        container.addSubview_(title)
        
        # Group 1: Auto Launch
        group1 = self._create_settings_group(((40, 400), (500, 60)), container)
        
        autolaunch_label = self._create_modern_label("Auto-Launch on Login", (20, 20))
        group1.addSubview_(autolaunch_label)
        
        if HAS_NSSWITCH:
            autolaunch_switch = NSSwitch.alloc().initWithFrame_(((430, 18), (50, 24)))
            autolaunch_switch.setState_(1 if self.auto_launch_enabled else 0)
        else:
            autolaunch_switch = NSButton.alloc().initWithFrame_(((430, 18), (50, 24)))
            autolaunch_switch.setButtonType_(3)
            autolaunch_switch.setTitle_("")
            autolaunch_switch.setState_(1 if self.auto_launch_enabled else 0)
        group1.addSubview_(autolaunch_switch)
        self._settings_fields['auto_launch'] = autolaunch_switch
        
        # Group 2: Cache & Monitoring (3 rows, 70px each, Total Height 210)
        group2 = self._create_settings_group(((40, 160), (500, 210)), container)
        
        # Row 1: Cache selection duration (Base: 140)
        cache_label = self._create_modern_label("Cache Selection Duration (minutes)", (20, 140 + 38))
        group2.addSubview_(cache_label)
        cache_help = self._create_secondary_label("0 = always ask, 30 = remember for 30 mins", (20, 140 + 16))
        group2.addSubview_(cache_help)
        
        cache_field = NSTextField.alloc().initWithFrame_(((400, 140 + 24), (80, 24)))
        cache_field.setStringValue_(str(self.cache_duration_minutes))
        cache_field.setBezelStyle_(1)
        cache_field.setEditable_(True)
        cache_field.setSelectable_(True)
        group2.addSubview_(cache_field)
        self._settings_fields['cache_duration'] = cache_field
        
        self._add_divider(group2, 140)
        
        # Row 2: Clipboard monitoring (Base: 70)
        monitor_label = self._create_modern_label("Clipboard Monitoring", (20, 70 + 38))
        group2.addSubview_(monitor_label)
        monitor_help = self._create_secondary_label("Toggle monitoring from the menu bar", (20, 70 + 16))
        group2.addSubview_(monitor_help)
        
        monitor_status = self._create_secondary_label(
            "🟢 Enabled" if self.monitor_clipboard_enabled else "🔴 Disabled",
            (400, 70 + 26)
        )
        group2.addSubview_(monitor_status)
        
        self._add_divider(group2, 70)
        
        # Row 3: Clipboard Interval (Base: 0)
        interval_label = self._create_modern_label("Clipboard Check Interval (sec)", (20, 0 + 38))
        group2.addSubview_(interval_label)
        interval_help = self._create_secondary_label("Lower values = faster detection", (20, 0 + 16))
        group2.addSubview_(interval_help)
        
        interval_field = NSTextField.alloc().initWithFrame_(((400, 0 + 24), (80, 24)))
        interval_field.setStringValue_(str(self.clipboard_check_interval))
        interval_field.setBezelStyle_(1)
        interval_field.setEditable_(True)
        interval_field.setSelectable_(True)
        group2.addSubview_(interval_field)
        self._settings_fields['clipboard_interval'] = interval_field
        
        self._content_view.addSubview_(container)
    
    def _create_directories_content(self):
        """Create Directories settings content using modern Card UI."""
        container = NSView.alloc().initWithFrame_(((0, 0), (580, 550)))
        
        title = self._create_section_title("Directories", (40, 480))
        container.addSubview_(title)
        
        # Directories Group (2 rows, Total Height 120)
        group = self._create_settings_group(((40, 340), (500, 120)), container)
        
        # Series Directory (Base: 60)
        series_label = self._create_modern_label("Series Directory", (20, 60 + 20))
        group.addSubview_(series_label)
        
        series_field = NSTextField.alloc().initWithFrame_(((180, 60 + 18), (300, 24)))
        series_field.setStringValue_(self.api_client.series_directory)
        series_field.setBezelStyle_(1)
        series_field.setEditable_(True)
        series_field.setSelectable_(True)
        group.addSubview_(series_field)
        self._settings_fields['series_dir'] = series_field
        
        self._add_divider(group, 60)
        
        # Movies Directory (Base: 0)
        movies_label = self._create_modern_label("Movies Directory", (20, 0 + 20))
        group.addSubview_(movies_label)
        
        movies_field = NSTextField.alloc().initWithFrame_(((180, 0 + 18), (300, 24)))
        movies_field.setStringValue_(self.api_client.movies_directory)
        movies_field.setBezelStyle_(1)
        movies_field.setEditable_(True)
        movies_field.setSelectable_(True)
        group.addSubview_(movies_field)
        self._settings_fields['movies_dir'] = movies_field
        
        self._content_view.addSubview_(container)
    
    def _create_qbittorrent_content(self):
        """Create qBittorrent settings content using modern Card UI."""
        container = NSView.alloc().initWithFrame_(((0, 0), (580, 550)))
        
        title = self._create_section_title("qBittorrent", (40, 480))
        container.addSubview_(title)
        
        # Server Group
        group1 = self._create_settings_group(((40, 390), (500, 60)), container)
        
        url_label = self._create_modern_label("Server URL", (20, 20))
        group1.addSubview_(url_label)
        
        url_field = NSTextField.alloc().initWithFrame_(((150, 18), (330, 24)))
        url_field.setStringValue_(self.api_client.qbittorrent_url)
        url_field.setBezelStyle_(1)
        url_field.setEditable_(True)
        url_field.setSelectable_(True)
        group1.addSubview_(url_field)
        self._settings_fields['qb_url'] = url_field
        
        # Auth Group (3 rows, Height 180)
        group2 = self._create_settings_group(((40, 180), (500, 180)), container)
        
        # Username (Base: 120)
        user_label = self._create_modern_label("Username", (20, 120 + 20))
        group2.addSubview_(user_label)
        
        user_field = NSTextField.alloc().initWithFrame_(((150, 120 + 18), (330, 24)))
        user_field.setPlaceholderString_("Optional")
        user_field.setBezelStyle_(1)
        user_field.setEditable_(True)
        user_field.setSelectable_(True)
        try:
            if self.cache_manager.credentials_exist():
                creds = self.cache_manager.load_credentials()
                if creds:
                    user_field.setStringValue_(creds[0])
        except:
            pass
        group2.addSubview_(user_field)
        self._settings_fields['qb_user'] = user_field
        
        self._add_divider(group2, 120)
        
        # Password (Base: 60)
        pass_label = self._create_modern_label("Password", (20, 60 + 20))
        group2.addSubview_(pass_label)
        
        pass_field = NSSecureTextField.alloc().initWithFrame_(((150, 60 + 18), (330, 24)))
        pass_field.setPlaceholderString_("Optional")
        pass_field.setBezelStyle_(1)
        pass_field.setEditable_(True)
        pass_field.setSelectable_(True)
        group2.addSubview_(pass_field)
        self._settings_fields['qb_pass'] = pass_field
        
        self._add_divider(group2, 60)
        
        # Status & Action (Base: 0)
        creds_status = "✓ Saved" if self.cache_manager.credentials_exist() else "✗ Not saved"
        status_label = self._create_secondary_label(f"Status: {creds_status}", (20, 0 + 22))
        group2.addSubview_(status_label)
        
        test_btn = NSButton.alloc().initWithFrame_(((200, 0 + 16), (130, 28)))
        test_btn.setTitle_("Test Connection")
        test_btn.setBezelStyle_(2)
        test_btn.setTarget_(self._action_handler)
        test_btn.setAction_("testConnectionClicked:")
        group2.addSubview_(test_btn)
        
        clear_btn = NSButton.alloc().initWithFrame_(((350, 0 + 16), (130, 28)))
        clear_btn.setTitle_("Clear Credentials")
        clear_btn.setBezelStyle_(2)
        clear_btn.setTarget_(self._action_handler)
        clear_btn.setAction_("clearCredentialsClicked:")
        group2.addSubview_(clear_btn)
        
        self._content_view.addSubview_(container)
    
    def _create_sites_content(self):
        """Create Sites settings content using modern Card UI."""
        container = NSView.alloc().initWithFrame_(((0, 0), (580, 550)))
        
        title = self._create_section_title("Sites", (40, 480))
        container.addSubview_(title)
        
        # Scrollable Group
        group = self._create_settings_group(((40, 70), (500, 390)), container)
        
        # NSScrollView setup for dynamic list
        self._sites_scroll_view = NSScrollView.alloc().initWithFrame_(((1, 1), (498, 388)))
        self._sites_scroll_view.setHasVerticalScroller_(True)
        self._sites_scroll_view.setDrawsBackground_(False)
        self._sites_scroll_view.setBorderType_(0)
        
        self.sites_document_view = NSView.alloc().initWithFrame_(((0, 0), (480, 388)))
        self._sites_scroll_view.setDocumentView_(self.sites_document_view)
        group.addSubview_(self._sites_scroll_view)
        
        # Add Site Button
        add_btn = NSButton.alloc().initWithFrame_(((40, 20), (120, 28)))
        add_btn.setTitle_("Add Site")
        add_btn.setBezelStyle_(2)
        add_btn.setTarget_(self._action_handler)
        add_btn.setAction_("addSiteClicked:")
        container.addSubview_(add_btn)
        
        if not self._working_sites:
            self._working_sites = [{"name": "", "url": ""}]
            
        self._rebuild_sites_ui()
        self._content_view.addSubview_(container)

    def _rebuild_sites_ui(self):
        """Rebuild the text fields in the scroll view based on _working_sites."""
        for v in list(self.sites_document_view.subviews()):
            v.removeFromSuperview()
            
        row_height = 40
        num_sites = len(self._working_sites)
        total_height = max(388, num_sites * row_height + 20)
        
        self.sites_document_view.setFrameSize_((480, total_height))
        self._site_rows = []
        
        for i, site in enumerate(self._working_sites):
            y = total_height - (i + 1) * row_height - 10
            
            # Site Name Field
            name_field = NSTextField.alloc().initWithFrame_(((20, y), (140, 24)))
            name_field.setStringValue_(site.get("name", ""))
            name_field.setPlaceholderString_("Site Name")
            name_field.setBezelStyle_(1)
            name_field.setEditable_(True)
            name_field.setSelectable_(True)
            self.sites_document_view.addSubview_(name_field)
            
            # Site URL Field
            url_field = NSTextField.alloc().initWithFrame_(((170, y), (250, 24)))
            url_field.setStringValue_(site.get("url", ""))
            url_field.setPlaceholderString_("https://...")
            url_field.setBezelStyle_(1)
            url_field.setEditable_(True)
            url_field.setSelectable_(True)
            self.sites_document_view.addSubview_(url_field)
            
            # Remove Button
            rm_btn = NSButton.alloc().initWithFrame_(((430, y), (40, 24)))
            rm_btn.setTitle_("-")
            rm_btn.setBezelStyle_(2)
            rm_btn.setTarget_(self._action_handler)
            rm_btn.setAction_("removeSiteClicked:")
            rm_btn.setTag_(i)
            self.sites_document_view.addSubview_(rm_btn)
            
            self._site_rows.append({
                "name_field": name_field,
                "url_field": url_field
            })
            
        self.sites_document_view.scrollPoint_((0, total_height))

    def _add_site(self, sender):
        """Action to add a blank site row."""
        self._save_working_sites_state()
        self._working_sites.append({"name": "", "url": ""})
        self._rebuild_sites_ui()
        
    def _remove_site(self, sender):
        """Action to remove a specific site row."""
        self._save_working_sites_state()
        idx = sender.tag()
        if 0 <= idx < len(self._working_sites):
            self._working_sites.pop(idx)
            self._rebuild_sites_ui()
            
    def _save_working_sites_state(self):
        """Save text field values back into the memory list before destroying them."""
        if hasattr(self, '_site_rows'):
            new_working = []
            for row in self._site_rows:
                new_working.append({
                    "name": row['name_field'].stringValue(),
                    "url": row['url_field'].stringValue()
                })
            self._working_sites = new_working

    def _close_settings_(self, sender):
        """Close the settings window."""
        if hasattr(self, '_settings_window'):
            self._settings_window.close()
            NSApp().stopModalWithCode_(0)
    
    def _save_all_settings(self):
        """Save all settings from all tabs."""
        try:
            # Save auto-launch setting
            if 'auto_launch' in self._settings_fields:
                auto_launch_checked = self._settings_fields['auto_launch'].state() == 1
                if auto_launch_checked != self.auto_launch_enabled:
                    self.auto_launch_enabled = auto_launch_checked
                    self.cache_manager.save_setting("auto_launch_enabled", auto_launch_checked)
                    # Update launch agent
                    self._setup_auto_launch()
            
            # Save clipboard interval
            if 'clipboard_interval' in self._settings_fields:
                new_interval = self._settings_fields['clipboard_interval'].stringValue()
                try:
                    interval_secs = float(new_interval)
                    if interval_secs < 0.1:
                        self.handle_error("Clipboard check interval must be at least 0.1 seconds.")
                        return
                    if interval_secs > 10.0:
                        self.handle_error("Clipboard check interval must be at most 10.0 seconds.")
                        return
                    self.cache_manager.save_setting("clipboard_check_interval", interval_secs)
                    self.clipboard_check_interval = interval_secs
                except ValueError:
                    self.handle_error("Clipboard check interval must be a valid number (e.g., 0.5)")
                    return
            
            # Validate qBittorrent URL
            if 'qb_url' in self._settings_fields:
                new_url = self._settings_fields['qb_url'].stringValue()
                if not new_url:
                    self.handle_error("qBittorrent URL is required.")
                    return
                if not (new_url.startswith("http://") or new_url.startswith("https://")):
                    self.handle_error("qBittorrent URL must start with http:// or https://")
                    return
                self.cache_manager.save_setting("qbittorrent_url", new_url)
                self.api_client.qbittorrent_url = new_url
            
            # Save qBittorrent credentials if provided
            if 'qb_user' in self._settings_fields and 'qb_pass' in self._settings_fields:
                username = self._settings_fields['qb_user'].stringValue()
                password = self._settings_fields['qb_pass'].stringValue()
                
                # Only save if both are provided
                if username and password:
                    try:
                        self.cache_manager.save_credentials(username, password)
                        self._show_notification("Credentials Updated", "qBittorrent credentials have been saved.")
                    except Exception as e:
                        self.handle_error(f"Failed to save credentials: {e}")
                        return
            
            # Save directories
            if 'series_dir' in self._settings_fields:
                new_series = self._settings_fields['series_dir'].stringValue()
                if not new_series:
                    self.handle_error("Series directory is required.")
                    return
                self.cache_manager.save_setting("series_directory", new_series)
                self.api_client.series_directory = new_series
            
            if 'movies_dir' in self._settings_fields:
                new_movies = self._settings_fields['movies_dir'].stringValue()
                if not new_movies:
                    self.handle_error("Movies directory is required.")
                    return
                self.cache_manager.save_setting("movies_directory", new_movies)
                self.api_client.movies_directory = new_movies
            
            # Save Dynamic Sites
            if self._current_settings_section == "Sites":
                self._save_working_sites_state()
                
            valid_sites = []
            for s in self._working_sites:
                name = s.get("name", "").strip()
                url = s.get("url", "").strip()
                if name and url:
                    if not (url.startswith("http://") or url.startswith("https://")):
                        url = "https://" + url
                    valid_sites.append({"name": name, "url": url})
            
            self.saved_sites = valid_sites
            self.cache_manager.save_sites(valid_sites)
            
            # Dynamically update the sites menu items 
            if "Sites" in self.app.menu:
                self._populate_sites_menu(self.app.menu["Sites"])
            
            # Save cache duration
            if 'cache_duration' in self._settings_fields:
                new_cache = self._settings_fields['cache_duration'].stringValue()
                try:
                    cache_mins = float(new_cache)
                    self.cache_manager.save_setting("cache_duration_minutes", cache_mins)
                    self.cache_duration_minutes = cache_mins
                except ValueError:
                    self.handle_error("Cache duration must be a valid number (e.g., 30)")
                    return
            
            self._show_notification("Settings Saved", "All settings have been updated successfully.")
        except Exception as e:
            self.handle_error(f"Error saving settings: {e}")
    
    def check_clipboard(self):
        """Monitor clipboard for magnet links."""
        try:
            if not self.monitor_clipboard_enabled:
                return
            
            pasteboard = NSPasteboard.generalPasteboard()
            clipboard_content = pasteboard.stringForType_(NSPasteboardTypeString)
            
            if clipboard_content:
                clipboard_str = str(clipboard_content)
                if (clipboard_str.startswith("magnet:") and 
                    clipboard_str != self.last_magnet_url):
                    print(f"[DEBUG] New magnet link detected!")
                    self.last_magnet_url = clipboard_str
                    # Add to queue for main thread to process
                    self.magnet_queue.put(clipboard_str)
                    # Try to activate app if available
                    try:
                        NSApp().activateIgnoringOtherApps_(True)
                    except:
                        pass  # NSApp might not be available in test context
        except Exception as e:
            print(f"[DEBUG] Error in check_clipboard: {e}")
    
    def _show_magnet_dialog(self, magnet_url):
        """Show the content type dialog for a magnet link (runs on main thread)."""
        try:
            # Ensure we're on the main thread
            if not NSThread.isMainThread():
                print(f"[DEBUG] Not on main thread, scheduling for main thread")
                # Schedule on main thread using GCD (Grand Central Dispatch)
                from Foundation import NSOperationQueue, NSBlockOperation
                main_queue = NSOperationQueue.mainQueue()
                op = NSBlockOperation.blockOperationWithBlock_(
                    lambda: self.prompt_content_type(magnet_url, from_clipboard=True)
                )
                main_queue.addOperation_(op)
                return
            
            self.prompt_content_type(magnet_url, from_clipboard=True)
        except Exception as e:
            print(f"[DEBUG] Error in _show_magnet_dialog: {e}")
            import traceback
            traceback.print_exc()
            try:
                self.handle_error(f"Error processing magnet link: {e}")
            except:
                print(f"[DEBUG] Could not show error dialog")
    
    def handle_error(self, message):
        """Show error dialog and copy message to clipboard.
        
        Args:
            message: The error message to display
        """
        # Try to copy to clipboard (non-critical)
        try:
            pasteboard = NSPasteboard.generalPasteboard()
            pasteboard.clearContents()
            pasteboard.setString_forType_(NSString.stringWithString_(message), NSPasteboardTypeString)
        except Exception:
            pass  # Clipboard copy is optional
        
        # Show alert (critical)
        try:
            alert = NSAlert.alloc().init()
            if self._get_app_icon():
                alert.setIcon_(self._get_app_icon())
            alert.setMessageText_("Error")
            alert.setInformativeText_(message)
            alert.setAlertStyle_(NSAlertStyleCritical)
            alert.addButtonWithTitle_("OK")
            alert.runModal()
        except Exception as e:
            print(f"Error displaying error dialog: {e}")
    
    def _show_notification(self, title, message):
        """Show a system notification (macOS native).
        
        Args:
            title: Notification title
            message: Notification message
        """
        if HAS_USER_NOTIFICATIONS:
            try:
                center = UNUserNotificationCenter.currentNotificationCenter()
                content = UNMutableNotificationContent.alloc().init()
                content.setTitle_(title)
                content.setBody_(message)
                
                identifier = f"MagnetLinker-{time.time()}"
                request = UNNotificationRequest.requestWithIdentifier_content_trigger_(
                    identifier, content, None
                )
                
                def completion_handler(error):
                    if error:
                        print(f"[DEBUG] Error delivering notification: {error}")
                        
                center.addNotificationRequest_withCompletionHandler_(request, completion_handler)
                return
            except Exception as e:
                print(f"[DEBUG] Error showing banner notification: {e}")
                # Fall back to alert on error
                
        # Fallback to standard alert if UNUserNotificationCenter is not available
        try:
            alert = NSAlert.alloc().init()
            if self._get_app_icon():
                alert.setIcon_(self._get_app_icon())
            alert.setMessageText_(title)
            alert.setInformativeText_(message)
            alert.setAlertStyle_(NSAlertStyleInformational)
            alert.addButtonWithTitle_("OK")
            alert.runModal()
        except Exception:
            pass
    
    def run(self):
        """Start the rumps menu bar app."""
        # Set flag before starting threads to avoid race condition
        self.clipboard_monitor_running = True
        
        # Start clipboard monitoring thread
        if self.monitor_clipboard_enabled:
            self._start_clipboard_monitor()
        
        # Start a thread to process magnet links from queue
        self._start_queue_processor()
        
        # Run the app
        self.app.run()
    
    def _start_queue_processor(self):
        """Start a thread to process magnet links from the queue."""
        def process_queue():
            while self.clipboard_monitor_running or not self.magnet_queue.empty():
                try:
                    magnet_url = self.magnet_queue.get(timeout=0.2)
                    print(f"[DEBUG] Processing magnet from queue")
                    self._show_magnet_dialog(magnet_url)
                except queue.Empty:
                    pass  # Queue is empty, that's fine
                except Exception as e:
                    print(f"[DEBUG] Error processing queue: {e}")
        
        queue_thread = threading.Thread(target=process_queue, daemon=True)
        queue_thread.start()
    
    def _start_clipboard_monitor(self):
        """Start the clipboard monitoring thread."""
        # Set flag to indicate monitoring is running
        self.clipboard_monitor_running = True
        
        def monitor():
            while self.clipboard_monitor_running:
                try:
                    if self.monitor_clipboard_enabled:
                        self.check_clipboard()
                    time.sleep(self.clipboard_check_interval)
                except Exception as e:
                    print(f"[DEBUG] Monitor error: {e}")
        
        self.clipboard_monitor_thread = threading.Thread(target=monitor, daemon=True)
        self.clipboard_monitor_thread.start()