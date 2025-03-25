
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
        
        # Add variables for debouncing and dynamic column tracking
        self.current_cols = None
        self.resize_job = None

        self.setup_gui()

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
        self.main_frame = main_frame  # Store a reference to the main frame

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
        
        # Bind the window resize event (with debouncing)
        self.root.bind("<Configure>", self.on_window_resize)

        # Set up the control frame with buttons
        control_frame = CTkFrame(main_frame)
        control_frame.pack(pady=10)

        refresh_button = CTkButton(control_frame, text="Refresh", command=lambda: self.refresh_upcoming())
        refresh_button.grid(row=0, column=0, padx=5)
        Tooltip(refresh_button, text="Refresh the list of upcoming episodes")

        add_show_button = CTkButton(control_frame, text="Add Show", command=lambda: self.toggle_add_show_panel())
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

        # Add hamburger menu button (moved to top left)
        settings_button = CTkButton(
            self.root, 
            text="⚙️", 
            command=self.toggle_settings_panel, 
            fg_color="gray",
            text_color="white", 
            font=("Arial Unicode MS", 15), 
            width=50, 
            height=30
        )
        settings_button.place(relx=0.0, rely=0.0, anchor="nw", x=10, y=10) 
        Tooltip(settings_button, text="Toggle settings panel")

        # Create settings panel (initially hidden)
        self.create_settings_panel()
        self.create_add_show_panel()

        # Load initial data and create show boxes
        self.refresh_upcoming()


    def toggle_settings_panel(self):
        """Toggle the settings panel open/closed state."""
        if self.is_settings_open:
            self.close_settings_panel()
        else:
            self.open_settings_panel()

    def open_settings_panel(self):
        """Open the settings panel by sliding it in from the right as an overlay."""
        if not self.is_settings_open:
            # Determine the panel size (half of the window width)
            window_width = self.root.winfo_width()
            panel_width = window_width // 2
            
            # Position the panel
            self.settings_panel.configure(width=panel_width)
            self.settings_panel.place(
                relx=0.0,  # Right edge of window
                rely=0.0,  # Top of window
                relwidth=0.5,  # Half the width of window
                relheight=1.0,  # Full height
                anchor="nw"  # Anchor to northeast (top-right)
            )
            
            # Make panel visible
            self.settings_panel.lift()  # Bring to front
            self.is_settings_open = True
            
            # Bind a click event to the root window to detect clicks outside the panel
            self.root.bind("<Button-1>", self.check_outside_click)

    def close_settings_panel(self):
        """Close the settings panel by removing it."""
        if self.is_settings_open:
            self.settings_panel.place_forget()
            self.is_settings_open = False
            
            # Unbind the click event when the panel is closed
            self.root.unbind("<Button-1>")

    def create_settings_panel(self):
        """Create the settings panel that will overlay the main content."""
        # Create the settings panel as a floating frame
        self.settings_panel = CTkFrame(
            self.root,
            fg_color="#1A1A1A",
            corner_radius=10,
            border_width=1,
            border_color="#333333"
        )
        
        # Initialize panel state
        self.is_settings_open = False
        
        # Set up the settings panel content
        self.setup_settings_panel()

    def setup_settings_panel(self):
        """Set up the settings panel content with tabs."""
        # Create a close button at the top right
        close_button = CTkButton(
            self.settings_panel,
            text="⬅️⚙️",
            command=self.close_settings_panel,
            text_color="white",
            font=("Arial", 14),
            width=30,
            height=30,
            fg_color="#1A1A1A",
            hover_color="#333333"
        )
        close_button.place(relx=1.0, rely=0.0, anchor="ne", x=-10, y=10)
        
        # Settings title
        settings_title = CTkLabel(
            self.settings_panel,
            text="Settings",
            font=("Helvetica", 16, "bold"),
            text_color="white"
        )
        settings_title.pack(pady=(20, 15), padx=10)
        
        # Create tabview for settings categories
        self.settings_tabview = CTkTabview(
            self.settings_panel,
            fg_color="#1A1A1A",
            segmented_button_fg_color="gray25",
            segmented_button_selected_color="#3E3E3E",
            segmented_button_unselected_color="gray25",
            text_color="white"
        )
        self.settings_tabview.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Add tabs to the tabview
        self.settings_tabview.add("General")
        self.settings_tabview.add("qBittorrent")
        self.settings_tabview.add("Appearance")
        self.settings_tabview.set("General")  # Default to general tab
        
        # Configure each tab
        self.setup_general_tab()
        self.setup_qbittorrent_tab()
        self.setup_appearance_tab()

    def toggle_add_show_panel(self):
        """Toggle the settings panel open/closed state."""
        if self.is_add_show_open:
            self.close_add_show_panel()
        else:
            self.open_add_show_panel()

    def open_add_show_panel(self):
        """Open the add_show panel by sliding it in from the left as an overlay."""
        if not self.is_add_show_open:
            # Determine the panel size (half of the window width)
            window_width = self.root.winfo_width()
            panel_width = window_width // 2
            
            # Position the panel at the top of the window
            self.add_show_panel.configure(width=panel_width)
            self.add_show_panel.place(
                relx=0.0,      # Left edge of window
                rely=0.0,      # Top of window
                relwidth=0.5,  # Half the width of window
                relheight=1.0, # Full height
                anchor="nw"    # Anchor to northwest (top-left)
            )
            
            # Make panel visible and ensure it's on top
            self.add_show_panel.lift()  # Bring to front
            self.is_add_show_open = True
            
            # Bind a click event to the root window to detect clicks outside the panel
            self.root.bind("<Button-1>", lambda event: self.check_outside_click(event, widget="add_show"))


    def close_add_show_panel(self):
        """Close the add_show panel by removing it."""
        if self.is_add_show_open:
            self.add_show_panel.place_forget()
            self.is_add_show_open = False
            
            # Unbind the click event when the panel is closed
            self.root.unbind("<Button-1>")

    def create_add_show_panel(self):
        """Create the add_show panel that will overlay the main content."""
        # Create the add_show panel as a floating frame
        self.add_show_panel = CTkFrame(
            self.root,
            fg_color="#1A1A1A",
            corner_radius=10,
            border_width=1,
            border_color="#333333"
        )
        
        # Initialize panel state
        self.is_add_show_open = False
        
        # Set up the add_show panel content
        self.setup_add_show_panel()

    def update_autocomplete_panel(self, event, entry, method_var, autocomplete_listbox, autocomplete_frame):
        """
        Enhanced autocomplete method that properly positions and displays the autocomplete listbox.
        
        This method performs the following:
        1. Checks if autocomplete should be active (name method selected and text entered)
        2. Fetches and displays matching suggestions
        3. Properly positions the listbox below the entry field
        4. Ensures the listbox is sized appropriately
        """
        # Hide autocomplete when not in "name" mode
        if method_var.get() != "name":
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
                # Clear and populate the listbox
                autocomplete_listbox.delete(0, tk.END)
                for suggestion in suggestions:
                    autocomplete_listbox.insert(tk.END, suggestion)
                    
                # Display the listbox
                autocomplete_listbox.pack(fill=tk.X, expand=True)
                autocomplete_listbox.configure(width=entry.winfo_width())
                
                # Ensure the listbox is visible and in the right position
                autocomplete_frame.lift()
                
                # Adjust height based on item count but with a maximum
                item_count = min(len(suggestions), 7)  # Show up to 7 items
                autocomplete_listbox.configure(height=item_count)
            else:
                autocomplete_listbox.pack_forget()
        except Exception as e:
            # If any error occurs, hide the autocomplete
            autocomplete_listbox.pack_forget()

    def update_autocomplete_visibility(self, entry, method_var, autocomplete_listbox):
        """
        Update the visibility of the autocomplete listbox based on radio button selection.
        Hide autocomplete when IMDb ID is selected.
        """
        if method_var.get() != "name":
            autocomplete_listbox.pack_forget()
        else:
            # Re-trigger autocomplete if there's text and name method is selected
            typed = entry.get().strip()
            if typed:
                self.update_autocomplete(None, entry, method_var, autocomplete_listbox)

    def setup_add_show_panel(self):
        """Set up the add_show panel content with a better layout."""
        # Create a close button at the top right
        close_button = CTkButton(
            self.add_show_panel,
            text="⬅️📺",
            command=self.close_add_show_panel,
            text_color="white",
            font=("Arial", 14),
            width=30,
            height=30,
            fg_color="#1A1A1A",
            hover_color="#333333"
        )
        close_button.place(relx=1.0, rely=0.0, anchor="ne", x=-10, y=10)
        
        # Main content frame to organize the panel elements
        content_frame = CTkFrame(self.add_show_panel, fg_color="transparent")
        content_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(50, 20))
        
        # Add show title at the top of the content
        add_show_title = CTkLabel(
            content_frame,
            text="Add Show to Watchlist",
            font=("Helvetica", 16, "bold"),
            text_color="white"
        )
        add_show_title.pack(pady=(0, 20))

        # Radio button selection: by name or IMDb ID
        method_var = tk.StringVar(value="name")
        rb_frame = CTkFrame(content_frame, fg_color="#1A1A1A")
        rb_frame.pack(pady=5, fill=tk.X)
        
        method_label = CTkLabel(rb_frame, text="Select method:", text_color="white")
        method_label.pack(side=tk.LEFT, padx=(0, 10))
        
        # Radio buttons with consistent styling
        rb_name = CTkRadioButton(
            rb_frame,
            text="Name",
            variable=method_var,
            value="name",
            command=lambda: self.update_autocomplete_visibility(entry, method_var, autocomplete_listbox),
            text_color="white",
            fg_color="#3E3E3E",
            hover_color="#555555"
        )
        rb_name.pack(side=tk.LEFT, padx=10)
        
        rb_imdb = CTkRadioButton(
            rb_frame,
            text="IMDb ID",
            variable=method_var,
            value="imdb",
            command=lambda: self.update_autocomplete_visibility(entry, method_var, autocomplete_listbox),
            text_color="white",
            fg_color="#3E3E3E",
            hover_color="#555555"
        )
        rb_imdb.pack(side=tk.LEFT, padx=10)

        # Input section
        input_frame = CTkFrame(content_frame, fg_color="transparent")
        input_frame.pack(fill=tk.X, pady=15)
        
        input_label = CTkLabel(
            input_frame, 
            text="Enter Show Name or IMDb ID:", 
            text_color="white"
        )
        input_label.pack(anchor="w", pady=(0, 5))
        
        entry = CTkEntry(
            input_frame,
            width=40,
            fg_color="#333333",
            text_color="white",
            border_color="#555555"
        )
        entry.pack(fill=tk.X)
        entry.focus_set()  # Set focus to the entry widget

        # Create a dedicated frame for the autocomplete listbox
        autocomplete_frame = CTkFrame(content_frame, fg_color="transparent")
        autocomplete_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Create the autocomplete listbox with improved styling
        autocomplete_listbox = tk.Listbox(
            autocomplete_frame, 
            fg="white", 
            bg="#333333", 
            height=7,
            width=40,  # Set a proper width
            selectbackground="#555555",
            selectforeground="white",
            font=("Helvetica", 11)  # Set a proper font
        )
        # Do not pack the listbox initially - it will be displayed when needed

        # Result message label
        result_label = CTkLabel(
            content_frame, 
            text="", 
            fg_color="transparent", 
            text_color="red",
            height=20  # Fixed height to prevent layout shifts
        )
        result_label.pack(pady=5, fill=tk.X)

        # Button section at the bottom
        button_frame = CTkFrame(content_frame, fg_color="transparent")
        button_frame.pack(pady=15)
        
        # Define helper functions for the buttons
        def open_imdb_from_add():
            user_input = entry.get().strip()
            if not user_input:
                result_label.configure(text="Enter a show name or IMDb ID first.")
                return
            if (method_var.get() == "name"):
                info = self.api_client.get_next_episode(user_input)
                imdb_id = info.get("imdb")
                cache_file = self.cache_manager.get_cache_file_path(user_input)
            else:
                imdb_id = user_input
                cache_file = None
            if imdb_id:
                url = "https://www.imdb.com/title/" + imdb_id
                webbrowser.open(url)
                if cache_file and os.path.exists(cache_file) and user_input not in self.watchlist_manager.watchlist:
                    os.remove(cache_file)
            else:
                result_label.configure(text="IMDb page not available for the given input.")

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
                    self.close_add_show_panel()
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
                self.close_add_show_panel()
        
        # Styled buttons with consistent coloring
        add_button = CTkButton(
            button_frame,
            text="Add Show",
            command=validate_and_add,
            text_color="white",
            width=120
        )
        add_button.pack(side=tk.LEFT, padx=5)
        
        imdb_button = CTkButton(
            button_frame,
            text="Open IMDb Page",
            command=open_imdb_from_add,
            text_color="white",
            width=120
        )
        imdb_button.pack(side=tk.LEFT, padx=5)
        
        # Create a new method to update autocomplete with better positioning
        def update_autocomplete_handler(event):
            self.update_autocomplete_panel(event, entry, method_var, autocomplete_listbox, autocomplete_frame)
        
        # Bind event handlers
        entry.bind("<KeyRelease>", update_autocomplete_handler)
        autocomplete_listbox.bind("<<ListboxSelect>>", lambda event: self.on_listbox_select(
            event, entry, autocomplete_listbox))
        
        # Bind click event to close autocomplete listbox
        self.add_show_panel.bind("<Button-1>", lambda event: self.close_autocomplete(
            event, autocomplete_listbox))

    def setup_general_tab(self):
        """Set up the general settings tab."""
        tab = self.settings_tabview.tab("General")
        
        # Monitor clipboard setting
        clipboard_var = tk.BooleanVar(value=self.monitor_clipboard_enabled)
        clipboard_check = CTkCheckBox(
            tab,
            text="Monitor clipboard for magnet links",
            variable=clipboard_var,
            onvalue=True,
            offvalue=False,
            text_color="white",
            command=lambda: self.update_setting("monitor_clipboard_enabled", clipboard_var.get())
        )
        clipboard_check.pack(anchor="w", padx=10, pady=10)
        
        # Quality settings
        quality_frame = CTkFrame(tab, fg_color="transparent")
        quality_frame.pack(fill=tk.X, padx=10, pady=10)
        
        quality_enable_var = tk.BooleanVar(value=self.quality_setting_enabled)
        quality_check = CTkCheckBox(
            quality_frame,
            text="Enable quality filter for searches",
            variable=quality_enable_var,
            onvalue=True,
            offvalue=False,
            text_color="white",
            command=lambda: self.update_setting("quality_setting_enabled", quality_enable_var.get())
        )
        quality_check.pack(anchor="w")
        
        quality_label = CTkLabel(quality_frame, text="Preferred quality:", text_color="white")
        quality_label.pack(anchor="w", pady=(10, 0))
        
        quality_options = ["720p", "1080p", "2160p", "4K"]
        quality_var = StringVar(value=self.video_quality)
        quality_dropdown = CTkComboBox(
            quality_frame,
            width=200,
            values=quality_options,
            variable=quality_var,
            state="readonly",
            fg_color="gray25",
            button_color="gray25",
            button_hover_color="gray35",
            text_color="white",
            dropdown_fg_color="gray25",
            dropdown_hover_color="gray35",
            dropdown_text_color="white",
            command=lambda value: self.update_setting("video_quality", value)
        )
        quality_dropdown.pack(pady=(0, 10), padx=10)

    def setup_qbittorrent_tab(self):
        """Set up the qBittorrent settings tab."""
        tab = self.settings_tabview.tab("qBittorrent")
        
        # qBittorrent settings (URL and check connection)
        self.configure_ctk_label(tab, "qBittorrent Web URL:", pady=(10, 0))
        qbittorrent_url_entry = CTkEntry(tab, width=40, fg_color="gray25", text_color="white")
        qbittorrent_url_entry.insert(0, self.qbittorrent_url)
        qbittorrent_url_entry.pack(pady=(0, 10), padx=10, fill=tk.X)
        qbittorrent_url_entry.bind(
            "<FocusOut>",
            lambda event: self.save_qbittorrent_url(qbittorrent_url_entry.get().strip())
        )

        # Create a frame for the connection buttons
        connection_buttons_frame = CTkFrame(tab, fg_color="transparent")
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

        login_frame = CTkFrame(tab, fg_color="transparent")
        login_frame.pack(pady=10)

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
        self.configure_ctk_label(tab, "Series Directory:", pady=(10, 0))
        series_directory_entry = CTkEntry(tab, width=40, fg_color="gray25", text_color="white")
        series_directory_entry.insert(0, self.api_client.series_directory)
        series_directory_entry.pack(pady=(0, 10), padx=10, fill=tk.X)
        series_directory_entry.bind(
            "<FocusOut>",
            lambda event: self.save_series_directory(series_directory_entry.get().strip())
        )

        # Movies Directory entry
        self.configure_ctk_label(tab, "Movies Directory:", pady=(10, 0))
        movies_directory_entry = CTkEntry(tab, width=40, fg_color="gray25", text_color="white")
        movies_directory_entry.insert(0, self.api_client.movies_directory)
        movies_directory_entry.pack(pady=(0, 10), padx=10, fill=tk.X)
        movies_directory_entry.bind(
            "<FocusOut>",
            lambda event: self.save_movies_directory(movies_directory_entry.get().strip())
        )

    def setup_appearance_tab(self):
        """Set up the appearance settings tab."""
        tab = self.settings_tabview.tab("Appearance")
        
        # Theme selection
        theme_label = CTkLabel(tab, text="Color Theme:", text_color="white")
        theme_label.pack(anchor="w", padx=10, pady=(10, 0))
        
        theme_frame = CTkFrame(tab, fg_color="transparent")
        theme_frame.pack(fill=tk.X, padx=10, pady=10)
        
        theme_var = StringVar(value=self.color_theme)
        themes = ["blue", "dark-blue", "green"]
        
        for i, theme in enumerate(themes):
            theme_radio = CTkRadioButton(
                theme_frame,
                text=theme.capitalize(),
                variable=theme_var,
                value=theme,
                text_color="white",
                command=lambda t=theme: self.update_theme(t)
            )
            theme_radio.pack(anchor="w", pady=5)

    def update_setting(self, setting_name, value):
        """Update a setting and save it to the cache."""
        setattr(self, setting_name, value)
        self.cache_manager.save_setting(setting_name, value)
        
        # Special handling for quality filter checkbox
        if setting_name == "quality_setting_enabled":
            # If we're in the settings panel and the quality dropdown exists
            if hasattr(self, 'settings_tabview') and self.is_settings_open:
                # Find the quality dropdown in the General tab
                general_tab = self.settings_tabview.tab("General")
                for frame in general_tab.winfo_children():
                    if isinstance(frame, CTkFrame):
                        for widget in frame.winfo_children():
                            if isinstance(widget, CTkComboBox):
                                # Enable/disable the quality dropdown based on checkbox state
                                widget.configure(state="normal" if value else "disabled")
                                break

    def create_show_boxes(self):
        """Create boxes for all shows in the show_data list with a dynamic number of columns."""
        # Clear existing boxes
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        
        self.boxes = {}  # Reset boxes dictionary
        
        # Compute dynamic column count based on the current width of the scrollable frame
        available_width = self.scrollable_frame.winfo_width()
        box_width = 250  # width of each box in pixels
        pad = 10         # horizontal padding (sum of left and right)
        
        # Default to 3 columns if width is not yet available (initial load)
        if available_width <= 10:  # Very small width means the widget isn't fully rendered yet
            dynamic_cols = 3
        else:
            dynamic_cols = max(1, available_width // (box_width + pad))
        
        self.current_cols = dynamic_cols  # Update current column count
        
        # Create boxes for each show using the dynamic column count
        for index, show_info in enumerate(self.show_data):
            row = index // dynamic_cols
            col = index % dynamic_cols
            self.create_show_box(show_info, row, col)
    
    def create_show_box(self, show_info, row, col):
        """Create a box for a single show in the scrollable frame placed at the specified row and column."""
        # Create box frame with preset dimensions and style
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
        """Refresh the box with the next episode info for each show in the watchlist."""
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

    def search_and_open_url(self, show_name, episode=None, base_url="https://ext.to/browse/?q=",quality=True):
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
            self.search_and_open_url(show_name, quality=False, base_url="https://www.ktuvit.me/Search.aspx?q=")
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
    
    def on_window_resize(self, event=None):
        """Debounce window resize events so as not to recreate boxes too frequently."""
        # Only respond to actual size changes of the main window
        if event and event.widget == self.root:
            if self.resize_job:
                self.root.after_cancel(self.resize_job)
            # Delay the relayout to avoid rapid multiple calls during resizing (250ms debounce)
            self.resize_job = self.root.after(250, self.relayout)
    
    def relayout(self):
        """Recompute the dynamic columns and update the layout only if needed."""
        available_width = self.scrollable_frame.winfo_width()
        box_width = 250  # Must match the box width used in create_show_box
        pad = 10         # Sum of horizontal paddings
        
        # If width is not yet properly rendered, default to 3 columns
        if available_width <= 10:
            dynamic_cols = 3
        else:
            dynamic_cols = max(1, available_width // (box_width + pad))
        
        # Only re-create the boxes if the column count changes
        if self.current_cols != dynamic_cols:
            self.current_cols = dynamic_cols
            # Instead of refreshing data (which may cause flicker), re-layout the existing boxes.
            self.create_show_boxes()
            
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

    def update_theme(self, theme):
        """Update the color theme and apply it."""
        self.color_theme = theme
        self.cache_manager.save_setting("color_theme", theme)
        customtkinter.set_default_color_theme(theme)
        # Show a message that a restart is required for the theme to fully apply
        messagebox.showinfo("Theme Changed", "Please restart the application for the theme change to fully take effect.")

    def clear_qbittorrent_credentials(self):
        """Clear saved qBittorrent credentials."""
        self.cache_manager.clear_credentials()
        messagebox.showinfo("Credentials Cleared", "qBittorrent credentials have been cleared.")
            
    def check_outside_click(self, event, widget="settings"):
        """Check if a click occurred outside the settings panel."""
        if widget == "add_show":
            widget_open = self.is_add_show_open
            widget_panel = self.add_show_panel
            widget_close = self.close_add_show_panel
        elif widget == "settings":
            widget_open = self.is_settings_open
            widget_panel = self.settings_panel
            widget_close = self.close_settings_panel
        else:
            return

        if widget_open:
            # Get panel coordinates
            panel_x = widget_panel.winfo_rootx()
            panel_y = widget_panel.winfo_rooty()
            panel_width = widget_panel.winfo_width()
            panel_height = widget_panel.winfo_height()
            
            # Check if click is outside the panel boundaries
            if (event.x_root < panel_x or 
                event.x_root > panel_x + panel_width or 
                event.y_root < panel_y or 
                event.y_root > panel_y + panel_height):
                
                # Click is outside, close the panel
                widget_close()
