import tkinter as tk
from tkinter import messagebox, ttk
from customtkinter import CTkFrame, CTkLabel, CTkButton, CTkEntry, CTkToplevel, CTkRadioButton, CTkCheckBox
import webbrowser
import os
import pyperclip
from tkinter import PhotoImage  # Add this import for the gear icon
from tkinter import StringVar  # Add this import

class GUIManager:
    def __init__(self, root, cache_manager, watchlist_manager, api_client):
        self.root = root
        self.cache_manager = cache_manager
        self.watchlist_manager = watchlist_manager
        self.api_client = api_client
        self.sort_column, self.sort_reverse = self.cache_manager.get_sort_type()
        self.monitor_clipboard_enabled = self.cache_manager.load_setting("monitor_clipboard_enabled", True)  # Load setting from cache
        self.qbittorrent_url = self.cache_manager.load_setting("qbittorrent_url", "http://192.168.1.113:8080/")  # Load setting from cache
        self.video_quality = self.cache_manager.load_setting("video_quality", "1080p")  # Load setting from cache
        self.quality_setting_enabled = self.cache_manager.load_setting("quality_setting_enabled", True)  # Load setting from cache
        self.setup_gui()

    def setup_gui(self):
        """Set up the main GUI components."""
        self.root.title("Upcoming Releases Viewer")
        self.root.geometry("920x450")

        # Set up the main frame
        main_frame = CTkFrame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Add a title label with larger font
        title_label = CTkLabel(main_frame, text="Upcoming Episode Releases", font=("Helvetica", 16, "bold"))
        title_label.pack(pady=10)

        # Set up the treeview with custom styles
        columns = ("Show", "Episode", "Title", "Air Date")
        self.upcoming_tree = ttk.Treeview(main_frame, columns=columns, show="headings")
        for col in columns:
            self.upcoming_tree.heading(col, text=col, command=lambda _col=col: self.sort_upcoming_tree(_col))
            self.upcoming_tree.column(col, width=120 if col != "Title" else 200)
        self.upcoming_tree.pack(fill=tk.BOTH, expand=True)

        # Apply dark theme styles to the treeview
        style = ttk.Style()
        style.theme_use("clam")

        style.configure("Treeview", background="black", foreground="white", fieldbackground="black")
        style.map('Treeview', background=[('selected', 'grey')], foreground=[('selected', 'white')])

        # Set up the control frame with buttons
        control_frame = CTkFrame(main_frame)
        control_frame.pack(pady=10)

        refresh_button = CTkButton(control_frame, text="Refresh", command=lambda: self.refresh_upcoming())
        refresh_button.grid(row=0, column=0, padx=5)

        add_show_button = CTkButton(control_frame, text="Add Show", command=lambda: self.open_add_show_window())
        add_show_button.grid(row=0, column=1, padx=5)

        remove_show_button = CTkButton(control_frame, text="Remove Show", command=lambda: self.remove_show())
        remove_show_button.grid(row=0, column=2, padx=5)

        open_imdb_button = CTkButton(control_frame, text="Open IMDb Page", command=lambda: self.open_imdb())
        open_imdb_button.grid(row=0, column=3, padx=5)

        open_qbittorrent_button = CTkButton(control_frame, text="Send to qBittorrent", command=lambda: self.open_qbittorrent_with_magnet())
        open_qbittorrent_button.grid(row=0, column=4, padx=5)

        search_label = CTkLabel(control_frame, text="Search on:", text_color="white")
        search_label.grid(row=1, column=0, padx=5, pady=5)

        search_rutor_button = CTkButton(control_frame, text="Rutor", command=lambda: self.search_selected("rutor"))
        search_rutor_button.grid(row=1, column=1, padx=5)

        search_ext_button = CTkButton(control_frame, text="EXT", command=lambda: self.search_selected("ext"))
        search_ext_button.grid(row=1, column=2, padx=5)

        search_nyaa_button = CTkButton(control_frame, text="Nyaa", command=lambda: self.search_selected("nyaa"))
        search_nyaa_button.grid(row=1, column=3, padx=5)

        # Add settings button with gear icon
        settings_icon = PhotoImage(file=r"C:\Users\gured\Downloads\211751_gear_icon.png")  # Use raw string for the file path
        settings_icon = settings_icon.subsample(2, 2)  # Make the icon smaller
        settings_button = tk.Button(self.root, image=settings_icon, command=self.open_settings_window, bg="gray")  # Change background color
        settings_button.image = settings_icon  # Keep a reference to avoid garbage collection
        settings_button.place(relx=1.0, rely=0.0, anchor="ne", x=-10, y=10)  # Position the button at the top right

        # Load initial data
        self.refresh_upcoming()

        # Apply initial sort if available
        if self.sort_column:
            self.sort_upcoming_tree(self.sort_column, initial=True)

        # Initialize last_magnet_url
        self.last_magnet_url = ""

        # Start monitoring the clipboard
        self.monitor_clipboard()

    def handle_error(self, error_message):
        """Display an error message to the user and copy it to the clipboard."""
        pyperclip.copy(error_message)
        messagebox.showerror("Error", error_message)

    def refresh_upcoming(self):
        """Refresh the table with the next episode info for each show in the watchlist."""
        for row in self.upcoming_tree.get_children():
            self.upcoming_tree.delete(row)
        for show in self.watchlist_manager.watchlist:
            info = self.api_client.get_next_episode(show)
            self.upcoming_tree.insert("", "end", values=(
                info["show"],
                info["episode"],
                info["title"],
                info["airdate"]
            ))

    def remove_show(self):
        """Remove the selected show from the watchlist and delete its cache file."""
        selected = self.upcoming_tree.selection()
        if not selected:
            self.handle_error("Please select a show to remove.")
            return
        item = self.upcoming_tree.item(selected[0])
        show_to_remove = item["values"][0]
        self.watchlist_manager.remove_show(show_to_remove)
        self.refresh_upcoming()

    def open_imdb(self):
        """Open the IMDb page for the selected show using its IMDb ID."""
        selected = self.upcoming_tree.selection()
        if not selected:
            self.handle_error("Please select a show from the list.")
            return
        show = self.upcoming_tree.item(selected[0])["values"][0]
        info = self.api_client.get_next_episode(show)
        imdb_id = info.get("imdb")
        if imdb_id:
            url = "https://www.imdb.com/title/" + imdb_id
            webbrowser.open(url)
        else:
            self.handle_error(f"IMDb page not available for {show}.")
    
    def prompt_qbittorrent_credentials(self):
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
        username_entry.pack(pady=(0, 5), padx=10, fill=tk.X)

        # Password label and entry
        self.configure_ctk_label(credentials_win, "Password:")
        password_entry = CTkEntry(credentials_win, width=40, fg_color="black", text_color="white", show="*")
        password_entry.pack(pady=(0, 5), padx=10, fill=tk.X)

        # Button to submit credentials
        def submit_credentials():
            username = username_entry.get().strip()
            password = password_entry.get().strip()
            if username and password:
                self.cache_manager.save_credentials(username, password)
                credentials_win.destroy()
                self.open_qbittorrent_with_magnet()
            else:
                self.handle_error("Please enter both username and password.")

        submit_button = CTkButton(credentials_win, text="Submit", command=submit_credentials, text_color="white")
        submit_button.pack(pady=10)

    def open_qbittorrent_with_magnet(self):
        """Send the magnet URL from the clipboard to the qBittorrent web interface with authentication."""
        try:
            magnet_url = pyperclip.paste()
            if not magnet_url.startswith("magnet:"):
                self.handle_error("Clipboard does not contain a valid magnet URL.")
                return
            self.api_client.open_qbittorrent_with_magnet(magnet_url)
        except Exception as e:
            self.handle_error(f"Failed to open qBittorrent: {e}")

    def open_qbittorrent_web(self):
        """Open the qBittorrent web interface."""
        try:
            self.api_client.open_qbittorrent_web()
        except Exception as e:
            self.handle_error(f"Failed to open qBittorrent web interface: {e}")

    def search_and_open_url(self, show_name, episode=None, base_url="https://ext.to/browse/?q="):
        """Search and open URL for the show and previous episode if provided."""
        if episode and episode.startswith("S") and "E" in episode:
            season, ep_num = episode[1:].split("E")
            try:
                prev_ep_num = int(ep_num) - 1
                if prev_ep_num < 1:
                    query = show_name  # No previous episode for episode 1
                else:
                    prev_episode = f"S{int(season):02d}E{prev_ep_num:02d}"
                    query = f"{show_name} {prev_episode}"
            except ValueError:
                query = show_name
        else:
            query = show_name
        
        if self.quality_setting_enabled:
            query += f" {self.video_quality}"
        
        formatted_query = query.replace(" ", "+")
        url = f"{base_url}{formatted_query}"
        webbrowser.open(url)

    def search_selected(self, option):
        """Search for the selected show based on the given option."""
        try:
            selected_item = self.upcoming_tree.selection()[0]
            values = self.upcoming_tree.item(selected_item)["values"]
            show_name = values[0]
            episode = values[1]
            if option == "ext":
                self.search_and_open_url(show_name, episode, base_url="https://ext.to/browse/?q=")
            elif option == "nyaa":
                self.search_and_open_url(show_name, episode, base_url="https://nyaa.si/?q=")
            elif option == "rutor":
                self.search_and_open_url(show_name, base_url="https://rutor.info/search/")
            else:
                self.handle_error("Invalid search option selected.")
        except IndexError:
            self.handle_error("Please select a show to search.")

    def search_and_send_to_qbittorrent(self, site):
        """Search for the selected show and send the magnet link to qBittorrent."""
        try:
            selected_item = self.upcoming_tree.selection()[0]
            values = self.upcoming_tree.item(selected_item)["values"]
            show_name = values[0]
            episode = values[1]
            magnet_link = self.api_client.search_torrent(show_name, episode, site)
            if magnet_link:
                pyperclip.copy(magnet_link)
                self.api_client.open_qbittorrent_with_magnet(magnet_link)
                messagebox.showinfo("Success", "Magnet link copied and sent to qBittorrent.")
            else:
                self.handle_error("Failed to find a magnet link.")
        except IndexError:
            self.handle_error("Please select a show to search.")
        except Exception as e:
            self.handle_error(f"An error occurred: {e}")

    def open_add_show_window(self):
        """
        Open a larger window to add a new show. You can choose between:
        - Adding by show name (with auto-complete suggestions), or
        - Adding by IMDb ID.
        The input is validated before adding to the persistent watchlist.
        """
        add_win = CTkToplevel(self.root)
        add_win.title("Add Show")
        add_win.geometry("550x360")
        add_win.configure(fg_color="black")  # Set background color to black

        # Ensure the new window is in the foreground
        add_win.lift()
        add_win.focus_force()
        add_win.transient(self.root)

        # Radio button selection: by name or IMDb ID.
        method_var = tk.StringVar(value="name")
        rb_frame = CTkFrame(add_win, fg_color="black")
        rb_frame.pack(pady=5, fill=tk.X, padx=10)
        self.configure_ctk_label(rb_frame, "Select method:", pady=0)
        self.configure_radiobutton(rb_frame, "Name", method_var, "name", lambda: autocomplete_listbox.pack_forget())
        self.configure_radiobutton(rb_frame, "IMDb ID", method_var, "imdb", lambda: autocomplete_listbox.pack_forget())

        # Input label and entry.
        self.configure_ctk_label(add_win, "Enter Show Name or IMDb ID:", pady=(0, 0))
        entry = CTkEntry(add_win, width=40, fg_color="black", text_color="white")  # Increased width
        entry.pack(pady=(0, 5), padx=10, fill=tk.X)
        entry.focus_set()  # Set focus to the entry widget

        # Listbox for auto-complete suggestions (initially hidden).
        autocomplete_listbox = tk.Listbox(add_win, fg="white", bg="black", height=10, width=50)

        result_label = CTkLabel(add_win, text="", fg_color="black", text_color="red")
        result_label.pack(pady=0)

        entry.bind("<KeyRelease>", lambda event: self.update_autocomplete(event, entry, method_var, autocomplete_listbox))
        autocomplete_listbox.bind("<<ListboxSelect>>", lambda event: self.on_listbox_select(event, entry, autocomplete_listbox))

        # Bind click event to close autocomplete listbox
        add_win.bind("<Button-1>", lambda event: self.close_autocomplete(event, autocomplete_listbox))

        # --- Button to Open IMDb Page in the Add Show Window ---
        def open_imdb_from_add():
            user_input = entry.get().strip()
            if not user_input:
                result_label.configure(text="Enter a show name or IMDb ID first.")
                return
            if (method_var.get() == "name"):
                info = self.api_client.get_next_episode(user_input)
                imdb_id = info.get("imdb")
                cache_file = self.cache_manager.get_cache_file_path(user_input)  # Get the cache file path
            else:
                imdb_id = user_input
                cache_file = None  # No cache file for IMDb ID search
            if imdb_id:
                url = "https://www.imdb.com/title/" + imdb_id
                webbrowser.open(url)
                if cache_file and os.path.exists(cache_file) and user_input not in self.watchlist_manager.watchlist:
                    os.remove(cache_file)  # Delete the cache file if it exists and the show is not in the watchlist
            else:
                result_label.configure(text="IMDb page not available for the given input.")

        # --- Validate and Add Show ---
        def validate_and_add():
            user_input = entry.get().strip()
            if not user_input:
                result_label.configure(text="Please enter a value.")
                return
            if method_var.get() == "name":
                if user_input in self.watchlist_manager.watchlist:
                    result_label.configure(text=f"'{user_input}' is already in your watchlist.")
                    return
                info = self.api_client.get_next_episode(user_input)
                if info["title"] == "Failed to fetch info":
                    result_label.configure(text=f"Show '{user_input}' not found. Check the name.")
                    return
                new_show = info["show"]
            else:
                data = self.api_client.lookup_show_by_imdb(user_input)
                if data is None:
                    result_label.configure(text=f"Show with IMDb ID '{user_input}' not found.")
                    return
                new_show = data.get("name")
                if new_show in self.watchlist_manager.watchlist:
                    result_label.configure(text=f"'{new_show}' is already in your watchlist.")
                    return
            self.watchlist_manager.add_show(new_show)
            self.refresh_upcoming()
            add_win.destroy()
        
        # Validate and add show (buttons side by side)
        button_frame = CTkFrame(add_win, fg_color="black")
        button_frame.pack(pady=(0, 5))
        
        self.configure_ctk_button(button_frame, "Add Show", validate_and_add, 0, 0)
        self.configure_ctk_button(button_frame, "Open IMDb Page", open_imdb_from_add, 0, 1)
        
        # Popular shows section (3 buttons per row)
        self.configure_ctk_label(add_win, "Latest Popular Shows:", font=("Helvetica", 12, "bold"), pady=(0, 0))
        popular_shows_frame = CTkFrame(add_win, fg_color="black")
        popular_shows_frame.pack(padx=0, fill=tk.X)
        
        popular_shows = self.api_client.fetch_latest_shows()  # Ensure you use the latest fetch_latest_shows() function
        for i, show in enumerate(popular_shows):
            row = i // 3
            col = i % 3
            btn = CTkButton(popular_shows_frame, text=show, text_color="white",
                            command=lambda s=show: (entry.delete(0, tk.END), entry.insert(0, s)))
            btn.grid(row=row, column=col, padx=2, pady=2)

    def configure_ctk_button(self, parent, text, command, row, column, padx=5, pady=5):
        """Configure a CTkButton with the given parameters."""
        button = CTkButton(parent, text=text, command=command, text_color="white")
        button.grid(row=row, column=column, padx=padx, pady=pady)
        return button

    def configure_ctk_label(self, parent, text, font=None, pady=5):
        """Configure a CTkLabel with the given parameters."""
        label = CTkLabel(parent, text=text, font=font, text_color="white")
        label.pack(pady=pady)
        return label

    def configure_radiobutton(self, parent, text, variable, value, command):
        """Configure a CTkRadioButton with the given parameters."""
        rb = CTkRadioButton(parent, text=text, variable=variable, value=value, command=command, text_color="white")
        rb.pack(side=tk.LEFT, padx=5)
        return rb

    def update_autocomplete(self, event, entry, method_var, autocomplete_listbox):
        """Update the autocomplete suggestions based on the user's input."""
        if (method_var.get() != "name"):
            autocomplete_listbox.pack_forget()
            return
        typed = entry.get().strip()
        if not typed:
            autocomplete_listbox.pack_forget()
            return
        try:
            results = self.api_client.search_shows(typed)
            suggestions = []
            for item in results:
                show_name = item.get("show", {}).get("name")
                if show_name and show_name not in suggestions:
                    suggestions.append(show_name)
            if suggestions:
                autocomplete_listbox.delete(0, tk.END)
                for suggestion in suggestions:
                    autocomplete_listbox.insert(tk.END, suggestion)
                autocomplete_listbox.place(x=entry.winfo_x(), y=entry.winfo_y() + entry.winfo_height())
                autocomplete_listbox.lift()
            else:
                autocomplete_listbox.pack_forget()
        except Exception:
            autocomplete_listbox.pack_forget()

    def on_listbox_select(self, event, entry, autocomplete_listbox):
        """Handle the selection of an item from the autocomplete listbox."""
        selected_value = autocomplete_listbox.get(autocomplete_listbox.curselection())
        entry.delete(0, tk.END)
        entry.insert(0, selected_value)
        autocomplete_listbox.place_forget()

    def close_autocomplete(self, event, autocomplete_listbox):
        """Close the autocomplete listbox when clicking anywhere in the add show window."""
        autocomplete_listbox.place_forget()

    def sort_upcoming_tree(self, col, initial=False):
        """Sort the upcoming_tree by the given column."""
        data = [(self.upcoming_tree.set(child, col), child) for child in self.upcoming_tree.get_children('')]
        data.sort(reverse=self.sort_reverse)
        for index, (val, child) in enumerate(data):
            self.upcoming_tree.move(child, '', index)
        if not initial:
            self.sort_reverse = not self.sort_reverse
            self.cache_manager.set_sort_type(col, self.sort_reverse)

    def open_settings_window(self):
        """Open the settings window."""
        settings_win = CTkToplevel(self.root)
        settings_win.title("Settings")
        settings_win.geometry("350x400")  # Adjusted height to accommodate new setting
        settings_win.configure(fg_color="black")

        # Ensure the new window is in the foreground
        settings_win.lift()
        settings_win.focus_force()
        settings_win.transient(self.root)

        # Create a frame for better organization
        settings_frame = CTkFrame(settings_win, fg_color="black")
        settings_frame.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)

        # Clipboard monitoring toggle
        clipboard_monitor_var = tk.BooleanVar(value=self.monitor_clipboard_enabled)
        clipboard_monitor_check = CTkCheckBox(settings_frame, text="Enable Clipboard Monitoring", variable=clipboard_monitor_var, command=lambda: self.toggle_clipboard_monitoring(clipboard_monitor_var.get()), text_color="white")
        clipboard_monitor_check.pack(pady=10, anchor="w")

        # qBittorrent URL entry
        self.configure_ctk_label(settings_frame, "qBittorrent URL:", pady=(10, 0))
        qbittorrent_url_entry = CTkEntry(settings_frame, width=40, fg_color="black", text_color="white")
        qbittorrent_url_entry.insert(0, self.qbittorrent_url)
        qbittorrent_url_entry.pack(pady=(0, 10), padx=10, fill=tk.X)

        # Quality setting toggle
        quality_setting_var = tk.BooleanVar(value=self.quality_setting_enabled)
        quality_setting_check = CTkCheckBox(settings_frame, text="Enable Quality Setting", variable=quality_setting_var, text_color="white")
        quality_setting_check.pack(pady=10, anchor="w")

        # Video quality selection
        self.configure_ctk_label(settings_frame, "Select Video Quality:", pady=(10, 0))
        quality_var = StringVar(value=self.video_quality)
        quality_options = ["480p", "720p", "1080p", "2160p"]
        quality_menu = ttk.OptionMenu(settings_frame, quality_var, self.video_quality, *quality_options)
        quality_menu.pack(pady=(0, 10), padx=10, fill=tk.X)

        # Button to save settings
        def save_settings():
            self.qbittorrent_url = qbittorrent_url_entry.get().strip()
            self.cache_manager.save_setting("qbittorrent_url", self.qbittorrent_url)
            self.quality_setting_enabled = quality_setting_var.get()
            self.cache_manager.save_setting("quality_setting_enabled", self.quality_setting_enabled)
            self.video_quality = quality_var.get()
            self.cache_manager.save_setting("video_quality", self.video_quality)
            settings_win.destroy()

        save_button = CTkButton(settings_frame, text="Save", command=save_settings, text_color="white")
        save_button.pack(pady=20)

        # Add other settings options here as needed

    def toggle_clipboard_monitoring(self, enabled):
        """Toggle clipboard monitoring on or off."""
        self.monitor_clipboard_enabled = enabled
        self.cache_manager.save_setting("monitor_clipboard_enabled", enabled)  # Save setting to cache
        if enabled:
            self.monitor_clipboard()
        else:
            self.root.after_cancel(self.clipboard_monitor_id)

    def monitor_clipboard(self):
        """Monitor the clipboard for magnet URLs and prompt the user to send them to qBittorrent."""
        if not self.monitor_clipboard_enabled:
            return
        try:
            clipboard_content = pyperclip.paste()
            if (clipboard_content.startswith("magnet:") and clipboard_content != self.last_magnet_url):
                self.last_magnet_url = clipboard_content
                if messagebox.askyesno("Magnet URL Detected", "A magnet URL was detected in the clipboard. Do you want to send it to qBittorrent?"):
                    self.open_qbittorrent_with_magnet()
        except Exception as e:
            self.handle_error(f"Failed to monitor clipboard: {e}")
        finally:
            self.clipboard_monitor_id = self.root.after(1000, self.monitor_clipboard)  # Check the clipboard every second