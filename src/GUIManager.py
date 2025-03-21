import tkinter as tk
from tkinter import messagebox, ttk
import customtkinter
from customtkinter import CTkFrame, CTkLabel, CTkButton, CTkEntry, CTkToplevel, CTkRadioButton, CTkCheckBox, CTkTabview, CTkScrollableFrame, CTkComboBox
import webbrowser
import os
import pyperclip
from tkinter import StringVar
import threading

# Implement a custom Tooltip class with delay
class Tooltip:
    def __init__(self, widget, text, delay=500):
        self.widget = widget
        self.text = text
        self.delay = delay
        self.tooltip_window = None
        self.widget.bind("<Enter>", self.schedule_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)
        self.after_id = None

    def schedule_tooltip(self, event=None):
        self.after_id = self.widget.after(self.delay, self.show_tooltip)

    def show_tooltip(self):
        if self.tooltip_window or not self.text:
            return
        x, y, _, _ = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 25
        self.tooltip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(tw, text=self.text, justify=tk.LEFT,
                         background="#ffffff", relief=tk.SOLID, borderwidth=1,
                         font=("Helvetica", "8", "normal"))
        label.pack(ipadx=1)

    def hide_tooltip(self, event=None):
        if self.after_id:
            self.widget.after_cancel(self.after_id)
            self.after_id = None
        tw = self.tooltip_window
        self.tooltip_window = None
        if tw:
            tw.destroy()

