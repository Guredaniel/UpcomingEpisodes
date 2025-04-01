
import pyperclip
import tkinter as tk
from tkinter import messagebox
from customtkinter import CTkToplevel, CTkFrame, CTkLabel, CTkTabview, CTkButton, CTkEntry, CTkCheckBox
from pystray import Icon, MenuItem, Menu
from PIL import Image, ImageDraw, ImageFont
import threading
import sys
import winreg
import webbrowser
from datetime import datetime, timedelta

class GUIManager:
    def __init__(self, root, cache_manager, api_client):
        # Initialize a hidden main window for scheduling tasks
        self.root = root
        self.root.withdraw()

        self.cache_manager = cache_manager
        self.api_client = api_client
        
        # Initialize last_magnet_url and settings loaded from cache
        self.last_magnet_url = ""
        self.monitor_clipboard_enabled = self.cache_manager.load_setting("monitor_clipboard_enabled", True)
        self.add_to_startup = self.cache_manager.load_setting("add_to_startup", False)

        # Initialize termination flag to signal tasks to stop
        self.should_exit = False
        self.prompt_win_geometry = None  # Attribute to store prompt window geometry
        
        # Cached selection for movie/series with timestamp: (option, timestamp)
        # This stores the last selection; if within cache_duration_minutes, selection prompt will be skipped.
        self.cached_selection = None
        # Cache selection duration in hours (default is 1)
        self.cache_duration_minutes = self.cache_manager.load_setting("cache_duration_minutes", 30.0)

        # Preload the settings window at startup
        self.load_settings_window()

        # Start monitoring the clipboard if enabled
        if self.monitor_clipboard_enabled:
            self.start_clipboard_monitor()

        # Start the system tray icon in a separate daemon thread
        self.tray_thread = threading.Thread(target=self.run_tray, daemon=True)
        self.tray_thread.start()

        # Start the Tk event loop to keep the application running
        self.root.mainloop()

    def load_settings_window(self):
        """
        Build the settings window at startup and keep it hidden.
        The window is pre-built so that it can immediately be shown when requested.
        """
        self.settings_window = CTkToplevel(self.root)
        self.settings_window.title("MagnetLinker - Settings")
        self.settings_window.geometry("350x360")
        # Override window close behavior to hide rather than destroy it.
        self.settings_window.protocol("WM_DELETE_WINDOW", self.settings_window.withdraw)
        self.settings_window.resizable(False, False)

        # Main frame for settings
        main_frame = CTkFrame(self.settings_window, fg_color="#1A1A1A", corner_radius=10, border_width=1, border_color="#333333")
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Add a title label
        title_label = CTkLabel(main_frame, text="Settings", font=("Helvetica", 16, "bold"), text_color="white")
        title_label.pack(pady=(10, 0))

        # Create the tabview
        self.settings_tabview = CTkTabview(main_frame, fg_color="#1A1A1A", segmented_button_fg_color="gray25",
                             segmented_button_selected_color="#3E3E3E", segmented_button_unselected_color="gray25",
                             text_color="white")
        self.settings_tabview.pack(fill="both", expand=True, padx=10)

        # Add tabs
        self.settings_tabview.add("General")
        self.settings_tabview.add("qBittorrent")
        self.settings_tabview.add("Directories")
        self.settings_tabview.set("General")  # Show General by default

        self.setup_general_tab()
        self.setup_qbittorrent_tab()
        self.setup_directories_tab()

        # Create error message label above control frame
        self.error_label = CTkLabel(
            main_frame,
            text="",
            text_color="white",
            font=("Helvetica", 12),
            fg_color="#FF5555",  # Red background
            corner_radius=5,
            height=0  # Initially collapsed
        )
        # (Not packed yet; will be shown when needed)

        # Add a close button that hides the window instead of destroying it
        self.close_button = CTkButton(main_frame, text="Close", command=self.settings_window.withdraw, width=100)
        self.close_button.pack(pady=10, padx=10)

        # Hide window initially
        self.settings_window.withdraw()

    def setup_directories_tab(self):
        # Setup content for Directories tab
        directories_tab = self.settings_tabview.tab("Directories")

        # Series Directory entry
        self.configure_ctk_label(directories_tab, "Series Directory:", pady=(10, 0))
        series_directory_entry = CTkEntry(directories_tab, width=40, fg_color="gray25", text_color="white")
        series_directory_entry.insert(0, self.api_client.series_directory)
        series_directory_entry.pack(pady=(0, 10), padx=10, fill=tk.X)
        series_directory_entry.bind(
            "<KeyRelease>",
            lambda event: self.save_information(series_directory_entry.get().strip(), "series_directory")
        )

        # Movies Directory entry
        self.configure_ctk_label(directories_tab, "Movies Directory:", pady=(10, 0))
        movies_directory_entry = CTkEntry(directories_tab, width=40, fg_color="gray25", text_color="white")
        movies_directory_entry.insert(0, self.api_client.movies_directory)
        movies_directory_entry.pack(pady=(0, 10), padx=10, fill=tk.X)
        movies_directory_entry.bind(
            "<KeyRelease>",
            lambda event: self.save_information(movies_directory_entry.get().strip(), "movies_directory")
        )

    def setup_general_tab(self):
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
            command=lambda: self.update_setting("monitor_clipboard_enabled", clipboard_var.get())
        )
        clipboard_check.pack(anchor="w", padx=10, pady=10)

        # Add to Startup check box
        startup_var = tk.BooleanVar(value=self.add_to_startup)
        startup_check = CTkCheckBox(
            general_tab,
            text="Add to startup",
            variable=startup_var,
            onvalue=True,
            offvalue=False,
            text_color="white",
            command=lambda: self.update_setting("add_to_startup", startup_var.get())
        )
        startup_check.pack(anchor="w", padx=10, pady=10)

        # New: Cache selection duration (hours) setting.
        duration_label = CTkLabel(general_tab, text="Cache selection duration (minutes):", text_color="white")
        duration_label.pack(anchor="w", padx=10, pady=(10, 0))
        duration_entry = CTkEntry(general_tab, width=20, fg_color="gray25", text_color="white")
        # Set initial value; convert to string.
        duration_entry.insert(0, str(self.cache_duration_minutes))
        duration_entry.pack(anchor="w", padx=10, pady=(0, 10), fill=tk.X)
        # When entry changes, update the setting.
        duration_entry.bind("<KeyRelease>", lambda event: self.update_cache_duration(duration_entry.get().strip()))

    def setup_qbittorrent_tab(self):
        # Setup content for qbittorrent tab
        qbittorrent_tab = self.settings_tabview.tab("qBittorrent")

        self.configure_ctk_label(qbittorrent_tab, "qBittorrent Web URL:", pady=(10, 0))
        qbittorrent_url_entry = CTkEntry(qbittorrent_tab, width=40, fg_color="gray25", text_color="white")
        qbittorrent_url_entry.insert(0, self.api_client.qbittorrent_url)
        qbittorrent_url_entry.pack(pady=(0, 10), padx=10, fill=tk.X)
        qbittorrent_url_entry.bind(
            "<KeyRelease>",
            lambda event: self.save_information(qbittorrent_url_entry.get().strip(), "qbittorrent_url")
        )

        connection_buttons_frame = CTkFrame(qbittorrent_tab, fg_color="transparent")
        connection_buttons_frame.pack(pady=10)

        check_connection_button = CTkButton(
            connection_buttons_frame,
            text="Check Connection",
            command=lambda: self.check_qbittorrent_connection(check_connection_button),
            text_color="white"
        )
        check_connection_button.pack(side="left", padx=5)

        open_site_button = CTkButton(
            connection_buttons_frame,
            text="Open Web UI",
            command=lambda: webbrowser.open(self.api_client.qbittorrent_url),
            text_color="white"
        )
        open_site_button.pack(side="left", padx=5)

        login_frame = CTkFrame(qbittorrent_tab, fg_color="transparent")
        login_frame.pack(pady=10)

        save_login_button = CTkButton(
            login_frame,
            text="Set Credentials",
            command=lambda: self.prompt_qbittorrent_credentials(magnet=False, button=save_login_button),
            text_color="white"
        )
        save_login_button.pack(side="left", padx=5)

        delete_login_button = CTkButton(
            login_frame,
            text="Clear Credentials",
            command=lambda: self.delete_login_cache(delete_login_button),
            text_color="white"
        )
        delete_login_button.pack(side="left", padx=5)

    def save_information(self, address, setting_name):
        valid_settings = {"series_directory", "movies_directory", "qbittorrent_url"}
    
        if setting_name not in valid_settings:
            raise ValueError(f"Unknown setting name: {setting_name}")
    
        setattr(self.api_client, setting_name, address)
        self.cache_manager.save_setting(setting_name, address)

    def delete_login_cache(self, button):
        """Delete the qBittorrent credentials from the cache."""
        files_deleted = self.cache_manager.delete_login_cache()
        if files_deleted == True:
            button.configure(text="Login Data Removed", fg_color="green", hover_color="darkgreen")
        else:
            button.configure(text="No Login Data Found", fg_color="red", hover_color="darkred")

    def update_cache_duration(self, value):
        try:
            # Convert the entered value to a float (or int)
            new_duration = float(value)
            self.cache_duration_minutes = new_duration
            self.update_setting("cache_duration_minutes", new_duration)
        except ValueError:
            # If conversion fails, do nothing or add error handling if desired.
            pass

    def check_qbittorrent_connection(self, button):
        """Check the connection to the qBittorrent web interface and update the button text."""
        def run_check():
            button.configure(text="Testing...")
            success, message = self.api_client.check_qbittorrent_connection()
            if success:
                button.configure(text="Connection Successful", fg_color="green", hover_color="darkgreen")
            else:
                button.configure(text="Connection Failed", fg_color="red", hover_color="darkred")
        threading.Thread(target=run_check).start()

    def update_setting(self, setting_name, value):
        """Update a setting and save it to the cache."""
        setattr(self, setting_name, value)
        self.cache_manager.save_setting(setting_name, value)
        
        if setting_name == "monitor_clipboard_enabled":
            if value:
                self.start_clipboard_monitor()
            else:
                # When disabling, simply set flag so scheduled checks stop
                self.should_exit = True
        elif setting_name == "add_to_startup":
            appName = "MagnetApp"
            regKeyPath = r"Software\Microsoft\Windows\CurrentVersion\Run"
            try:
                regKey = winreg.OpenKey(winreg.HKEY_CURRENT_USER, regKeyPath, 0, winreg.KEY_ALL_ACCESS)
                if value:
                    executable = sys.executable
                    winreg.SetValueEx(regKey, appName, 0, winreg.REG_SZ, f'"{executable}"')
                else:
                    try:
                        winreg.DeleteValue(regKey, appName)
                    except FileNotFoundError:
                        pass
                winreg.CloseKey(regKey)
            except Exception as e:
                print(f"Error updating startup registry entry: {e}")

    def start_clipboard_monitor(self):
        """Start periodic clipboard monitoring using Tk.after, avoiding a separate thread."""
        # Reset the exit flag in case it was previously enabled
        self.should_exit = False
        self.check_clipboard()
        
    def check_clipboard(self):
        """Check clipboard for new magnet link and schedule next check."""
        if self.should_exit:
            return
        try:
            current_clipboard = pyperclip.paste()
            if current_clipboard.startswith("magnet:") and current_clipboard != self.last_magnet_url:
                self.last_magnet_url = current_clipboard
                # Schedule the UI update on the main thread immediately
                self.root.after(0, self.open_qbittorrent_with_magnet, current_clipboard, True)
        except Exception:
            pass
        # Schedule next clipboard check in 2000ms (2 seconds)
        self.root.after(2000, self.check_clipboard)

    def open_qbittorrent_with_magnet(self, magnet_url, from_clipboard=False):
        """Send the magnet link to the qBittorrent web interface with authentication.
           If a cached selection exists (and is less than the specified duration), it is automatically used.
           Otherwise, the user is prompted to choose between movie or series.
           If the skip checkbox is checked when making a selection, that choice is cached.
        """
        try:
            if not magnet_url.startswith("magnet:"):
                return
            if not self.cache_manager.credentials_exist():
                self.root.after(0, self.prompt_qbittorrent_credentials)
                return

            # Check for a previously cached selection.
            if self.cached_selection is not None:
                cached_option, cached_time = self.cached_selection
                expiration_time = cached_time + timedelta(hours=self.cache_duration_hours)
                if datetime.now() < expiration_time:
                    is_series = (cached_option == "Series")
                    self.api_client.open_qbittorrent_with_magnet(magnet_url, is_series)
                    return
                else:
                    self.cached_selection = None

            def on_select(option):
                # If the skip (remember choice) checkbox is checked, cache this choice.
                if skip_var.get():
                    self.cached_selection = (option, datetime.now())
                else:
                    self.cached_selection = None
                is_series = (option == "Series")
                self.api_client.open_qbittorrent_with_magnet(magnet_url, is_series)
                # Save window geometry before closing for consistent placement.
                geom = prompt_win.winfo_geometry()  # format "320x150+X+Y"
                parts = geom.split('+')
                if len(parts) == 3:
                    self.prompt_win_geometry = f"+{parts[1]}+{parts[2]}"
                prompt_win.destroy() 

            prompt_win = CTkToplevel(self.root)
            prompt_win.title("MagnetLinker - Content Type")
            if self.prompt_win_geometry:
                prompt_win.geometry(f"320x150{self.prompt_win_geometry}")
            else:
                prompt_win.geometry("320x150")
            prompt_win.resizable(False, False)
            prompt_win.configure(fg_color="black")
            prompt_win.lift()
            prompt_win.focus_force()
            prompt_win.transient(self.root)

            if from_clipboard:
                prompt_label = CTkLabel(prompt_win, text="A magnet link was detected in the clipboard.\nIs this a movie or a series?", text_color="white")
            else:
                prompt_label = CTkLabel(prompt_win, text="Is this a movie or a series?", text_color="white")
            prompt_label.pack(pady=10)

            # Add a check box for caching the selected option.
            skip_var = tk.BooleanVar(value=False)
            skip_checkbox = CTkCheckBox(prompt_win, text=f"Remember my choice for {self.cache_duration_minutes} minutes", variable=skip_var, text_color="white")
            skip_checkbox.pack(pady=5)

            button_frame = CTkFrame(prompt_win, fg_color="black")
            button_frame.pack(pady=10)
            movie_button = CTkButton(button_frame, text="Movie", command=lambda: on_select("Movie"), text_color="white")
            movie_button.grid(row=0, column=0, padx=10)
            series_button = CTkButton(button_frame, text="Series", command=lambda: on_select("Series"), text_color="white")
            series_button.grid(row=0, column=1, padx=10)
        except (ConnectionError, TimeoutError) as e:
            self.handle_error(f"Network error: {e}")
        except Exception as e:
            self.handle_error(f"Failed to open qBittorrent: {e}")

    def prompt_qbittorrent_credentials(self, magnet=True, button=False):
        """Prompt the user for qBittorrent username and password credentials."""
        credentials_win = CTkToplevel(self.root)
        credentials_win.title("MagnetLinker - qBittorrent Credentials")
        credentials_win.geometry("300x200")
        credentials_win.configure(fg_color="black")
        credentials_win.lift()
        credentials_win.focus_force()
        credentials_win.transient(self.root)
        credentials_win.resizable(False, False)

        self.configure_ctk_label(credentials_win, "Username:")
        username_entry = CTkEntry(credentials_win, width=40, fg_color="black", text_color="white")
        username_entry.pack(pady=(0, 5), padx=10, fill="x")

        self.configure_ctk_label(credentials_win, "Password:")
        password_entry = CTkEntry(credentials_win, width=40, fg_color="black", text_color="white", show="*")
        password_entry.pack(pady=(0, 5), padx=10, fill="x")

        def submit_credentials(magnet, button):
            username = username_entry.get().strip()
            password = password_entry.get().strip()
            if username and password:
                try:
                    self.cache_manager.save_credentials(username, password)
                except Exception as e:
                    if button:
                        button.configure(text="Failed Saving", fg_color="red", hover_color="darkred")
                        credentials_win.destroy()
                if button:
                    button.configure(text="Credentials Saved", fg_color="green", hover_color="darkgreen")
                credentials_win.destroy()
                if magnet:
                    self.open_qbittorrent_with_magnet(self.last_magnet_url)
            else:
                self.handle_error("Please enter both the username and password.")

        submit_button = CTkButton(credentials_win, text="Submit", command=lambda: submit_credentials(magnet, button), text_color="white")
        submit_button.pack(pady=10)

    def open_qbittorrent_with_torrent_file(self):
        """
        Prompt the user to select a torrent file and then allow them to choose whether the torrent is for a movie or a series.
        Calls the APIClient's open_qbittorrent_with_torrent_file function.
        """
        try:
            import tkinter.filedialog  # Ensure filedialog is available
            # Open file dialog to select a torrent file
            torrent_file_path = tkinter.filedialog.askopenfilename(
                title="MagnetLinker - Select Torrent File",
                filetypes=[("Torrent Files", "*.torrent")]
            )
            if not torrent_file_path:
                return  # user cancelled the selection

            def on_select(option):
                is_series = (option == "Series")
                self.api_client.open_qbittorrent_with_torrent_file(torrent_file_path, is_series)
                prompt_win.destroy()

            # Create a prompt window to choose between Movie and Series
            prompt_win = CTkToplevel(self.root)
            prompt_win.title("MagnetLinker - Content Type")
            prompt_win.geometry("320x120")
            prompt_win.configure(fg_color="black")
            prompt_win.lift()
            prompt_win.focus_force()
            prompt_win.transient(self.root)
            prompt_win.resizable(False, False)

            prompt_label = CTkLabel(prompt_win, text="Is this torrent for a movie or a series?", text_color="white")
            prompt_label.pack(pady=10)

            button_frame = CTkFrame(prompt_win, fg_color="black")
            button_frame.pack(pady=10)
            movie_button = CTkButton(button_frame, text="Movie", command=lambda: on_select("Movie"), text_color="white")
            movie_button.grid(row=0, column=0, padx=10)
            series_button = CTkButton(button_frame, text="Series", command=lambda: on_select("Series"), text_color="white")
            series_button.grid(row=0, column=1, padx=10)
        except Exception as e:
            self.handle_error(f"Failed to open torrent file: {e}")

    def handle_error(self, error_message):
        """Display an error message to the user and copy it to the clipboard."""
        pyperclip.copy(error_message)
        messagebox.showerror("Error", error_message)

    def on_settings(self, icon, item):
        """
        Callback triggered when the user selects 'Settings' from the tray menu.
        Now that the settings window is preloaded, we simply deiconify it.
        """
        self.root.after(0, lambda: self.settings_window.deiconify())

    def on_exit(self, icon, item):
        """
        Callback triggered when the user selects 'Exit' from the tray menu.
        Stops the system tray icon.
        """
        icon.stop()
        # Signal tasks to stop
        self.should_exit = True
        
        # Join tray_thread if it's alive and not the current thread
        if hasattr(self, "tray_thread") and self.tray_thread.is_alive() and threading.current_thread() is not self.tray_thread:
            self.tray_thread.join(timeout=3)
        
        # Stop the Tk main loop and close the application window
        self.root.quit()
        self.root.destroy()

    def reset_selection(self):
        """Reset the cached selection so that the user is prompted again."""
        self.cached_selection = None

    def create_tray_menu(self):
        return Menu(
            MenuItem('Open qBittorrent', lambda icon, item: self.api_client.open_qbittorrent_web()),
            MenuItem('Send magnet link', lambda icon, item: self.open_qbittorrent_with_magnet(pyperclip.paste(), from_clipboard=False)),
            MenuItem('Send torrent file', lambda icon, item: self.open_qbittorrent_with_torrent_file()),
            MenuItem('Reset Selection', lambda icon, item: self.reset_selection()),
            MenuItem('Settings', lambda icon, item: self.on_settings(icon, item)),
            Menu.SEPARATOR,
            MenuItem('Exit', lambda icon, item: self.on_exit(icon, item))
        )

    def run_tray(self):
        icon = Icon("MagnetLinker", self.create_image(), "MagnetLinker", menu=self.create_tray_menu())
        icon.run()

    def create_image(self):
        """
        Create an image for the system tray icon.
        """
        size = (64, 64)
        image = Image.new('RGBA', size, (255, 255, 255, 0))
        draw = ImageDraw.Draw(image)
        try:
            font = ImageFont.truetype("seguiemj.ttf", 47)
        except IOError:
            font = ImageFont.load_default()
        draw.text((0, 11), "🧲", font=font, fill=(255, 255, 255), stroke_width=5, stroke_fill="black")
        return image

    def configure_ctk_label(self, parent, text, font=None, pady=5):
        """Configure a CTkLabel with the given parameters."""
        label = CTkLabel(parent, text=text, font=font, text_color="white", anchor="w", justify="left")
        label.pack(pady=pady, anchor="w", padx=10)
        return label
