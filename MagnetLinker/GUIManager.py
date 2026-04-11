"""Cross-platform GUI manager using tkinter/customtkinter for Windows/Linux.

Provides tray icon interface, settings dialogs, and torrent/magnet link handling.
Uses customtkinter for modern UI theming and dark mode support.
"""

from __future__ import annotations

import logging
import os
import sys
import threading
import webbrowser
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

import pyperclip
import tkinter as tk
import tkinter.filedialog
import tkinter.font as tkfont
from tkinter import messagebox

from PIL import Image, ImageDraw, ImageFont
from customtkinter import (
    CTkToplevel, CTkFrame, CTkLabel, CTkTabview, CTkButton, CTkEntry,
    CTkCheckBox, CTkFont
)
from pystray import Icon, MenuItem, Menu

# Only import winreg if on Windows
if sys.platform.startswith("win32"):
    import winreg

logger = logging.getLogger(__name__)


class GUIManager:
    """Cross-platform GUI manager for MagnetLinker application.

    Handles tray icon operations, settings dialogs, and file operations on Windows/Linux.
    On macOS, uses MacOSGUIManager instead.
    """
    def __init__(
        self, root: tk.Tk, cache_manager: Any, api_client: Any
    ) -> None:
        """Initialize GUIManager with tkinter root and dependencies.

        Args:
            root: The tkinter root window.
            cache_manager: Cache manager for storing settings and credentials.
            api_client: API client for qBittorrent communication.
        """
        self.root: tk.Tk = root
        self.cache_manager: Any = cache_manager
        self.api_client: Any = api_client
        self.tk_default_font: tkfont.Font = tkfont.nametofont("TkDefaultFont")
        self.ctk_default_font: CTkFont = CTkFont(
            family=self.tk_default_font.cget("family"),
            size=self.tk_default_font.cget("size")
        )

        # Initialize last_magnet_url and settings loaded from cache
        self.last_magnet_url: str = ""
        self.monitor_clipboard_enabled: bool = self.cache_manager.load_setting(
            "monitor_clipboard_enabled", True
        )
        self.add_to_startup: bool = self.cache_manager.load_setting(
            "add_to_startup", False
        )

        # Sites settings (defaults provided)
        self.site_rutor_url: str = self.cache_manager.load_setting(
            "site_rutor_url", "https://rutor.info"
        )
        self.site_ext_url: str = self.cache_manager.load_setting(
            "site_ext_url", "https://ext.to"
        )
        self.site_nyaa_url: str = self.cache_manager.load_setting(
            "site_nyaa_url", "https://nyaa.si"
        )

        # Saved dynamic torrent sites from macOS port
        self.saved_sites: list[dict[str, str]] = self.cache_manager.get_saved_sites()
        self._working_sites: list[dict[str, str]] = list(self.saved_sites)
        self._site_rows: list[dict[str, Any]] = []

        # Clipboard check interval (in seconds)
        self.clipboard_check_interval: float = self.cache_manager.load_setting(
            "clipboard_check_interval", 0.5
        )

        # Initialize termination flag to signal tasks to stop
        self.should_exit: bool = False
        self.prompt_win_geometry: Optional[str] = None

        # Cached selection for movie/series with timestamp: (option, timestamp)
        self.cached_selection: Optional[tuple[str, Optional[datetime]]] = None
        self.cache_duration_minutes: float = self.cache_manager.load_setting(
            "cache_duration_minutes", 30.0
        )
        self.indefinite_selection: bool = self.cache_manager.load_setting(
            "indefinite_selection", False
        )
        self.tray_thread: Optional[threading.Thread] = None
        self.tray_icon: Optional[Icon] = None
        self.settings_window: Optional[CTkToplevel] = None
        self.mac_settings_win: Optional[tk.Toplevel] = None
        self.sites_frame: Optional[tk.Frame] = None
        self.error_label: Optional[CTkLabel] = None
        self.close_button: Optional[CTkButton] = None
        self.settings_tabview: Optional[CTkTabview] = None
        self.rutor_btn: Optional[tk.Button] = None
        self.ext_btn: Optional[tk.Button] = None
        self.nyaa_btn: Optional[tk.Button] = None

        if sys.platform == "darwin":
            self.root.withdraw()  # Hide the window
            # On macOS, ensure the dock icon is hidden
            try:
                import objc  # noqa: F401
                from Foundation import NSObject  # noqa: F401
                self.root.createcommand('tk::mac::ReopenApplication', self.dummyCallback)
                self.root.createcommand('::tk::mac::OnHide', self.dummyCallback)
                self.root.createcommand('::tk::mac::OnShow', self.dummyCallback)
                # Hide dock icon
                from AppKit import NSApp
                NSApp().setActivationPolicy_(1)  # NSApplicationActivationPolicyAccessory
                os.environ["TK_SILENCE_DEPRECATION"] = "1"
            except ImportError as e:
                logger.warning("macOS-specific imports failed: %s", e)
        else:
            self.root.withdraw()  # Hide the main window immediately

            # Set window attributes to keep it hidden from taskbar
            if sys.platform.startswith("win32"):
                self.root.attributes('-alpha', 0)  # Make fully transparent
                # Remove from taskbar on Windows
                self.root.attributes('-toolwindow', True)

        # Configure root window properties
        self.root.resizable(False, False)
        self.root.title("MagnetLinker")

        # Preload the settings window at startup
        self.load_settings_window()
        self.root.withdraw()
        # Create the mac settings
        if sys.platform == "darwin":
            self.create_mac_settings_button()

        # Start monitoring the clipboard if enabled
        if self.monitor_clipboard_enabled:
            self.start_clipboard_monitor()

        # Start the system tray icon
        if sys.platform == "darwin":
            logger.info(
                "System tray icon is not supported on macOS due to technical limitations. "
                "The app will run without a tray icon."
            )
        else:
            self.tray_thread = threading.Thread(target=self.run_tray, daemon=True)
            self.tray_thread.start()

        # Start the Tk event loop to keep the application running
        self.root.mainloop()

    def dummyCallback(self, *args: Any) -> None:
        """Empty callback for macOS window management.

        Args:
            *args: Variable arguments from macOS window events.

        Returns:
            None
        """
        pass

    def create_mac_settings_button(self) -> None:
        """Create a small floating window with tray actions for macOS.

        Returns:
            None
        """
        self.mac_settings_win = tk.Toplevel(self.root)
        self.mac_settings_win.title("MagnetLinker")
        self.mac_settings_win.geometry("180x290")
        self.mac_settings_win.resizable(False, False)
        self.mac_settings_win.protocol("WM_DELETE_WINDOW", lambda: self.root.quit())  # Prevent closing

        btn_frame = tk.Frame(self.mac_settings_win)
        btn_frame.pack(expand=True, fill="both", padx=8, pady=8)

        tk.Button(
            btn_frame,
            text="Open qBittorrent",
            command=lambda: self.api_client.open_qbittorrent_web(),
            width=18,
            height=1
        ).pack(fill="x", pady=2)

        tk.Button(
            btn_frame,
            text="Send magnet link",
            command=lambda: self.open_qbittorrent_with_magnet(pyperclip.paste(), from_clipboard=False),
            width=18,
            height=1
        ).pack(fill="x", pady=2)

        tk.Button(
            btn_frame,
            text="Send torrent file",
            command=self.open_qbittorrent_with_torrent_file,
            width=18,
            height=1
        ).pack(fill="x", pady=2)

        # Site buttons arranged in a 2x2 grid (build but only pack when enabled)
        self.sites_frame = tk.Frame(btn_frame)

        self.rutor_btn = tk.Button(self.sites_frame, text="rutor", command=lambda: webbrowser.open(self.site_rutor_url), width=9, height=1)
        self.ext_btn = tk.Button(self.sites_frame, text="ext.to", command=lambda: webbrowser.open(self.site_ext_url), width=9, height=1)
        self.nyaa_btn = tk.Button(self.sites_frame, text="nyaa.si", command=lambda: webbrowser.open(self.site_nyaa_url), width=9, height=1)

        # Place buttons in 2 columns
        self.rutor_btn.grid(row=0, column=0, padx=0, pady=2, sticky="ew")
        self.ext_btn.grid(row=0, column=1, padx=0, pady=2, sticky="ew")
        self.nyaa_btn.grid(row=1, column=0, padx=0, pady=2, sticky="ew")

        # Make columns expand evenly
        self.sites_frame.grid_columnconfigure(0, weight=1)
        self.sites_frame.grid_columnconfigure(1, weight=1)

        # Always show sites
        self.sites_frame.pack(fill="x", pady=(6, 6))

        tk.Button(
            btn_frame,
            text="Reset selection",
            command=self.reset_selection,
            width=18,
            height=1
        ).pack(fill="x", pady=2)

        tk.Button(
            btn_frame,
            text="Settings",
            command=lambda: self.settings_window.deiconify(),
            width=18,
            height=1
        ).pack(fill="x", pady=2)

        tk.Button(
            btn_frame,
            text="Exit",
            command=lambda: self.root.quit(),
            width=18,
            height=1
        ).pack(fill="x", pady=2)

    def setup_sites_tab(self) -> None:
        """Create the Sites tab allowing editing of saved torrent site entries.

        Returns:
            None
        """
        assert self.settings_tabview is not None, "settings_tabview must be initialized"
        sites_tab = self.settings_tabview.tab("Sites")

        if not self._working_sites:
            self._working_sites = [{"name": "", "url": ""}]

        header_frame = CTkFrame(sites_tab, fg_color="transparent")
        header_frame.pack(fill="x", padx=10, pady=(10, 0))

        CTkLabel(
            header_frame,
            text="Name",
            text_color="white",
            width=18,
            anchor="w",
        ).pack(side="left", padx=(0, 5))
        CTkLabel(
            header_frame,
            text="URL",
            text_color="white",
            width=40,
            anchor="w",
        ).pack(side="left", padx=(0, 5))

        add_button = CTkButton(
            sites_tab,
            text="Add Site",
            width=120,
            command=self._add_site_row,
        )
        add_button.pack(anchor="w", padx=10, pady=(8, 10))

        self._sites_tab_body = CTkFrame(sites_tab, fg_color="transparent")
        self._sites_tab_body.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self._rebuild_sites_tab()

    def save_site_setting(self, key: str, value: str) -> None:
        """Save a site URL to cache and update the button command/live URL.

        Args:
            key: The setting key (e.g., 'site_rutor_url').
            value: The new URL value.

        Returns:
            None
        """
        if not value:
            return
        self.cache_manager.save_setting(key, value)
        setattr(self, key, value)
        # Update button commands if the sites_frame exists
        try:
            if key == "site_rutor_url" and hasattr(self, "rutor_btn") and self.rutor_btn:
                self.rutor_btn.configure(
                    command=lambda: webbrowser.open(self.site_rutor_url)
                )
            elif key == "site_ext_url" and hasattr(self, "ext_btn") and self.ext_btn:
                self.ext_btn.configure(
                    command=lambda: webbrowser.open(self.site_ext_url)
                )
            elif key == "site_nyaa_url" and hasattr(self, "nyaa_btn") and self.nyaa_btn:
                self.nyaa_btn.configure(
                    command=lambda: webbrowser.open(self.site_nyaa_url)
                )
        except Exception as e:
            logger.debug("Error updating site button: %s", e)

    def _save_sites_state(self) -> None:
        """Persist the current Sites tab rows to cache and update the tray menu."""
        valid_sites: list[dict[str, str]] = []
        for site in self._working_sites:
            name = site.get("name", "").strip()
            url = site.get("url", "").strip()
            if name and url:
                if not url.startswith(("http://", "https://")):
                    url = "https://" + url
                valid_sites.append({"name": name, "url": url})

        self.saved_sites = valid_sites
        self.cache_manager.save_sites(valid_sites)
        self._update_tray_menu()

    def _save_sites_from_entries(self) -> None:
        """Load values from the current site row widgets into working settings and persist them."""
        self._working_sites = []
        for row in self._site_rows:
            name = row["name_entry"].get().strip()
            url = row["url_entry"].get().strip()
            if name or url:
                self._working_sites.append({"name": name, "url": url})

        if not self._working_sites:
            self._working_sites = [{"name": "", "url": ""}]

        self._save_sites_state()

    def _rebuild_sites_tab(self) -> None:
        """Rebuild the Sites tab rows based on the current working sites."""
        for widget in self._sites_tab_body.winfo_children():
            widget.destroy()

        self._site_rows = []

        for i, site in enumerate(self._working_sites):
            row_frame = CTkFrame(self._sites_tab_body, fg_color="transparent")
            row_frame.pack(fill="x", pady=4)

            name_entry = CTkEntry(
                row_frame,
                width=18,
                fg_color="gray25",
                text_color="white",
            )
            name_entry.insert(0, site.get("name", ""))
            name_entry.pack(side="left", padx=(0, 5), fill="x", expand=True)
            name_entry.bind(
                "<FocusOut>",
                lambda event: self._save_sites_from_entries(),
            )

            url_entry = CTkEntry(
                row_frame,
                width=28,
                fg_color="gray25",
                text_color="white",
            )
            url_entry.insert(0, site.get("url", ""))
            url_entry.pack(side="left", padx=(0, 5), fill="x", expand=True)
            url_entry.bind(
                "<FocusOut>",
                lambda event: self._save_sites_from_entries(),
            )

            remove_button = CTkButton(
                row_frame,
                text="-",
                width=24,
                command=lambda index=i: self._remove_site_row(index),
            )
            remove_button.pack(side="right")

            self._site_rows.append(
                {
                    "name_entry": name_entry,
                    "url_entry": url_entry,
                    "frame": row_frame,
                }
            )

    def _add_site_row(self) -> None:
        """Add a new empty site row to the Sites tab."""
        self._save_sites_from_entries()
        self._working_sites.append({"name": "", "url": ""})
        self._rebuild_sites_tab()

    def _remove_site_row(self, index: int) -> None:
        """Remove a site row from the Sites tab."""
        self._save_sites_from_entries()
        if 0 <= index < len(self._working_sites):
            self._working_sites.pop(index)
        if not self._working_sites:
            self._working_sites = [{"name": "", "url": ""}]
        self._rebuild_sites_tab()

    def load_settings_window(self) -> None:
        """Build the settings window at startup and keep it hidden.

        The window is pre-built so that it can immediately be shown when requested.

        Returns:
            None
        """
        self.settings_window = CTkToplevel(self.root)
        self.settings_window.title("MagnetLinker - Settings")
        # Increase height to provide more vertical space for controls
        self.settings_window.geometry("400x540")
        # Override window close behavior to hide rather than destroy it.
        self.settings_window.protocol("WM_DELETE_WINDOW", self.settings_window.withdraw)
        self.settings_window.resizable(False, False)
        # Make window stay on top
        self.settings_window.attributes('-topmost', True)

        # Main frame for settings with a modern gradient background effect
        main_frame = CTkFrame(
            self.settings_window,
            fg_color=("#2B2B2B", "#1A1A1A"),
            corner_radius=15,
            border_width=2,
            border_color=("#444444", "#333333"),
        )
        main_frame.pack(fill="both", expand=True, padx=15, pady=15)

        # Add a stylish header
        header_frame = CTkFrame(main_frame, fg_color="transparent")
        header_frame.pack(fill="x", padx=15, pady=(15, 5))

        title_label = CTkLabel(
            header_frame,
            text="Settings",
            font=CTkFont(
                family=self.ctk_default_font.cget("family"),
                size=20,
                weight="bold",
            ),
            text_color=("#FFFFFF", "#E0E0E0"),
        )
        title_label.pack(side="left")

        # Create the tabview with modern styling
        self.settings_tabview = CTkTabview(
            main_frame,
            fg_color=("gray90", "gray17"),
            segmented_button_fg_color=("gray80", "gray20"),
            segmented_button_selected_color=("#1E90FF", "#2979FF"),
            segmented_button_selected_hover_color=("#1976D2", "#2962FF"),
            segmented_button_unselected_color=("gray75", "gray23"),
            segmented_button_unselected_hover_color=("gray70", "gray25"),
            text_color=("gray20", "gray90"),
        )
        self.settings_tabview.pack(fill="both", expand=True, padx=15, pady=(10, 5))

        # Add tabs
        self.settings_tabview.add("General")
        self.settings_tabview.add("qBittorrent")
        self.settings_tabview.add("Sites")
        self.settings_tabview.add("Directories")
        self.settings_tabview.set("General")  # Show General by default

        self.setup_general_tab()
        self.setup_qbittorrent_tab()
        self.setup_sites_tab()
        self.setup_directories_tab()

        # Create error message label above control frame
        self.error_label = CTkLabel(
            main_frame,
            text="",
            text_color="white",
            fg_color="#FF5555",  # Red background
            corner_radius=5,
            height=0,  # Initially collapsed
        )
        # (Not packed yet; will be shown when needed)

        # Add a close button that hides the window instead of destroying it
        self.close_button = CTkButton(
            main_frame, text="Close", command=self.settings_window.withdraw, width=100
        )
        self.close_button.pack(pady=10, padx=10)

        # Hide window initially
        self.settings_window.withdraw()
        logger.debug("Settings window loaded")

    def setup_directories_tab(self) -> None:
        """Setup content for Directories tab.

        Returns:
            None
        """
        assert self.settings_tabview is not None, "settings_tabview must be initialized"
        # Setup content for Directories tab
        directories_tab = self.settings_tabview.tab("Directories")

        # Series Directory entry
        self.configure_ctk_label(directories_tab, "Series directory:", pady=(10, 0))
        series_directory_entry = CTkEntry(
            directories_tab, width=40, fg_color="gray25", text_color="white"
        )
        series_directory_entry.insert(0, self.api_client.series_directory)
        series_directory_entry.pack(pady=(0, 10), padx=10, fill=tk.X)
        series_directory_entry.bind(
            "<KeyRelease>",
            lambda event: self.save_information(
                series_directory_entry.get().strip(), "series_directory"
            ),
        )

        # Movies Directory entry
        self.configure_ctk_label(directories_tab, "Movies directory:", pady=(10, 0))
        movies_directory_entry = CTkEntry(
            directories_tab, width=40, fg_color="gray25", text_color="white"
        )
        movies_directory_entry.insert(0, self.api_client.movies_directory)
        movies_directory_entry.pack(pady=(0, 10), padx=10, fill=tk.X)
        movies_directory_entry.bind(
            "<KeyRelease>",
            lambda event: self.save_information(
                movies_directory_entry.get().strip(), "movies_directory"
            ),
        )

    def setup_general_tab(self) -> None:
        """Setup content for General tab.

        Returns:
            None
        """
        assert self.settings_tabview is not None, "settings_tabview must be initialized"
        # Setup content for General tab
        general_tab = self.settings_tabview.tab("General")

        clipboard_var = tk.BooleanVar(value=self.monitor_clipboard_enabled)
        clipboard_check = CTkCheckBox(
            general_tab,
            text="Monitor clipboard for magnet links",
            variable=clipboard_var,
            onvalue=True,
            offvalue=False,
            text_color="white",
            command=lambda: self.update_setting(
                "monitor_clipboard_enabled", clipboard_var.get()
            ),
        )
        clipboard_check.pack(anchor="w", padx=10, pady=10)

        # Show info for macOS users
        if sys.platform == "darwin":
            info_label = CTkLabel(
                general_tab,
                text="On macOS, add this app to Login Items in\nSystem Settings for startup launch.",
                text_color="#FFD700",
            )
            info_label.pack(anchor="w", padx=10, pady=(0, 10))
        else:
            # Add to Startup check box
            startup_var = tk.BooleanVar(value=self.add_to_startup)
            startup_check = CTkCheckBox(
                general_tab,
                text="Add to startup",
                variable=startup_var,
                onvalue=True,
                offvalue=False,
                text_color="white",
                command=lambda: self.update_setting("add_to_startup", startup_var.get()),
            )
            startup_check.pack(anchor="w", padx=10, pady=10)

        # Cache selection duration (minutes) setting.
        duration_label = CTkLabel(
            general_tab,
            text="Cache selection duration (minutes):",
            text_color="white",
        )
        duration_label.pack(anchor="w", padx=10, pady=(10, 0))
        duration_entry = CTkEntry(
            general_tab, width=20, fg_color="gray25", text_color="white"
        )
        # Set initial value; convert to string.
        duration_entry.insert(0, str(self.cache_duration_minutes))
        duration_entry.pack(anchor="w", padx=10, pady=(0, 10), fill=tk.X)
        # When entry changes, update the setting.
        duration_entry.bind(
            "<KeyRelease>",
            lambda event: self.update_cache_duration(duration_entry.get().strip()),
        )

        # Clipboard check interval setting
        interval_label = CTkLabel(
            general_tab, text="Clipboard check interval (seconds):", text_color="white"
        )
        interval_label.pack(anchor="w", padx=10, pady=(10, 0))
        interval_entry = CTkEntry(
            general_tab, width=20, fg_color="gray25", text_color="white"
        )
        interval_entry.insert(0, str(self.clipboard_check_interval))
        interval_entry.pack(anchor="w", padx=10, pady=(0, 5), fill=tk.X)
        interval_entry.bind(
            "<KeyRelease>",
            lambda event: self.update_clipboard_interval(interval_entry.get().strip()),
        )

        # Help text for interval
        interval_help = CTkLabel(
            general_tab,
            text="Lower = faster detection, higher CPU. (0.1–2.0 sec recommended)",
            text_color="white",
            font=CTkFont(size=10),
            anchor="w",
            justify="left",
        )
        interval_help.pack(anchor="w", padx=10, pady=(0, 10), fill="x")

    def setup_qbittorrent_tab(self) -> None:
        """Setup content for qBittorrent tab.

        Returns:
            None
        """
        assert self.settings_tabview is not None, "settings_tabview must be initialized"
        # Setup content for qbittorrent tab
        qbittorrent_tab = self.settings_tabview.tab("qBittorrent")

        self.configure_ctk_label(
            qbittorrent_tab, "qBittorrent web URL:", pady=(10, 0)
        )
        qbittorrent_url_entry = CTkEntry(
            qbittorrent_tab, width=40, fg_color="gray25", text_color="white"
        )
        qbittorrent_url_entry.insert(0, self.api_client.qbittorrent_url)
        qbittorrent_url_entry.pack(pady=(0, 10), padx=10, fill=tk.X)
        qbittorrent_url_entry.bind(
            "<KeyRelease>",
            lambda event: self.save_information(
                qbittorrent_url_entry.get().strip(), "qbittorrent_url"
            ),
        )

        connection_buttons_frame = CTkFrame(qbittorrent_tab, fg_color="transparent")
        connection_buttons_frame.pack(pady=10)

        check_connection_button = CTkButton(
            connection_buttons_frame,
            text="Check connection",
            command=lambda: self.check_qbittorrent_connection(
                check_connection_button
            ),
            text_color="white",
        )
        check_connection_button.pack(side="left", padx=5)

        open_site_button = CTkButton(
            connection_buttons_frame,
            text="Open web UI",
            command=lambda: webbrowser.open(self.api_client.qbittorrent_url),
            text_color="white",
        )
        open_site_button.pack(side="left", padx=5)

        login_frame = CTkFrame(qbittorrent_tab, fg_color="transparent")
        login_frame.pack(pady=10)

        save_login_button = CTkButton(
            login_frame,
            text="Set credentials",
            command=lambda: self.prompt_qbittorrent_credentials(
                magnet=False, button=save_login_button
            ),
            text_color="white",
        )
        save_login_button.pack(side="left", padx=5)

        delete_login_button = CTkButton(
            login_frame,
            text="Clear credentials",
            command=lambda: self.delete_login_cache(delete_login_button),
            text_color="white",
        )
        delete_login_button.pack(side="left", padx=5)

    def save_information(self, address: str, setting_name: str) -> None:
        """Save information to cache.

        Args:
            address: The value to save.
            setting_name: The setting key name.

        Raises:
            ValueError: If setting_name is not recognized.

        Returns:
            None
        """
        valid_settings = {"series_directory", "movies_directory", "qbittorrent_url"}

        if setting_name not in valid_settings:
            raise ValueError(f"Unknown setting name: {setting_name}")

        setattr(self.api_client, setting_name, address)
        self.cache_manager.save_setting(setting_name, address)
        logger.debug("Saved setting %s: %s", setting_name, address)

    def delete_login_cache(self, button: CTkButton) -> None:
        """Delete the qBittorrent credentials from the cache.

        Args:
            button: The button to update with status.

        Returns:
            None
        """
        files_deleted = self.cache_manager.delete_login_cache()
        if files_deleted is True:
            button.configure(
                text="Login Data Removed", fg_color="green", hover_color="darkgreen"
            )
            logger.info("Login cache deleted")
        else:
            button.configure(
                text="No Login Data Found", fg_color="red", hover_color="darkred"
            )
            logger.debug("No login cache found to delete")

    def update_cache_duration(self, value: str) -> None:
        """Update the cache duration setting.

        Args:
            value: The duration value as a string.

        Returns:
            None
        """
        try:
            # Convert the entered value to a float (or int)
            new_duration = float(value)
            self.cache_duration_minutes = new_duration
            self.update_setting("cache_duration_minutes", new_duration)
            logger.debug("Cache duration updated to %f minutes", new_duration)
        except ValueError:
            logger.debug("Invalid cache duration value: %s", value)

    def update_clipboard_interval(self, value: str) -> None:
        """Update the clipboard check interval setting.

        Args:
            value: The interval value as a string (seconds).

        Returns:
            None
        """
        try:
            new_interval = float(value)
            # Validate range
            if new_interval < 0.1:
                new_interval = 0.1
            elif new_interval > 10.0:
                new_interval = 10.0
            self.clipboard_check_interval = new_interval
            self.cache_manager.save_setting("clipboard_check_interval", new_interval)
            logger.debug("Clipboard check interval updated to %f seconds", new_interval)
        except ValueError:
            logger.debug("Invalid clipboard interval value: %s", value)

    def check_qbittorrent_connection(self, button: CTkButton) -> None:
        """Check the connection to the qBittorrent web interface and update the button text.

        Args:
            button: The button to update with connection status.

        Returns:
            None
        """
        def run_check() -> None:
            button.configure(text="Testing...")
            try:
                success, message = self.api_client.check_qbittorrent_connection()
                if success:
                    button.configure(
                        text="Connection successful",
                        fg_color="green",
                        hover_color="darkgreen",
                    )
                    logger.info("qBittorrent connection successful")
                else:
                    button.configure(
                        text="Connection failed", fg_color="red", hover_color="darkred"
                    )
                    logger.warning("qBittorrent connection failed: %s", message)
            except Exception as e:
                button.configure(
                    text="Connection failed", fg_color="red", hover_color="darkred"
                )
                logger.exception("Error checking qBittorrent connection: %s", e)

        threading.Thread(target=run_check).start()

    def update_setting(self, setting_name: str, value: Any) -> None:
        """Update a setting and save it to the cache.

        Args:
            setting_name: The name of the setting to update.
            value: The new value for the setting.

        Returns:
            None
        """
        setattr(self, setting_name, value)
        self.cache_manager.save_setting(setting_name, value)

        if setting_name == "monitor_clipboard_enabled":
            if value:
                self.start_clipboard_monitor()
            else:
                # When disabling, simply set flag so scheduled checks stop
                self.should_exit = True
                logger.debug("Clipboard monitoring disabled")
        elif setting_name == "add_to_startup":
            # Only attempt to add to startup if on Windows
            if sys.platform.startswith("win32"):
                appName = "MagnetApp"
                regKeyPath = r"Software\Microsoft\Windows\CurrentVersion\Run"
                try:
                    regKey = winreg.OpenKey(
                        winreg.HKEY_CURRENT_USER, regKeyPath, 0, winreg.KEY_ALL_ACCESS
                    )
                    if value:
                        executable = sys.executable
                        winreg.SetValueEx(
                            regKey, appName, 0, winreg.REG_SZ, f'"{executable}"'
                        )
                        logger.info("Added application to Windows startup")
                    else:
                        try:
                            winreg.DeleteValue(regKey, appName)
                            logger.info("Removed application from Windows startup")
                        except FileNotFoundError:
                            pass
                    winreg.CloseKey(regKey)
                except Exception as e:
                    logger.exception("Error updating startup registry entry: %s", e)
            else:
                # On macOS/Linux, inform user this feature is not supported
                logger.debug("Add to startup is only supported on Windows")

    def start_clipboard_monitor(self) -> None:
        """Start periodic clipboard monitoring using Tk.after, avoiding a separate thread.

        Returns:
            None
        """
        # Reset the exit flag in case it was previously enabled
        self.should_exit = False
        logger.debug("Clipboard monitoring started")
        self.check_clipboard()

    def check_clipboard(self) -> None:
        """Check clipboard for new magnet link and schedule next check.

        Returns:
            None
        """
        if self.should_exit:
            return
        try:
            current_clipboard = pyperclip.paste()
            if (
                current_clipboard.startswith("magnet:")
                and current_clipboard != self.last_magnet_url
            ):
                self.last_magnet_url = current_clipboard
                logger.debug("New magnet link detected in clipboard")
                # Schedule the UI update on the main thread immediately
                self.root.after(
                    0,
                    self.open_qbittorrent_with_magnet,
                    current_clipboard,
                    True,
                )
        except Exception as e:
            logger.debug("Error checking clipboard: %s", e)
        # Schedule next clipboard check based on configurable interval
        interval_ms = int(self.clipboard_check_interval * 1000)
        self.root.after(interval_ms, self.check_clipboard)

    def open_qbittorrent_with_magnet(
        self, magnet_url: str, from_clipboard: bool = False
    ) -> None:
        """Send the magnet link to the qBittorrent web interface with authentication.

        If a cached selection exists (and is less than the specified duration), it is
        automatically used. Otherwise, the user is prompted to choose between movie or series.
        If the skip checkbox is checked when making a selection, that choice is cached.

        Args:
            magnet_url: The magnet link URL.
            from_clipboard: Whether the magnet link came from clipboard.

        Returns:
            None
        """
        try:
            if not magnet_url or not isinstance(magnet_url, str):
                self.handle_error("No valid magnet link found in clipboard")
                return
                
            if not magnet_url.startswith("magnet:"):
                self.handle_error("Invalid magnet link format")
                return
                
            if not self.cache_manager.credentials_exist():
                self.root.after(0, self.prompt_qbittorrent_credentials)
                return

            # macOS fix: temporarily deiconify root so Toplevel renders correctly
            root_was_withdrawn = False
            if sys.platform == "darwin" and not self.root.winfo_viewable():
                self.root.deiconify()
                root_was_withdrawn = True

            # Check for a previously cached selection.
            if self.cached_selection is not None:
                cached_option, cached_time = self.cached_selection
                if self.indefinite_selection:
                    is_series = (cached_option == "Series")
                    self.api_client.open_qbittorrent_with_magnet(magnet_url, is_series)
                    if root_was_withdrawn:
                        self.root.withdraw()
                    return
                elif cached_time is not None:
                    expiration_time = cached_time + timedelta(minutes=self.cache_duration_minutes)
                    if datetime.now() < expiration_time:
                        is_series = (cached_option == "Series")
                        self.api_client.open_qbittorrent_with_magnet(magnet_url, is_series)
                        if root_was_withdrawn:
                            self.root.withdraw()
                        return
                    else:
                        self.cached_selection = None

            def on_select(option):
                try:
                    if indefinite_var.get():
                        self.cached_selection = (option, None)  # None timestamp means indefinite
                        self.indefinite_selection = True
                    elif skip_var.get():
                        self.cached_selection = (option, datetime.now())
                        self.indefinite_selection = False
                    else:
                        self.cached_selection = None
                        self.indefinite_selection = False
                    self.cache_manager.save_setting("indefinite_selection", self.indefinite_selection)
                    is_series = (option == "Series")
                    try:
                        self.api_client.open_qbittorrent_with_magnet(magnet_url, is_series)
                    except Exception as e:
                        error_str = str(e)
                        if (
                            "No route to host" in error_str
                            or "Failed to establish a new connection" in error_str
                            or "Max retries exceeded" in error_str
                        ):
                            self.handle_error(
                                "Could not connect to qBittorrent at the configured address.\n"
                                "Please check your network connection and qBittorrent Web UI settings."
                            )
                        else:
                            self.handle_error(error_str)
                    geom = prompt_win.winfo_geometry()
                    parts = geom.split('+')
                    if len(parts) == 3:
                        self.prompt_win_geometry = f"+{parts[1]}+{parts[2]}"
                    prompt_win.destroy()
                    if root_was_withdrawn:
                        self.root.withdraw()
                except Exception as e:
                    self.handle_error(str(e))

            prompt_win = CTkToplevel(self.root)
            prompt_win.title("MagnetLinker - Content Type")
            prompt_win.attributes("-topmost", True)
            if self.prompt_win_geometry:
                prompt_win.geometry(f"320x180{self.prompt_win_geometry}")
            else:
                prompt_win.geometry("320x180")
            prompt_win.resizable(False, False)
            prompt_win.configure(fg_color="black")
            prompt_win.lift()
            prompt_win.focus_force()
            prompt_win.transient(self.root)

            if from_clipboard:
                prompt_label = CTkLabel(
                    prompt_win,
                    text="A magnet link was detected in the clipboard.\nIs this a movie or a series?",
                    text_color="white",
                    font=CTkFont(family=self.ctk_default_font.cget("family"), size=14, weight="normal")
                )
            else:
                prompt_label = CTkLabel(
                    prompt_win,
                    text="Is this a movie or a series?",
                    text_color="white",
                    font=CTkFont(family=self.ctk_default_font.cget("family"), size=14, weight="normal")
                )
            prompt_label.pack(pady=10)

            skip_var = tk.BooleanVar(value=False)
            indefinite_var = tk.BooleanVar(value=False)
            checkbox_frame = CTkFrame(prompt_win, fg_color="black")
            checkbox_frame.pack(pady=5)
            dialog_font = CTkFont(family=self.ctk_default_font.cget("family"), size=14, weight="normal")
            
            skip_checkbox = CTkCheckBox(
                checkbox_frame, 
                text=f"Remember for {self.cache_duration_minutes} minutes", 
                variable=skip_var, 
                text_color="white",
                command=lambda: self.handle_checkbox_toggle(skip_var, indefinite_var),
                font=dialog_font
            )
            skip_checkbox.pack(anchor="w", pady=2)
            indefinite_checkbox = CTkCheckBox(
                checkbox_frame, 
                text="Remember indefinitely", 
                variable=indefinite_var, 
                text_color="white",
                command=lambda: self.handle_checkbox_toggle(indefinite_var, skip_var),
                font=dialog_font
            )
            indefinite_checkbox.pack(anchor="w", pady=2)
            button_frame = CTkFrame(prompt_win, fg_color="black")
            button_frame.pack(pady=10)
            movie_button = CTkButton(
                button_frame,
                text="Movie",
                command=lambda: on_select("Movie"),
                text_color="white",
                font=dialog_font
            )
            movie_button.grid(row=0, column=0, padx=10)
            series_button = CTkButton(
                button_frame,
                text="Series",
                command=lambda: on_select("Series"),
                text_color="white",
                font=dialog_font
            )
            series_button.grid(row=0, column=1, padx=10)

            # macOS fix: force redraw
            if sys.platform == "darwin":
                prompt_win.update()
        except (ConnectionError, TimeoutError) as e:
            self.handle_error(f"Network error: {e}")
        except Exception as e:
            self.handle_error(f"Failed to open qBittorrent: {e}")

    def handle_checkbox_toggle(
        self, checked_var: tk.BooleanVar, other_var: tk.BooleanVar
    ) -> None:
        """Ensure only one checkbox can be selected at a time.

        Args:
            checked_var: The checked variable.
            other_var: The other variable to uncheck.

        Returns:
            None
        """
        if checked_var.get():
            other_var.set(False)

    def prompt_qbittorrent_credentials(
        self, magnet: bool = True, button: Optional[CTkButton] = None
    ) -> None:
        """Prompt the user for qBittorrent username and password credentials.

        Args:
            magnet: Whether to process magnet link after credentials are saved.
            button: Optional button to update with status.

        Returns:
            None
        """
        credentials_win = CTkToplevel()  # Create without parent
        credentials_win.title("MagnetLinker - qBittorrent Credentials")
        credentials_win.geometry("300x200")
        credentials_win.configure(fg_color="#1A1A1A")  # Match dark theme

        # Force the window to be on top and grab focus
        credentials_win.attributes('-topmost', True)
        credentials_win.lift()
        credentials_win.focus_force()
        credentials_win.grab_set()  # Make window modal
        credentials_win.resizable(False, False)

        # Add subtle border on macOS
        if sys.platform == "darwin":
            credentials_win.configure(border_width=1, border_color="#333333")

        self.configure_ctk_label(credentials_win, "Username:")
        username_entry = CTkEntry(
            credentials_win, width=40, fg_color="#2B2B2B", text_color="white"
        )
        username_entry.pack(pady=(0, 5), padx=10, fill="x")

        self.configure_ctk_label(credentials_win, "Password:")
        password_entry = CTkEntry(
            credentials_win, width=40, fg_color="#2B2B2B", text_color="white", show="*"
        )
        password_entry.pack(pady=(0, 5), padx=10, fill="x")

        def submit_credentials(magnet: bool, button: Optional[CTkButton]) -> None:
            username = username_entry.get().strip()
            password = password_entry.get().strip()
            if username and password:
                try:
                    self.cache_manager.save_credentials(username, password)
                    if button:
                        button.configure(
                            text="Credentials Saved",
                            fg_color="green",
                            hover_color="darkgreen",
                        )
                    logger.info("qBittorrent credentials saved")
                except Exception as e:
                    logger.exception("Error saving credentials: %s", e)
                    if button:
                        button.configure(
                            text="Failed Saving",
                            fg_color="red",
                            hover_color="darkred",
                        )
                finally:
                    credentials_win.grab_release()
                    credentials_win.destroy()
                    if magnet:
                        self.open_qbittorrent_with_magnet(self.last_magnet_url)
            else:
                self.handle_error("Please enter both username and password.")

        submit_button = CTkButton(
            credentials_win,
            text="Submit",
            command=lambda: submit_credentials(magnet, button),
            text_color="white",
            fg_color="#1E90FF",
            hover_color="#0066CC",
        )
        submit_button.pack(pady=10)

    def open_qbittorrent_with_torrent_file(self) -> None:
        """Prompt the user to select a torrent file and send it to qBittorrent.

        Returns:
            None
        """
        try:
            if not self.cache_manager.credentials_exist():
                self.handle_error(
                    "No qBittorrent credentials found. Please set them first."
                )
                self.prompt_qbittorrent_credentials(magnet=False)
                return

            # Open file dialog to select a torrent file
            torrent_file_path = tkinter.filedialog.askopenfilename(
                title="MagnetLinker - Select Torrent File",
                filetypes=[("Torrent Files", "*.torrent")],
            )
            if not torrent_file_path:
                return  # user cancelled the selection

            def on_select(option: str) -> None:
                try:
                    is_series = option == "Series"
                    self.api_client.open_qbittorrent_with_torrent_file(
                        torrent_file_path, is_series
                    )
                    logger.info("Torrent file sent to qBittorrent (series=%s)", is_series)
                    prompt_win.destroy()
                except Exception as e:
                    logger.exception("Error sending torrent file: %s", e)
                    self.handle_error(f"Failed to send torrent: {e}")

            # Create a prompt window to choose between Movie and Series
            prompt_win = CTkToplevel(self.root)
            prompt_win.title("MagnetLinker - Content Type")
            prompt_win.attributes("-topmost", True)
            prompt_win.geometry("320x120")
            prompt_win.configure(fg_color="black")
            prompt_win.lift()
            prompt_win.focus_force()
            prompt_win.resizable(False, False)

            prompt_label = CTkLabel(
                prompt_win,
                text="Is this torrent for a movie or a series?",
                text_color="white",
            )
            prompt_label.pack(pady=10)

            button_frame = CTkFrame(prompt_win, fg_color="black")
            button_frame.pack(pady=10)
            movie_button = CTkButton(
                button_frame,
                text="Movie",
                command=lambda: on_select("Movie"),
                text_color="white",
            )
            movie_button.grid(row=0, column=0, padx=10)
            series_button = CTkButton(
                button_frame,
                text="Series",
                command=lambda: on_select("Series"),
                text_color="white",
            )
            series_button.grid(row=0, column=1, padx=10)
        except Exception as e:
            logger.exception("Error opening torrent file dialog: %s", e)
            self.handle_error(f"Failed to open torrent file: {e}")

    def handle_error(self, error_message: str) -> None:
        """Display an error message to the user and copy it to the clipboard.

        Args:
            error_message: The error message to display.

        Returns:
            None
        """
        pyperclip.copy(error_message)
        messagebox.showerror("Error", error_message)
        logger.error("Error displayed to user: %s", error_message)

    def on_settings(self, icon: Any, item: Any) -> None:
        """Callback triggered when the user selects 'Settings' from the tray menu.

        Args:
            icon: The tray icon.
            item: The menu item.

        Returns:
            None
        """
        assert self.settings_window is not None, "settings_window must be initialized"
        self.root.after(0, lambda: self.settings_window.deiconify())
        logger.debug("Settings window displayed")

    def on_exit(self, icon: Any, item: Any) -> None:
        """Callback triggered when the user selects 'Exit' from the tray menu.

        Args:
            icon: The tray icon.
            item: The menu item.

        Returns:
            None
        """
        try:
            logger.info("Application exit requested")
            # Signal tasks to stop
            self.should_exit = True

            # Stop the tray icon first
            icon.stop()

            # Join tray_thread if it's alive and not the current thread
            if (
                hasattr(self, "tray_thread")
                and self.tray_thread
                and self.tray_thread.is_alive()
                and threading.current_thread() is not self.tray_thread
            ):
                self.tray_thread.join(timeout=1)

            # Schedule the window destruction after other operations
            self.root.after(100, self._cleanup_and_exit)
        except Exception as e:
            logger.exception("Error during exit: %s", e)
            # Force exit if normal cleanup fails
            os._exit(0)

    def _cleanup_and_exit(self) -> None:
        """Helper method to clean up and exit the application.

        Returns:
            None
        """
        try:
            logger.debug("Cleaning up and exiting application")
            # Destroy all top-level windows
            for widget in self.root.winfo_children():
                if isinstance(widget, (CTkToplevel, tk.Toplevel)):
                    widget.destroy()

            # Reset window attributes before destroying
            if sys.platform.startswith("win32"):
                self.root.attributes('-alpha', 1)
                self.root.attributes('-toolwindow', False)

            # Finally destroy the root window and quit
            self.root.destroy()
            self.root.quit()
            logger.info("Application cleanly shut down")
        except Exception as e:
            logger.exception("Error during cleanup: %s", e)
            # Force exit if normal cleanup fails
            os._exit(0)

    def reset_selection(self) -> None:
        """Reset the cached selection and indefinite flag.

        Returns:
            None
        """
        self.cached_selection = None
        self.indefinite_selection = False
        self.cache_manager.save_setting("indefinite_selection", False)
        logger.debug("Selection cache cleared")

    def create_tray_menu(self) -> Menu:
        """Create the tray menu.

        Returns:
            Menu: The tray menu.
        """
        sites_menu_items = []
        for site in self.saved_sites:
            name = site.get("name", "")
            url = site.get("url", "")
            if name and url:
                sites_menu_items.append(
                    MenuItem(name, lambda icon, item, url=url: webbrowser.open(url))
                )

        if not sites_menu_items:
            sites_menu_items.append(
                MenuItem(
                    "No saved sites",
                    lambda icon, item: None,
                    enabled=False,
                )
            )

        return Menu(
            MenuItem(
                "Open qBittorrent",
                lambda icon, item: self.api_client.open_qbittorrent_web(),
            ),
            MenuItem(
                "Send torrent file",
                lambda icon, item: self.open_qbittorrent_with_torrent_file(),
            ),
            MenuItem(
                "Sites",
                Menu(*sites_menu_items),
            ),
            MenuItem(
                "Reset selection", lambda icon, item: self.reset_selection()
            ),
            MenuItem("Settings", lambda icon, item: self.on_settings(icon, item)),
            Menu.SEPARATOR,
            MenuItem("Exit", lambda icon, item: self.on_exit(icon, item)),
        )

    def _update_tray_menu(self) -> None:
        """Refresh the tray menu to reflect changed site settings."""
        if self.tray_icon is None:
            return
        try:
            self.tray_icon.menu = self.create_tray_menu()
            if hasattr(self.tray_icon, "update_menu"):
                self.tray_icon.update_menu()
        except Exception as e:
            logger.debug("Unable to refresh tray menu: %s", e)

    def run_tray(self) -> None:
        """Run the system tray icon loop.

        Returns:
            None
        """
        try:
            icon = Icon(
                "MagnetLinker",
                self.create_image(),
                "MagnetLinker",
                menu=self.create_tray_menu(),
            )
            self.tray_icon = icon
            logger.info("System tray icon started")
            icon.run()
        except Exception as e:
            logger.exception("Error in tray icon loop: %s", e)

    def create_image(self) -> Image.Image:
        """Create an image for the system tray icon.

        Returns:
            Image: The tray icon image.
        """
        size = (64, 64)
        image = Image.new("RGBA", size, (255, 255, 255, 0))
        draw = ImageDraw.Draw(image)
        try:
            font = ImageFont.truetype("seguiemj.ttf", 47)
        except IOError:
            font = ImageFont.load_default()
        draw.text(
            (0, 11),
            "🧲",
            font=font,
            fill=(255, 255, 255),
            stroke_width=5,
            stroke_fill="black",
        )
        return image

    def configure_ctk_label(
        self,
        parent: Any,
        text: str,
        font: Optional[CTkFont] = None,
        pady: int = 5,
    ) -> CTkLabel:
        """Configure a CTkLabel with the given parameters.

        Args:
            parent: The parent widget.
            text: The label text.
            font: Optional custom font.
            pady: Vertical padding.

        Returns:
            CTkLabel: The created label.
        """
        # Only set font if explicitly passed
        if font is not None:
            label = CTkLabel(
                parent, text=text, font=font, text_color="white", anchor="w",
                justify="left"
            )
        else:
            label = CTkLabel(
                parent, text=text, text_color="white", anchor="w", justify="left"
            )
        label.pack(pady=pady, anchor="w", padx=10)
        return label