class GUIManager:
    def __init__(self, root, cache_manager, watchlist_manager, api_client):
        self.root = root
        self.cache_manager = cache_manager
        self.watchlist_manager = watchlist_manager
        self.api_client = api_client
        self.monitor_clipboard_enabled = self.cache_manager.load_setting("monitor_clipboard_enabled", True)
        self.qbittorrent_url = self.cache_manager.load_setting("qbittorrent_url", "http://192.168.1.113:8080/")
        self.video_quality = self.cache_manager.load_setting("video_quality", "1080p")
        self.quality_setting_enabled = self.cache_manager.load_setting("quality_setting_enabled", True)

        self.color_theme = self.cache_manager.load_setting("color_theme", "blue")
        customtkinter.set_default_color_theme(self.color_theme)
        
        # New properties for box-based UI
        self.selected_box = None  # Currently selected show
        self.boxes = {}  # Dictionary to store references to show boxes by name
        self.show_data = []  # List to store show data

        self.setup_gui()
        self.settings_window = None

        # Initialize last_magnet_url
        self.last_magnet_url = ""

        # Start monitoring the clipboard
        self.monitor_clipboard()

    def setup_gui(self):
        """Set up the main GUI components with box-based UI."""
        self.root.title("Upcoming Releases Viewer")
        self.root.geometry("920x550")

        # Set up the main frame
        main_frame = CTkFrame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Add a title label with larger font
        title_label = CTkLabel(main_frame, text="Upcoming Episode Releases", font=("Helvetica", 16, "bold"))
        title_label.pack(pady=10)

        # Create a scrollable frame for show boxes instead of treeview
        self.scrollable_frame = CTkScrollableFrame(
            main_frame,
            fg_color="transparent",
            corner_radius=10,
            scrollbar_button_color="gray40",
            scrollbar_button_hover_color="gray30",
            scrollbar_fg_color="transparent",  # Make scrollbar background transparent
            orientation="vertical"
        )
        self.scrollable_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Configure the scrollbar to appear only when needed
        self.scrollable_frame._scrollbar.configure(command=self.scrollable_frame._parent_canvas.yview)
        self.scrollable_frame._parent_canvas.configure(
            yscrollcommand=lambda first, last: self.configure_scrollbar(
                self.scrollable_frame._scrollbar, first, last
            )
        )

        # Set up the control frame with buttons
        control_frame = CTkFrame(main_frame)
        control_frame.pack(pady=10)

        refresh_button = CTkButton(control_frame, text="Refresh", command=lambda: self.refresh_upcoming())
        refresh_button.grid(row=0, column=0, padx=5)
        Tooltip(refresh_button, text="Refresh the list of upcoming episodes")

        add_show_button = CTkButton(control_frame, text="Add Show", command=lambda: self.open_add_show_window())
        add_show_button.grid(row=0, column=1, padx=5)
        Tooltip(add_show_button, text="Add a new show to the watchlist")

        remove_show_button = CTkButton(control_frame, text="Remove Show", command=lambda: self.remove_show())
        remove_show_button.grid(row=0, column=2, padx=5)
        Tooltip(remove_show_button, text="Remove the selected show from the watchlist")

        open_imdb_button = CTkButton(control_frame, text="Open IMDb Page", command=lambda: self.open_imdb())
        open_imdb_button.grid(row=0, column=3, padx=5)
        Tooltip(open_imdb_button, text="Open the IMDb page for the selected show")

        open_qbittorrent_button = CTkButton(control_frame, text="Send to qBittorrent", command=lambda: self.send_to_qbittorrent())
        open_qbittorrent_button.grid(row=0, column=4, padx=5)
        Tooltip(open_qbittorrent_button, text="Send the copied magnet link to qBittorrent")

        search_label = CTkLabel(control_frame, text="Search on:", text_color="white")
        search_label.grid(row=1, column=0, padx=5, pady=5)

        search_rutor_button = CTkButton(control_frame, text="Rutor", command=lambda: self.search_selected("rutor"))
        search_rutor_button.grid(row=1, column=1, padx=5)
        Tooltip(search_rutor_button, text="Search for the selected show on Rutor")

        search_ext_button = CTkButton(control_frame, text="EXT", command=lambda: self.search_selected("ext"))
        search_ext_button.grid(row=1, column=2, padx=5)
        Tooltip(search_ext_button, text="Search for the selected show on EXT")

        search_nyaa_button = CTkButton(control_frame, text="Nyaa", command=lambda: self.search_selected("nyaa"))
        search_nyaa_button.grid(row=1, column=3, padx=5)
        Tooltip(search_nyaa_button, text="Search for the selected show on Nyaa")

        search_ktuvit_button = CTkButton(control_frame, text="Ktuvit", command=lambda: self.search_selected("ktuvit"))
        search_ktuvit_button.grid(row=1, column=4, padx=5)
        Tooltip(search_ktuvit_button, text="Search for the selected show on ktuvit")

        # Add settings button with gear icon
        settings_button = CTkButton(self.root, text="⚙️", command=self.open_settings_window, fg_color="gray",text_color="white", font=("Arial Unicode MS", 15), width=50, height=30)
        settings_button.place(relx=1.0, rely=0.0, anchor="ne", x=-10, y=10) 
        Tooltip(settings_button, text="Open the settings window")

        # Load initial data and create show boxes
        self.refresh_upcoming()

    def create_show_boxes(self):
            """Create boxes for all shows in the show_data list."""
            # Clear existing boxes
            for widget in self.scrollable_frame.winfo_children():
                widget.destroy()
            
            self.boxes = {}  # Reset boxes dictionary
            
            # Create boxes for each show
            for index, show_info in enumerate(self.show_data):
                self.create_show_box(show_info, index)
    
    def create_show_box(self, show_info, index):
        """Create a box for a single show in the scrollable frame."""
        # Calculate grid position (3 boxes per row)
        row = index // 3
        col = index % 3
        
        # Create box frame
        box = CTkFrame(
            master=self.scrollable_frame,
            width=250,
            height=180,
            corner_radius=10,
            fg_color="gray25",  # Unselected background
            border_width=2,     # Keep border width constant to avoid shifts
            border_color="gray40"
        )
        box.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")
        
        # Set the cursor once instead of binding to <Enter>
        box.configure(cursor="hand2")
        
        # Store reference to the box
        show_name = show_info["show"]
        self.boxes[show_name] = box
        
        # Bind the entire box to the click event
        box.bind("<Button-1>", lambda event, s=show_info: self.select_box(s))
        
        # Show name header
        label_show = CTkLabel(
            master=box,
            text=f"{show_info['show']}",
            font=("Helvetica", 16, "bold")
        )
        label_show.pack(anchor="w", padx=10, pady=(10, 2))
        label_show.bind("<Button-1>", lambda event, s=show_info: self.select_box(s))
        
        # Episode label
        label_episode = CTkLabel(
            master=box,
            text=f"Episode: {show_info['episode']}",
            font=("Helvetica", 12)
        )
        label_episode.pack(anchor="w", padx=10, pady=2)
        label_episode.bind("<Button-1>", lambda event, s=show_info: self.select_box(s))
        
        # Title label
        label_title = CTkLabel(
            master=box,
            text=f"Title: {show_info['title']}",
            font=("Helvetica", 12)
        )
        label_title.pack(anchor="w", padx=10, pady=2)
        label_title.bind("<Button-1>", lambda event, s=show_info: self.select_box(s))
        
        # Air Date label
        label_date = CTkLabel(
            master=box,
            text=f"Air Date: {show_info['airdate']}",
            font=("Helvetica", 12)
        )
        label_date.pack(anchor="w", padx=10, pady=(2, 10))
        label_date.bind("<Button-1>", lambda event, s=show_info: self.select_box(s))
    
    def select_box(self, show_info):
        """Handle selection of a show box."""
        # Reset previous selection style
        if self.selected_box and self.selected_box["show"] in self.boxes:
            prev_box = self.boxes[self.selected_box["show"]]
            prev_box.configure(fg_color="gray25", border_color="gray40")
        
        # Set new selection
        self.selected_box = show_info
        
        # Update the UI to show the selected box
        if show_info["show"] in self.boxes:
            current_box = self.boxes[show_info["show"]]
            current_box.configure(fg_color="gray35", border_color="#1E90FF")
    
    def remove_specific_show(self, show_name):
        """Remove a specific show by name from the watchlist."""
        self.watchlist_manager.remove_show(show_name)
        
        # If we removed the selected show, clear the selection
        if self.selected_box and self.selected_box["show"] == show_name:
            self.selected_box = None
        
        # Refresh the display
        self.refresh_upcoming()

    def handle_error(self, error_message):
            """Display an error message to the user and copy it to the clipboard."""
            pyperclip.copy(error_message)
            messagebox.showerror("Error", error_message)

    def refresh_upcoming(self):
        """Refresh the table with the next episode info for each show in the watchlist."""
        def fetch_data():
            # Get show data in a background thread
            self.show_data = []
            for show in self.watchlist_manager.watchlist:
                info = self.api_client.get_next_episode(show)
                self.show_data.append(info)
            
            # Update UI on the main thread
            self.root.after(0, self.create_show_boxes)

        threading.Thread(target=fetch_data).start()

    def remove_show(self):
        """Remove the selected show from the watchlist."""
        if not self.selected_box:
            self.handle_error("Please select a show to remove.")
            return
        
        show_to_remove = self.selected_box["show"]
        self.remove_specific_show(show_to_remove)

    def open_imdb(self):
        """Open the IMDb page for the selected show using its IMDb ID."""
        if not self.selected_box:
            self.handle_error("Please select a show from the list.")
            return
            
        show = self.selected_box["show"]
        info = self.api_client.get_next_episode(show)
        imdb_id = info.get("imdb")
        if imdb_id:
            url = "https://www.imdb.com/title/" + imdb_id
            webbrowser.open(url)
        else:
            self.handle_error(f"IMDb page not available for {show}.")
    
    def prompt_qbittorrent_credentials(self, magnet=True):
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
        def submit_credentials(magnet):
            username = username_entry.get().strip()
            password = password_entry.get().strip()
            if username and password:
                self.cache_manager.save_credentials(username, password)
                credentials_win.destroy()
                if magnet == True:
                    self.open_qbittorrent_with_magnet(self.last_magnet_url)  # Pass the magnet_url argument
            else:
                self.handle_error("Please enter both username and password.")

        submit_button = CTkButton(credentials_win, text="Submit",  command=lambda: submit_credentials(magnet), text_color="white")
        submit_button.pack(pady=10)

    def open_qbittorrent_with_magnet(self, magnet_url, from_clipboard=False):
        """Send the magnet URL to the qBittorrent web interface with authentication."""
        try:
            # Check if credentials exist
            if not self.cache_manager.credentials_exist():
                self.prompt_qbittorrent_credentials()
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
                prompt_label = CTkLabel(prompt_win, text="A magnet URL was detected in the clipboard.\nIs this a movie or a series?", text_color="white")
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

    def search_and_open_url(self, show_name, episode=None, base_url="https://ext.to/browse/?q=",quality=None):
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
        
        if self.quality_setting_enabled and quality:
            query += f" {self.video_quality}"
        
        formatted_query = query.replace(" ", "+")
        url = f"{base_url}{formatted_query}"
        webbrowser.open(url)

    def search_selected(self, option):
        """Search for the selected show based on the given option."""
        if not self.selected_box:
            self.handle_error("Please select a show to search.")
            return
            
        show_name = self.selected_box["show"]
        episode = self.selected_box["episode"]
        
        if option == "ext":
            self.search_and_open_url(show_name, episode, base_url="https://ext.to/browse/?q=")
        elif option == "nyaa":
            self.search_and_open_url(show_name, episode, base_url="https://nyaa.si/?q=")
        elif option == "rutor":
            self.search_and_open_url(show_name, base_url="https://rutor.info/search/")
        elif option == "ktuvit":
            self.search_and_open_url(show_name, quality=None, base_url="https://www.ktuvit.me/Search.aspx?q=")
        else:
            self.handle_error("Invalid search option selected.")

    def open_add_show_window(self):
        """
        Open a larger window to add a new show. You can choose between:
        - Adding by show name (with auto-complete suggestions), or
        - Adding by IMDb ID.
        The input is validated before adding to the persistent watchlist.
        """
        add_win = CTkToplevel(self.root)
        add_win.title("Add Show")
        add_win.geometry("450x310")
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
                try:
                    self.watchlist_manager.add_show(user_input)
                    self.refresh_upcoming()
                    add_win.destroy()
                except ValueError as e:
                    result_label.configure(text=str(e))
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
        
        # # Popular shows section (3 buttons per row)
        # self.configure_ctk_label(add_win, "Latest Popular Shows:", font=("Helvetica", 12, "bold"), pady=(0, 0))
        # popular_shows_frame = CTkFrame(add_win, fg_color="black")
        # popular_shows_frame.pack(padx=0, fill=tk.X)
        
        # popular_shows = self.api_client.fetch_latest_shows()  # Ensure you use the latest fetch_latest_shows() function
        # for i, show in enumerate(popular_shows):
        #     row = i // 3
        #     col = i % 3
        #     btn = CTkButton(popular_shows_frame, text=show, text_color="white",
        #                     command=lambda s=show: (entry.delete(0, tk.END), entry.insert(0, s)))
        #     btn.grid(row=row, column=col, padx=2, pady=2)

    def configure_ctk_button(self, parent, text, command, row, column, padx=5, pady=5):
        """Configure a CTkButton with the given parameters."""
        button = CTkButton(parent, text=text, command=command, text_color="white")
        button.grid(row=row, column=column, padx=padx, pady=pady)
        return button

    def configure_ctk_label(self, parent, text, font=None, pady=5):
        """Configure a CTkLabel with the given parameters."""
        label = CTkLabel(parent, text=text, font=font, text_color="white", anchor="w", justify="left")
        label.pack(pady=pady, anchor="w", padx=10)
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
        try:
            selected_value = autocomplete_listbox.get(autocomplete_listbox.curselection())
            entry.delete(0, tk.END)
            entry.insert(0, selected_value)
            autocomplete_listbox.place_forget()
        except tk.TclError:
            pass

    def close_autocomplete(self, event, autocomplete_listbox):
        """Close the autocomplete listbox when clicking anywhere in the add show window."""
        autocomplete_listbox.place_forget()

    def on_settings_window_close(self):
        # Reset the settings_window reference when the window is closed
        if hasattr(self, 'settings_win') and self.settings_win:
            self.settings_win.destroy()  # Close the settings window
            self.settings_win = None  # Reset the reference


    def open_settings_window(self):
        """Open the settings window with a tabbed interface."""
        if hasattr(self, 'settings_win') and self.settings_win and self.settings_win.winfo_exists():
            # If the window already exists, bring it to the foreground
            self.settings_win.lift()
            self.settings_win.focus_force()
        else:
            # Create the settings window
            self.settings_win = CTkToplevel(self.root)
            self.settings_win.title("Settings")
            self.settings_win.geometry("400x400")
            self.settings_win.configure(fg_color="black")
            self.settings_win.protocol("WM_DELETE_WINDOW", self.on_settings_window_close)
            self.settings_win.lift()
            self.settings_win.focus_force()
            self.settings_win.transient(self.root)

            # Create a CTkTabview to organize settings into tabs
            tabview = CTkTabview(self.settings_win, width=380, height=480)
            tabview.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

            # Add tabs for grouping settings
            tabview.add("Monitor")
            tabview.add("qBittorent")
            tabview.add("Quality")
            tabview.add("Appearance")

            # === Monitor Tab ===
            monitor_frame = tabview.tab("Monitor")
            # Clipboard monitoring toggle
            clipboard_monitor_var = tk.BooleanVar(value=self.monitor_clipboard_enabled)
            clipboard_monitor_check = CTkCheckBox(
                master=monitor_frame,
                text="Enable Clipboard Monitoring",
                variable=clipboard_monitor_var,
                command=lambda: self.toggle_clipboard_monitoring(clipboard_monitor_var.get()),
                text_color="white"
            )
            clipboard_monitor_check.pack(pady=10, padx=10, anchor="w")
            clipboard_monitor_var.trace_add(
                "write",
                lambda *args: self.save_setting("monitor_clipboard_enabled", clipboard_monitor_var.get())
            )

            # === qBittorent Tab ===
            qbittorent_frame = tabview.tab("qBittorent")
            # qBittorrent settings (URL and check connection)
            self.configure_ctk_label(qbittorent_frame, "qBittorrent URL:", pady=(10, 0))
            qbittorrent_url_entry = CTkEntry(qbittorent_frame, width=40, fg_color="gray25", text_color="white")
            qbittorrent_url_entry.insert(0, self.qbittorrent_url)
            qbittorrent_url_entry.pack(pady=(0, 10), padx=10, fill=tk.X)
            qbittorrent_url_entry.bind(
                "<FocusOut>",
                lambda event: self.save_qbittorrent_url(qbittorrent_url_entry.get().strip())
            )

            # Create a frame for the connection buttons
            connection_buttons_frame = CTkFrame(qbittorent_frame)
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
                command=lambda: self.open_qbittorrent_site(),
                text_color="white"
            )
            open_site_button.pack(side="left", padx=5)

            login_frame = CTkFrame(qbittorent_frame)
            login_frame.pack(pady=10)  # Add padding as needed

            save_login_button = CTkButton(
                login_frame,
                text="Set Credentials",
                command=lambda: self.prompt_qbittorrent_credentials(magnet=False),
                text_color="white"
            )
            save_login_button.pack(side="left", padx=5)

            delete_login_button = CTkButton(
                login_frame,
                text="Clear Credentials",
                command=lambda: self.delete_login_cache(),
                text_color="white"
            )
            delete_login_button.pack(side="left", padx=5)

            # Series Directory entry
            self.configure_ctk_label(qbittorent_frame, "Series Directory:", pady=(10, 0))
            series_directory_entry = CTkEntry(qbittorent_frame, width=40, fg_color="gray25", text_color="white")
            series_directory_entry.insert(0, self.api_client.series_directory)
            series_directory_entry.pack(pady=(0, 10), padx=10, fill=tk.X)
            series_directory_entry.bind(
                "<FocusOut>",
                lambda event: self.save_series_directory(series_directory_entry.get().strip())
            )

            # Movies Directory entry
            self.configure_ctk_label(qbittorent_frame, "Movies Directory:", pady=(10, 0))
            movies_directory_entry = CTkEntry(qbittorent_frame, width=40, fg_color="gray25", text_color="white")
            movies_directory_entry.insert(0, self.api_client.movies_directory)
            movies_directory_entry.pack(pady=(0, 10), padx=10, fill=tk.X)
            movies_directory_entry.bind(
                "<FocusOut>",
                lambda event: self.save_movies_directory(movies_directory_entry.get().strip())
            )

            # === Quality Tab ===
            quality_frame = tabview.tab("Quality")
            # Enable quality setting toggle
            quality_setting_var = tk.BooleanVar(value=self.quality_setting_enabled)
            quality_setting_check = CTkCheckBox(
                quality_frame,
                text="Enable Quality Setting",
                variable=quality_setting_var,
                text_color="white"
            )
            quality_setting_check.pack(pady=10, padx=10, anchor="w")
            quality_setting_var.trace_add(
                "write",
                lambda *args: self.save_setting("quality_setting_enabled", quality_setting_var.get())
            )

            # Video quality selection using CTkComboBox
            self.configure_ctk_label(quality_frame, "Select Video Quality:", pady=(10, 0))
            quality_options = ["480p", "720p", "1080p", "2160p"]
            quality_combobox = CTkComboBox(
                quality_frame,
                values=quality_options,
                command=lambda choice: self.save_setting("video_quality", choice),
                width=200,
                text_color="white",
                fg_color="gray25",
                dropdown_fg_color="gray25",
                dropdown_text_color="white",
                dropdown_hover_color="gray35"
            )
            quality_combobox.pack(pady=(0, 10), padx=10)
            quality_combobox.set(self.video_quality)

             # === Appearance Tab ===
            appearance_frame = tabview.tab("Appearance")
            
            # Color Theme Settings
            self.configure_ctk_label(appearance_frame, "Color Theme:", pady=(10, 0))
            
            # Create a combobox for color theme selection
            theme_values = ["blue", "green", "dark-blue"]
            theme_combobox = CTkComboBox(
                appearance_frame,
                values=theme_values,
                command=self.change_color_theme,
                width=200,
                text_color="white",
                fg_color="gray25",
                dropdown_fg_color="gray25",
                dropdown_text_color="white",
                dropdown_hover_color="gray35"
            )
            theme_combobox.pack(pady=0)
            theme_combobox.set(self.color_theme)

    def save_qbittorrent_url(self, url):
        """Save the qBittorrent URL setting."""
        self.qbittorrent_url = url
        self.cache_manager.save_setting("qbittorrent_url", self.qbittorrent_url)
        self.api_client.qbittorrent_url = self.qbittorrent_url  # Update the APIClient instance

    def save_series_directory(self, directory):
        """Save the series directory setting."""
        self.api_client.series_directory = directory
        self.cache_manager.save_setting("series_directory", self.api_client.series_directory)

    def save_movies_directory(self, directory):
        """Save the movies directory setting."""
        self.api_client.movies_directory = directory
        self.cache_manager.save_setting("movies_directory", self.api_client.movies_directory)

    def save_setting(self, key, value):
        """Save a generic setting."""
        self.cache_manager.save_setting(key, value)

    def delete_login_cache(self):
        """Delete the qBittorrent credentials from the cache."""
        files_deleted = self.cache_manager.delete_login_cache()
        if files_deleted == True:
            messagebox.showinfo("Login Data Removed", "The qBittorrent login data has been removed.")
        else:
            messagebox.showinfo("No Login Data Found", "No qBittorrent login data was found.")

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

    def toggle_clipboard_monitoring(self, enabled):
        """Toggle clipboard monitoring on or off."""
        self.monitor_clipboard_enabled = enabled
        self.cache_manager.save_setting("monitor_clipboard_enabled", enabled)  # Save setting to cache
        if enabled:
            self.monitor_clipboard()
        else:
            self.root.after_cancel(self.clipboard_monitor_id)

    def monitor_clipboard(self):
        """Monitor the clipboard for magnet links."""
        if hasattr(self, 'monitor_job'):
            self.root.after_cancel(self.monitor_job)
        
        if self.monitor_clipboard_enabled:
            try:
                current_clipboard = pyperclip.paste()
                if current_clipboard.startswith("magnet:") and current_clipboard != self.last_magnet_url:
                    self.last_magnet_url = current_clipboard
                    self.open_qbittorrent_with_magnet(current_clipboard, from_clipboard=True)
            except Exception:
                pass
            
            # Check clipboard every 2 seconds
            self.monitor_job = self.root.after(2000, self.monitor_clipboard)

    def configure_scrollbar(self, scrollbar, first, last):
        """Configure scrollbar to be visible only when needed."""
        scrollbar.set(first, last)
        
        # Show scrollbar only if not viewing the entire content (when the view doesn't represent 100%)
        if float(last) - float(first) < 0.999:
            scrollbar.grid()
        else:
            scrollbar.grid_remove()
            
    def send_to_qbittorrent(self):
        """Send the magnet URL from the clipboard to the qBittorrent web interface with authentication."""
        try:
            magnet_url = pyperclip.paste()
            if not magnet_url.startswith("magnet:"):
                self.handle_error("Clipboard does not contain a valid magnet URL.")
                return
            self.open_qbittorrent_with_magnet(magnet_url)
        except Exception as e:
            self.handle_error(f"Failed to open qBittorrent: {e}")
            
    def open_qbittorrent_site(self):
        """Open the qBittorrent web interface in the default browser."""
        try:
            webbrowser.open(self.qbittorrent_url)
        except Exception as e:
            self.handle_error(f"Failed to open qBittorrent web interface: {e}")

    def change_color_theme(self, theme):
        """Change the color theme and save the setting."""
        self.color_theme = theme
        self.save_setting("color_theme", theme)
        customtkinter.set_default_color_theme(theme)
        messagebox.showinfo("Settings Applied", "Appearance settings have been applied. Some changes may require restarting the application to take full effect.")
