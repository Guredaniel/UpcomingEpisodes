import pyperclip
import tkinter as tk
from tkinter import messagebox
from customtkinter import CTkToplevel, CTkFrame, CTkLabel, CTkTabview, CTkButton, CTkEntry, CTkCheckBox
from pystray import Icon, MenuItem, Menu
from PIL import Image, ImageDraw, ImageFont
import threading
import time
import sys
import winreg
import webbrowser

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
        self.add_to_startup = self.cache_manager.load_setting("add_to_startup", True)

        # Start monitoring the clipboard in a separate thread if enabled
        if self.monitor_clipboard_enabled:
            self.monitor_thread = threading.Thread(target=self.monitor_clipboard, daemon=True)
            self.monitor_thread.start()

        # Start the system tray icon in a separate daemon thread
        self.tray_thread = threading.Thread(target=self.run_tray, daemon=True)
        self.tray_thread.start()

        # Start the Tk event loop to keep the application running
        self.root.mainloop()

    def create_image(self):
        """
        Create an image for the system tray icon.
        """
        size = (64, 64)
        image = Image.new('RGBA', size, (255, 255, 255, 0))  # Transparent background
        draw = ImageDraw.Draw(image)
        
        # Load a font that supports emojis
        try:
            font = ImageFont.truetype("seguiemj.ttf", 48)  # Segoe UI Emoji (Windows)
        except IOError:
            font = ImageFont.load_default()

        # Draw the magnet emoji
        draw.text((10, 10), "🧲", font=font, fill=(255, 255, 255),stroke_width=3,stroke_fill="black")
        return image

    def open_settings_window(self, root):
        """
        Create and display a settings window modeled on the original implementation.
        This window uses a CTkToplevel with a CTkTabview containing two tabs.
        """
        # Create a new top-level window for settings
        settings_win = CTkToplevel(root)
        settings_win.title("MagnetApp - Settings")
        settings_win.geometry("350x350")

        # Main frame for settings
        main_frame = CTkFrame(settings_win, fg_color="#1A1A1A", corner_radius=10, border_width=1, border_color="#333333")
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
        # Don't pack it yet - we'll display it only when needed

        # Add a close button
        self.close_button = CTkButton(main_frame, text="Close", command=settings_win.destroy, width=100)
        self.close_button.pack(pady=10, padx=10)


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
            lambda event: self.save_information(series_directory_entry.get().strip(),"series_directory")
        )

        # Movies Directory entry
        self.configure_ctk_label(directories_tab, "Movies Directory:", pady=(10, 0))
        movies_directory_entry = CTkEntry(directories_tab, width=40, fg_color="gray25", text_color="white")
        movies_directory_entry.insert(0, self.api_client.movies_directory)
        movies_directory_entry.pack(pady=(0, 10), padx=10, fill=tk.X)
        movies_directory_entry.bind(
            "<KeyRelease>",
            lambda event: self.save_information(movies_directory_entry.get().strip(),"movies_directory")
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

    def setup_qbittorrent_tab(self):
        # Setup content for qbittorrent tab
        qbittorrent_tab = self.settings_tabview.tab("qBittorrent")

       # qBittorrent settings (URL and check connection)
        self.configure_ctk_label(qbittorrent_tab, "qBittorrent Web URL:", pady=(10, 0))
        qbittorrent_url_entry = CTkEntry(qbittorrent_tab, width=40, fg_color="gray25", text_color="white")
        qbittorrent_url_entry.insert(0, self.api_client.qbittorrent_url)
        qbittorrent_url_entry.pack(pady=(0, 10), padx=10, fill=tk.X)
        qbittorrent_url_entry.bind(
            "<KeyRelease>",
            lambda event: self.save_information(qbittorrent_url_entry.get().strip(),"qbittorrent_url")
        )

        # Create a frame for the connection buttons
        connection_buttons_frame = CTkFrame(qbittorrent_tab, fg_color="transparent")
        connection_buttons_frame.pack(pady=10)

        # Check Connection button
        check_connection_button = CTkButton(
            connection_buttons_frame,
            text="Check Connection",
            command=lambda: self.check_qbittorrent_connection(check_connection_button),
            text_color="white"
        )
        check_connection_button.pack(side="left", padx=5)

        # Open qBittorrent Site button
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
        if setting_name == "series_directory":
            self.api_client.series_directory = address
        elif setting_name == "movies_directory":
            self.api_client.movies_directory = address
        elif setting_name == "qbittorrent_url":
            self.api_client.qbittorrent_url = address
        else:
            raise ValueError(f"Unknown setting name: {setting_name}")
        
        self.cache_manager.save_setting(setting_name, address)

    def delete_login_cache(self, button):
        """Delete the qBittorrent credentials from the cache."""
        files_deleted = self.cache_manager.delete_login_cache()
        if files_deleted == True:
            button.configure(text="Login Data Removed", fg_color="green", hover_color="darkgreen")
        else:
           button.configure(text="No Login Data Found", fg_color="red", hover_color="darkred")

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
                self.monitor_thread = threading.Thread(target=self.monitor_clipboard, daemon=True)
                self.monitor_thread.start()
            else:
                self.monitor_thread.join()
                self.monitor_thread = None
        elif setting_name == "add_to_startup":
            appName = "MagnetApp"
            regKeyPath = r"Software\Microsoft\Windows\CurrentVersion\Run"
            try:
                regKey = winreg.OpenKey(winreg.HKEY_CURRENT_USER, regKeyPath, 0, winreg.KEY_ALL_ACCESS)
                if value:
                    # Add the executable path to the registry so the app runs on startup
                    executable = sys.executable
                    winreg.SetValueEx(regKey, appName, 0, winreg.REG_SZ, f'"{executable}"')
                else:
                    # Try to remove the registry entry
                    try:
                        winreg.DeleteValue(regKey, appName)
                    except FileNotFoundError:
                        pass
                winreg.CloseKey(regKey)
            except Exception as e:
                print(f"Error updating startup registry entry: {e}")

    def monitor_clipboard(self):
        while True:
            try:
                current_clipboard = pyperclip.paste()
                if current_clipboard.startswith("magnet:") and current_clipboard != self.last_magnet_url:
                    self.last_magnet_url = current_clipboard
                    # Schedule the magnet processing on the main thread
                    self.root.after(0, self.open_qbittorrent_with_magnet, current_clipboard, True)
            except Exception:
                pass
            time.sleep(2)

    def open_qbittorrent_with_magnet(self, magnet_url, from_clipboard=False):
        """Send the magnet URL to the qBittorrent web interface with authentication."""
        try:
            if not magnet_url.startswith("magnet:"):
                return
            # Check if credentials exist
            if not self.cache_manager.credentials_exist():
                self.root.after(0, self.prompt_qbittorrent_credentials)
                return

            # Prompt the user to select whether the content is a movie or a series
            def on_select(option):
                is_series = (option == "Series")
                self.api_client.open_qbittorrent_with_magnet(magnet_url, is_series)
                prompt_win.destroy() 

            prompt_win = CTkToplevel(self.root)
            prompt_win.title("Select Content Type")
            prompt_win.geometry("320x120")
            prompt_win.configure(fg_color="black")

            # Ensure the new window is in the foreground
            prompt_win.lift()
            prompt_win.focus_force()
            prompt_win.transient(self.root)

            if from_clipboard:
                prompt_label = CTkLabel(prompt_win, text=f"A magnet URL was detected in the clipboard.\nIs this a movie or a series?", text_color="white")
            else:
                prompt_label = CTkLabel(prompt_win, text="Is this a movie or a series?", text_color="white")
            prompt_label.pack(pady=10)

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
        """Prompt the user for qBittorrent username and password."""
        credentials_win = CTkToplevel(self.root)
        credentials_win.title("qBittorrent Credentials")
        credentials_win.geometry("300x200")
        credentials_win.configure(fg_color="black")

        # Ensure the new window is in the foreground
        credentials_win.lift()
        credentials_win.focus_force()
        credentials_win.transient(self.root)

        # Username label and entry
        self.configure_ctk_label(credentials_win, "Username:")
        username_entry = CTkEntry(credentials_win, width=40, fg_color="black", text_color="white")
        username_entry.pack(pady=(0, 5), padx=10, fill="x")

        # Password label and entry
        self.configure_ctk_label(credentials_win, "Password:")
        password_entry = CTkEntry(credentials_win, width=40, fg_color="black", text_color="white", show="*")
        password_entry.pack(pady=(0, 5), padx=10, fill="x")

        # Button to submit credentials
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
                    button.configure(text="Saved", fg_color="green", hover_color="darkgreen")
                credentials_win.destroy()
                if magnet:
                    self.open_qbittorrent_with_magnet(self.last_magnet_url)
            else:
                self.handle_error("Please enter both username and password.")

        submit_button = CTkButton(credentials_win, text="Submit", command=lambda: submit_credentials(magnet, button), text_color="white")
        submit_button.pack(pady=10)

    def handle_error(self, error_message):
        """Display an error message to the user and copy it to the clipboard."""
        pyperclip.copy(error_message)
        messagebox.showerror("Error", error_message)

    def on_settings(self, icon, item):
        """
        Callback triggered when the user selects 'Settings' from the tray menu.
        Instead of launching a new thread (which would result in GUI creation off the main thread),
        we schedule the settings window creation on the main thread.
        """
        self.root.after(0, lambda: self.open_settings_window(self.root))

    def on_exit(self, icon, item):
        """
        Callback triggered when the user selects 'Exit' from the tray menu.
        Stops the system tray icon.
        """
        icon.stop()

    def run_tray(self):
        """
        Creates and runs the system tray icon with a Settings and Exit menu.
        """
        # Use lambda to bind self to the callback
        icon = Icon("TV_Tray", self.create_image(), menu=Menu(
            MenuItem('Open qBittorrent', lambda icon, item: self.api_client.open_qbittorrent_web()),
            MenuItem('Send magnet', lambda icon, item: self.open_qbittorrent_with_magnet(pyperclip.paste(),from_clipboard=False)),
            MenuItem('Settings', lambda icon, item: self.on_settings(icon, item)),
            MenuItem('Exit', lambda icon, item: self.on_exit(icon, item))
        ))
        icon.run()

    def configure_ctk_label(self, parent, text, font=None, pady=5):
        """Configure a CTkLabel with the given parameters."""
        label = CTkLabel(parent, text=text, font=font, text_color="white", anchor="w", justify="left")
        label.pack(pady=pady, anchor="w", padx=10)
        return label