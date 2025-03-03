#!/usr/bin/env python3
"""
Spotube: We sync Spotify to YouTube so you don't have to... awkwardly search yourself.
"""

import json
import os
import html
import subprocess
import threading
import time
import io
from itertools import cycle
from typing import Any, Dict, Optional
import argparse
import webbrowser
from pathlib import Path
import urllib.request

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from PIL import Image, ImageTk
import requests
from io import BytesIO

import spotipy
from spotipy.oauth2 import SpotifyOAuth
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Global variables
current_mpv_process = None
DEFAULT_CONFIG_PATH = "config.json"

class ConfigManager:
    """Manages configuration loading, saving, and validation."""
    
    @staticmethod
    def load_config(filename: str = DEFAULT_CONFIG_PATH) -> Dict[str, Any]:
        """Load configuration from a JSON file."""
        try:
            with open(filename, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            default_config = {
                "spotify": {
                    "client_id": "YOUR_SPOTIFY_CLIENT_ID",
                    "client_secret": "YOUR_SPOTIFY_CLIENT_SECRET",
                    "redirect_uri": "http://localhost:8080",
                    "scope": "user-read-playback-state user-modify-playback-state",
                },
                "youtube": {"api_key": "YOUR_YOUTUBE_API_KEY"},
                "app": {
                    "check_interval": 5,
                    "mute_spotify": True,
                    "mpv_fullscreen": False,
                    "mpv_window_width": 1280,
                    "mpv_window_height": 720,
                },
            }
            with open(filename, "w") as f:
                json.dump(default_config, f, indent=4)
            return default_config
        except json.JSONDecodeError:
            messagebox.showerror("Configuration Error", "Invalid JSON in config file.")
            return None
    
    @staticmethod
    def save_config(config: Dict[str, Any], filename: str = DEFAULT_CONFIG_PATH) -> bool:
        """Save configuration to a JSON file."""
        try:
            with open(filename, "w") as f:
                json.dump(config, f, indent=4)
            return True
        except Exception as e:
            messagebox.showerror("Configuration Error", f"Failed to save config: {e}")
            return False
    
    @staticmethod
    def validate_config(config: Dict[str, Any]) -> bool:
        """Validate the configuration."""
        # Check Spotify credentials
        if (config["spotify"]["client_id"] == "YOUR_SPOTIFY_CLIENT_ID" or
            config["spotify"]["client_secret"] == "YOUR_SPOTIFY_CLIENT_SECRET"):
            return False
        
        # Check YouTube API key
        if config["youtube"]["api_key"] == "YOUR_YOUTUBE_API_KEY":
            return False
        
        return True


class SpotifyManager:
    """Manages Spotify API interactions."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.client = None
        self.previous_volume = None
    
    def get_client(self) -> Optional[spotipy.Spotify]:
        """Initialize and return a Spotify client."""
        if self.client is None:
            try:
                self.client = spotipy.Spotify(
                    auth_manager=SpotifyOAuth(
                        client_id=self.config["spotify"]["client_id"],
                        client_secret=self.config["spotify"]["client_secret"],
                        redirect_uri=self.config["spotify"]["redirect_uri"],
                        scope=self.config["spotify"]["scope"],
                        open_browser=True
                    )
                )
            except Exception as e:
                messagebox.showerror("Spotify Error", f"Failed to connect to Spotify: {e}")
                return None
        return self.client
    
    def get_currently_playing(self) -> Optional[Dict[str, Any]]:
        """Fetch the currently playing track on Spotify."""
        sp = self.get_client()
        if not sp:
            return None
        
        try:
            current_playback = sp.current_playback()
            if current_playback is None or not current_playback.get("is_playing", False):
                return None

            # Make sure we have a valid item
            if "item" not in current_playback or current_playback["item"] is None:
                return None

            track = current_playback["item"]
            track_id = track["id"]
            track_name = track["name"]
            artist_name = track["artists"][0]["name"]
            album_name = track["album"]["name"]
            album_art_url = track["album"]["images"][0]["url"] if track["album"]["images"] else None
            progress_ms = current_playback["progress_ms"]
            duration_ms = track["duration_ms"]

            return {
                "track_id": track_id,
                "track_name": track_name,
                "artist_name": artist_name,
                "album_name": album_name,
                "album_art_url": album_art_url,
                "track_query": f"{track_name} {artist_name} official music video",
                "progress_ms": progress_ms,
                "duration_ms": duration_ms,
            }
        except spotipy.exceptions.SpotifyException as e:
            print(f"Spotify API error: {e}")
            return None
        except Exception as e:
            print(f"Failed to get current track: {e}")
            return None
    
    def set_volume(self, volume: int) -> bool:
        """Set the Spotify playback volume."""
        sp = self.get_client()
        if not sp:
            return False
        
        try:
            # Store the previous volume if we're muting
            if volume <= 5 and self.previous_volume is None:
                current = sp.current_playback()
                if current and "device" in current:
                    self.previous_volume = current["device"].get("volume_percent", 100)
            
            sp.volume(volume)
            return True
        except spotipy.exceptions.SpotifyException as e:
            print(f"Volume control failed: {e}")
            return False
    
    def restore_volume(self) -> bool:
        """Restore the previous Spotify volume."""
        if self.previous_volume is not None:
            result = self.set_volume(self.previous_volume)
            if result:
                self.previous_volume = None
            return result
        return True
    
    def skip_to_next_track(self) -> bool:
        """Skip to the next track on Spotify."""
        sp = self.get_client()
        if not sp:
            return False
        
        try:
            sp.next_track()
            return True
        except spotipy.exceptions.SpotifyException as e:
            print(f"Failed to skip to the next track: {e}")
            return False
    
    def skip_to_previous_track(self) -> bool:
        """Skip to the previous track on Spotify."""
        sp = self.get_client()
        if not sp:
            return False
        
        try:
            sp.previous_track()
            return True
        except spotipy.exceptions.SpotifyException as e:
            print(f"Failed to skip to the previous track: {e}")
            return False


class YouTubeManager:
    """Manages YouTube API interactions."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
    
    def search_video(self, query: str) -> Optional[Dict[str, str]]:
        """Search for a YouTube video using the YouTube Data API."""
        try:
            youtube = build(
                "youtube", "v3", developerKey=self.config["youtube"]["api_key"]
            )
            request = youtube.search().list(
                part="snippet", q=query, type="video", maxResults=1
            )
            response = request.execute()
            if "items" not in response or len(response["items"]) == 0:
                return None

            video_id = response["items"][0]["id"]["videoId"]
            video_title = response["items"][0]["snippet"]["title"]
            thumbnail_url = response["items"][0]["snippet"]["thumbnails"]["high"]["url"]
            
            # Decode HTML entities in the video title
            decoded_title = html.unescape(video_title)
            
            return {
                "url": f"https://www.youtube.com/watch?v={video_id}",
                "title": decoded_title,  # Use the decoded title here
                "id": video_id,
                "thumbnail_url": thumbnail_url
            }
        except Exception as e:
            print(f"Error searching for video: {e}")
            return None
        except HttpError as e:
            print(f"YouTube API error: {e}")
            return None
        except Exception as e:
            print(f"Failed to search YouTube: {e}")
            return None


class MPVManager:
    """Manages MPV player interactions."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.current_process = None
    
    def check_installation(self) -> bool:
        """Check if MPV is installed and accessible."""
        try:
            result = subprocess.run(
                ["mpv", "--version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False
            )
            return result.returncode == 0
        except (subprocess.SubprocessError, FileNotFoundError):
            return False
    
    def play_video(self, video_info: Dict[str, str], start_time_ms: int) -> bool:
        """Play a video using MPV."""
        try:
            # Kill any existing MPV instances
            self.kill_processes()

            # Convert start time to seconds
            start_time_seconds = max(0, start_time_ms / 1000)  # Ensure non-negative

            # Create a window title with the video info - sanitize it
            safe_title = video_info["title"].replace('"', "").replace("'", "")
            window_title = f"Spotube: {safe_title}"

            # MPV options from config
            mpv_fullscreen = self.config["app"].get("mpv_fullscreen", False)
            mpv_window_width = self.config["app"].get("mpv_window_width", 1280)
            mpv_window_height = self.config["app"].get("mpv_window_height", 720)

            # Build command with proper quoting
            mpv_cmd = [
                "mpv",
                video_info["url"],
                f"--start={start_time_seconds}",
                "--force-window=yes",
                f"--title={window_title}",
                "--no-terminal",
            ]

            if mpv_fullscreen:
                mpv_cmd.append("--fullscreen")
            else:
                mpv_cmd.extend(
                    [f"--geometry={mpv_window_width}x{mpv_window_height}"]
                )

            self.current_process = subprocess.Popen(
                mpv_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            return True

        except FileNotFoundError:
            return False
        except Exception as e:
            print(f"Failed to play video: {e}")
            return False
    
    def kill_processes(self) -> None:
        """Kill all running MPV processes."""
        try:
            if self.current_process:
                self.current_process.terminate()
                self.current_process = None
                
            if os.name == "nt":  # Windows
                subprocess.run(
                    ["taskkill", "/F", "/IM", "mpv.exe"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False,
                )
            else:  # Unix/Linux/Mac
                subprocess.run(
                    ["pkill", "-9", "mpv"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False,
                )
            time.sleep(0.5)  # Give it time to close
        except Exception as e:
            print(f"Failed to kill MPV processes: {e}")


class SpotubeGUI:
    """Main GUI for the Spotube application."""
    
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Spotube")
        self.root.minsize(600, 500)
        
        # Set theme
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        # Configure colors
        self.bg_color = "#121212"
        self.text_color = "#FFFFFF"
        self.accent_color = "#1DB954"
        self.secondary_color = "#535353"
        
        # Configure styles
        self.style.configure("TFrame", background=self.bg_color)
        self.style.configure("TLabel", background=self.bg_color, foreground=self.text_color)
        self.style.configure("TButton", background=self.accent_color, foreground=self.text_color)
        self.style.configure("Accent.TButton", background=self.accent_color, foreground=self.text_color)
        self.style.configure("Secondary.TButton", background=self.secondary_color, foreground=self.text_color)
        
        # Load configuration
        self.config = ConfigManager.load_config()
        if not self.config:
            self.root.destroy()
            return
        
        # Initialize managers
        self.spotify = SpotifyManager(self.config)
        self.youtube = YouTubeManager(self.config)
        self.mpv = MPVManager(self.config)
        
        # State variables
        self.running = False
        self.monitor_thread = None
        self.current_track = None
        self.current_video = None
        
        # Create UI
        self.create_ui()
        
        # Check MPV installation
        if not self.mpv.check_installation():
            messagebox.showwarning(
                "MPV Not Found", 
                "MPV player is not installed or not in your PATH. "
                "Please install MPV to play videos."
            )
        
        # Check configuration
        if not ConfigManager.validate_config(self.config):
            self.show_config_dialog()
        
    def create_ui(self):
        """Create the user interface."""
        self.root.configure(bg=self.bg_color)
        
        # Main container
        self.main_frame = ttk.Frame(self.root, padding=10)
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Header
        header_frame = ttk.Frame(self.main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Logo (app icon only)
        try:
            # First try local path
            icon_path = Path(__file__).parent / "appicon.png"
            header_height = 60
            aspect_ratio = 450 / 315
            header_width = int(header_height * aspect_ratio)
            
            if icon_path.exists():
                app_icon = Image.open(icon_path)
                app_icon = app_icon.resize((header_width, header_height), Image.LANCZOS)
                app_icon_img = ImageTk.PhotoImage(app_icon)
                icon_label = ttk.Label(header_frame, image=app_icon_img)
                icon_label.image = app_icon_img  # Keep a reference to prevent garbage collection
                icon_label.pack(side=tk.LEFT)
            else:
                # If local file doesn't exist, fetch from GitHub
                github_url = "https://raw.githubusercontent.com/dullmace/spottube/main/appicon.png"
                app_icon_img = self.load_image_from_url(github_url, header_width, header_height)
                
                if app_icon_img:
                    icon_label = ttk.Label(header_frame, image=app_icon_img)
                    icon_label.image = app_icon_img  # Keep a reference to prevent garbage collection
                    icon_label.pack(side=tk.LEFT)
                else:
                    # Fallback to text if image not found
                    title_label = ttk.Label(
                        header_frame, 
                        text="Spotube", 
                        font=("Helvetica", 24, "bold"),
                        foreground=self.accent_color
                    )
                    title_label.pack(side=tk.LEFT)
        except Exception as e:
            print(f"Error loading header icon: {e}")
            # Fallback to text if there's any error
            title_label = ttk.Label(
                header_frame, 
                text="Spotube", 
                font=("Helvetica", 24, "bold"),
                foreground=self.accent_color
            )
            title_label.pack(side=tk.LEFT)

        
        # Status indicator
        self.status_var = tk.StringVar(value="Not Running")
        self.status_indicator = ttk.Label(
            header_frame,
            textvariable=self.status_var,
            foreground=self.secondary_color,
            font=("Helvetica", 12)
        )
        self.status_indicator.pack(side=tk.RIGHT, padx=10)
        
        # Content area - split into two panes
        content_frame = ttk.Frame(self.main_frame)
        content_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Left pane - Track info
        track_frame = ttk.Frame(content_frame, padding=10)
        track_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        ttk.Label(
            track_frame, 
            text="Spotify Track", 
            font=("Helvetica", 14, "bold"),
            foreground=self.accent_color
        ).pack(anchor=tk.W)
        
        # Album art placeholder
        self.album_art_frame = ttk.Frame(track_frame, width=250, height=250)
        self.album_art_frame.pack(pady=10)
        self.album_art_frame.pack_propagate(False)
        
        self.album_art_label = ttk.Label(self.album_art_frame)
        self.album_art_label.pack(fill=tk.BOTH, expand=True)
        
        # Track details
        track_details_frame = ttk.Frame(track_frame)
        track_details_frame.pack(fill=tk.X, pady=5)
        
        self.track_name_var = tk.StringVar(value="No track playing")
        self.artist_name_var = tk.StringVar(value="")
        self.album_name_var = tk.StringVar(value="")
        
        ttk.Label(
            track_details_frame, 
            textvariable=self.track_name_var,
            font=("Helvetica", 12, "bold"),
            wraplength=250
        ).pack(anchor=tk.W)
        
        ttk.Label(
            track_details_frame, 
            textvariable=self.artist_name_var,
            wraplength=250
        ).pack(anchor=tk.W)
        
        ttk.Label(
            track_details_frame, 
            textvariable=self.album_name_var,
            foreground=self.secondary_color,
            wraplength=250
        ).pack(anchor=tk.W)
        
        # Progress bar
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(
            track_frame, 
            variable=self.progress_var,
            mode='determinate',
            length=250
        )
        self.progress_bar.pack(pady=10)
        
        self.time_var = tk.StringVar(value="0:00 / 0:00")
        ttk.Label(
            track_frame,
            textvariable=self.time_var,
            foreground=self.secondary_color
        ).pack()
        
        # Right pane - YouTube info
        video_frame = ttk.Frame(content_frame, padding=10)
        video_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        ttk.Label(
            video_frame, 
            text="YouTube Video", 
            font=("Helvetica", 14, "bold"),
            foreground=self.accent_color
        ).pack(anchor=tk.W)
        
        # Video thumbnail placeholder
        self.video_thumb_frame = ttk.Frame(video_frame, width=250, height=140)
        self.video_thumb_frame.pack(pady=10)
        self.video_thumb_frame.pack_propagate(False)
        
        self.video_thumb_label = ttk.Label(self.video_thumb_frame)
        self.video_thumb_label.pack(fill=tk.BOTH, expand=True)
        
        # Video details
        video_details_frame = ttk.Frame(video_frame)
        video_details_frame.pack(fill=tk.X, pady=5)
        
        self.decoded_title_var = tk.StringVar(value="No video playing")
        
        ttk.Label(
            video_details_frame, 
            textvariable=self.decoded_title_var,
            font=("Helvetica", 12, "bold"),
            wraplength=250
        ).pack(anchor=tk.W)
        
        # Video URL
        self.video_url_var = tk.StringVar(value="")
        self.video_url_link = ttk.Label(
            video_details_frame,
            text="Open in browser",
            foreground=self.accent_color,
            cursor="hand2"
        )
        self.video_url_link.pack(anchor=tk.W, pady=5)
        self.video_url_link.bind("<Button-1>", self.open_video_in_browser)
        
        # Control buttons
        controls_frame = ttk.Frame(self.main_frame)
        controls_frame.pack(fill=tk.X, pady=10)
        
        # Playback controls
        playback_frame = ttk.Frame(controls_frame)
        playback_frame.pack(pady=10)
        
        self.prev_button = ttk.Button(
            playback_frame,
            text="⏮ Previous Track",
            width=16,
            command=self.previous_track
        )
        self.prev_button.pack(side=tk.LEFT, padx=5)
        
        self.next_button = ttk.Button(
            playback_frame,
            text="Next Track ⏭",
            width=16,
            command=self.next_track
        )
        self.next_button.pack(side=tk.LEFT, padx=5)
        
        # App controls
        app_controls_frame = ttk.Frame(controls_frame)
        app_controls_frame.pack(pady=10)
        
        self.start_button = ttk.Button(
            app_controls_frame,
            text="Start Monitoring",
            style="Accent.TButton",
            command=self.start_monitoring
        )
        self.start_button.pack(side=tk.LEFT, padx=5)
        
        self.stop_button = ttk.Button(
            app_controls_frame,
            text="Stop Monitoring",
            style="Secondary.TButton",
            command=self.stop_monitoring
        )
        self.stop_button.pack(side=tk.LEFT, padx=5)
        
        # Settings button
        self.settings_button = ttk.Button(
            app_controls_frame,
            text="Settings",
            command=self.show_config_dialog
        )
        self.settings_button.pack(side=tk.LEFT, padx=5)
        
        # Mute Spotify checkbox
        self.mute_spotify_var = tk.BooleanVar(value=self.config["app"]["mute_spotify"])
        self.mute_spotify_check = ttk.Checkbutton(
            app_controls_frame,
            text="Mute Spotify",
            variable=self.mute_spotify_var
        )
        self.mute_spotify_check.pack(side=tk.LEFT, padx=10)
        
        # Status bar
        status_bar = ttk.Frame(self.root, relief=tk.SUNKEN)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.status_message = tk.StringVar(value="Ready")
        status_label = ttk.Label(
            status_bar, 
            textvariable=self.status_message,
            padding=(5, 2)
        )
        status_label.pack(side=tk.LEFT)
        
        # Update UI state
        self.update_ui_state()
    
    def update_ui_state(self):
        """Update UI elements based on current state."""
        if self.running:
            self.status_var.set("Running")
            self.status_indicator.configure(foreground=self.accent_color)
        else:
            self.status_var.set("Not Running")
            self.status_indicator.configure(foreground=self.secondary_color)
    
    def load_image_from_url(self, url, width, height):
        """Load an image from a URL and resize it."""
        try:
            response = requests.get(url)
            img = Image.open(BytesIO(response.content))
            img = img.resize((width, height), Image.LANCZOS)
            return ImageTk.PhotoImage(img)
        except Exception as e:
            print(f"Failed to load image: {e}")
            return None
        
    def update_track_display(self, track_info):
        """Update the track display with new track information."""
        if not track_info:
            self.track_name_var.set("No track playing")
            self.artist_name_var.set("")
            self.album_name_var.set("")
            self.progress_var.set(0)
            self.time_var.set("0:00 / 0:00")
            self.album_art_label.configure(image="")
            return
        
        self.track_name_var.set(track_info["track_name"])
        self.artist_name_var.set(track_info["artist_name"])
        self.album_name_var.set(track_info["album_name"])
        
        # Update progress
        progress_sec = track_info["progress_ms"] / 1000
        duration_sec = track_info["duration_ms"] / 1000
        progress_pct = (progress_sec / duration_sec) * 100 if duration_sec > 0 else 0
        self.progress_var.set(progress_pct)
        
        # Format time as MM:SS
        progress_str = f"{int(progress_sec // 60)}:{int(progress_sec % 60):02d}"
        duration_str = f"{int(duration_sec // 60)}:{int(duration_sec % 60):02d}"
        self.time_var.set(f"{progress_str} / {duration_str}")
        
        # Load album art
        if track_info.get("album_art_url"):
            img = self.load_image_from_url(track_info["album_art_url"], 250, 250)
            if img:
                self.album_art_label.configure(image=img)
                self.album_art_label.image = img  # Keep a reference
    
    def update_video_display(self, video_info):
        """Update the video display with new video information."""
        if not video_info:
            self.decoded_title_var.set("No video playing")
            self.video_url_var.set("")
            self.video_thumb_label.configure(image="")
            self.video_url_link.pack_forget()
            return
        
        self.decoded_title_var.set(video_info["title"])
        self.video_url_var.set(video_info["url"])
        self.video_url_link.pack(anchor=tk.W, pady=5)
        
        # Load thumbnail
        if video_info.get("thumbnail_url"):
            img = self.load_image_from_url(video_info["thumbnail_url"], 250, 140)
            if img:
                self.video_thumb_label.configure(image=img)
                self.video_thumb_label.image = img  # Keep a reference
    
    def open_video_in_browser(self, event=None):
        """Open the current video URL in a web browser."""
        url = self.video_url_var.get()
        if url:
            webbrowser.open(url)
    
    def start_monitoring(self):
        """Start monitoring Spotify and playing YouTube videos."""
        if self.running:
            return
        
        self.running = True
        self.update_ui_state()
        self.status_message.set("Starting monitoring...")
        
        # Start monitoring in a separate thread
        self.monitor_thread = threading.Thread(target=self.monitor_spotify, daemon=True)
        self.monitor_thread.start()
    
    def stop_monitoring(self):
        """Stop monitoring and clean up."""
        if not self.running:
            return
        
        self.running = False
        self.update_ui_state()
        self.status_message.set("Stopping monitoring...")
        
        # Kill any playing videos
        self.mpv.kill_processes()
        
        # Restore Spotify volume if needed
        if self.mute_spotify_var.get():
            self.spotify.restore_volume()
        
        self.status_message.set("Monitoring stopped")
    
    def monitor_spotify(self):
        """Monitor Spotify for track changes and play corresponding YouTube videos."""
        last_track_id = None
        
        while self.running:
            try:
                # Get current track
                track_info = self.spotify.get_currently_playing()
                
                # Update UI with track info
                self.root.after(0, lambda t=track_info: self.update_track_display(t))
                
                if not track_info:
                    time.sleep(self.config["app"]["check_interval"])
                    continue
                
                # Check if track has changed
                if track_info["track_id"] != last_track_id:
                    self.status_message.set(f"New track detected: {track_info['track_name']}")
                    
                    # Search for video
                    self.root.after(0, lambda: self.status_message.set("Searching for video..."))
                    video_info = self.youtube.search_video(track_info["track_query"])
                    
                    # Update UI with video info
                    self.root.after(0, lambda v=video_info: self.update_video_display(v))
                    
                    if video_info:
                        # Mute Spotify if configured
                        if self.mute_spotify_var.get():
                            self.spotify.set_volume(0)
                        
                        # Play video
                        self.root.after(0, lambda: self.status_message.set("Playing video..."))
                        self.mpv.play_video(video_info, track_info["progress_ms"])
                        self.current_video = video_info
                        
                        self.root.after(0, lambda: self.status_message.set(f"Now playing: {video_info['title']}"))
                        last_track_id = track_info["track_id"]
                    else:
                        self.root.after(0, lambda: self.status_message.set("No video found for this track"))
                
                # Sleep for the configured interval
                time.sleep(self.config["app"]["check_interval"])
                
            except Exception as e:
                self.root.after(0, lambda e=e: self.status_message.set(f"Error: {e}"))
                time.sleep(self.config["app"]["check_interval"])
                
    def next_track(self):
        """Skip to the next track."""
        if self.spotify.skip_to_next_track():
            self.status_message.set("Skipped to next track")
        else:
            self.status_message.set("Failed to skip to next track")
    
    def previous_track(self):
        """Skip to the previous track."""
        if self.spotify.skip_to_previous_track():
            self.status_message.set("Skipped to previous track")
        else:
            self.status_message.set("Failed to skip to previous track")
    
    def show_config_dialog(self):
        """Show the configuration dialog."""
        config_dialog = ConfigDialog(self.root, self.config)
        if config_dialog.result:
            self.config = config_dialog.result
            ConfigManager.save_config(self.config)
            
            # Reinitialize managers with new config
            self.spotify = SpotifyManager(self.config)
            self.youtube = YouTubeManager(self.config)
            self.mpv = MPVManager(self.config)
            
            # Update UI
            self.mute_spotify_var.set(self.config["app"]["mute_spotify"])
            self.status_message.set("Configuration updated")


class ConfigDialog:
    """Dialog for editing the application configuration."""
    
    def __init__(self, parent, config):
        self.parent = parent
        self.config = config.copy()
        self.result = None
        
        # Create dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Spotube Settings")
        self.dialog.geometry("500x550")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Define colors for consistency
        self.bg_color = "#121212"  # Dark background
        self.text_color = "#FFFFFF"  # White text
        self.accent_color = "#1DB954"  # Spotify green
        self.border_color = "#333333"  # Dark gray for borders
        
        # Configure ttk styles to remove/darken borders
        self.configure_styles()
        
        # Make dialog modal
        self.dialog.focus_set()
        self.dialog.protocol("WM_DELETE_WINDOW", self.cancel)
        
        # Create UI
        self.create_ui()
        
        # Wait for dialog to close
        parent.wait_window(self.dialog)
    
    def configure_styles(self):
        style = ttk.Style()
        style.configure("TFrame", background=self.bg_color, borderwidth=0)
        style.configure("TLabelframe", background=self.bg_color, borderwidth=1, relief="solid", bordercolor=self.border_color)
        style.configure("TLabelframe.Label", background=self.bg_color, foreground=self.text_color)
        style.configure("TLabel", background=self.bg_color, foreground=self.text_color, borderwidth=0)
        style.configure("TButton", background=self.bg_color, foreground=self.text_color, borderwidth=1, bordercolor=self.border_color)
        style.configure("TEntry", fieldbackground=self.bg_color, foreground=self.text_color, bordercolor=self.border_color)
        style.configure("TNotebook", background=self.bg_color, borderwidth=0)
        style.configure("TNotebook.Tab", background=self.bg_color, foreground=self.text_color, borderwidth=1, bordercolor=self.border_color)
        style.configure("TCheckbutton", background=self.bg_color, foreground=self.text_color)
        style.configure("TSpinbox", fieldbackground=self.bg_color, foreground=self.text_color, bordercolor=self.border_color)
    
    def create_ui(self):
        """Create the configuration dialog UI."""
        # Main frame
        main_frame = ttk.Frame(self.dialog, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Notebook for tabs
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # =====================
        # Spotify tab
        # =====================
        spotify_frame = ttk.Frame(notebook, padding=10)
        notebook.add(spotify_frame, text="Spotify")
        
        # Create a frame for the credentials
        creds_frame = ttk.LabelFrame(spotify_frame, text="Spotify API Credentials")
        creds_frame.grid(row=0, column=0, columnspan=2, sticky=tk.W+tk.E+tk.N, pady=5, padx=5)
        creds_frame.columnconfigure(1, weight=1)  # Make the entry column expandable
        
        # Client ID
        ttk.Label(creds_frame, text="Client ID:").grid(row=0, column=0, sticky=tk.W, pady=5, padx=5)
        self.spotify_client_id = ttk.Entry(creds_frame, width=40)
        self.spotify_client_id.grid(row=0, column=1, sticky=tk.W+tk.E, pady=5, padx=5)
        self.spotify_client_id.insert(0, self.config["spotify"]["client_id"])
        
        # Client Secret
        ttk.Label(creds_frame, text="Client Secret:").grid(row=1, column=0, sticky=tk.W, pady=5, padx=5)
        self.spotify_client_secret = ttk.Entry(creds_frame, width=40, show="*")
        self.spotify_client_secret.grid(row=1, column=1, sticky=tk.W+tk.E, pady=5, padx=5)
        self.spotify_client_secret.insert(0, self.config["spotify"]["client_secret"])
        
        # Toggle button to show/hide secret
        self.show_secret_var = tk.BooleanVar(value=False)
        show_secret_check = ttk.Checkbutton(
            creds_frame, 
            text="Show Secret", 
            variable=self.show_secret_var,
            command=self.toggle_secret_visibility
        )
        show_secret_check.grid(row=1, column=2, padx=5)
        
        # Redirect URI
        ttk.Label(creds_frame, text="Redirect URI:").grid(row=2, column=0, sticky=tk.W, pady=5, padx=5)
        self.spotify_redirect_uri = ttk.Entry(creds_frame, width=40)
        self.spotify_redirect_uri.grid(row=2, column=1, sticky=tk.W+tk.E, pady=5, padx=5)
        self.spotify_redirect_uri.insert(0, self.config["spotify"]["redirect_uri"])
        
        # Default button
        default_uri_button = ttk.Button(
            creds_frame,
            text="Default",
            command=lambda: self.spotify_redirect_uri.delete(0, tk.END) or 
                        self.spotify_redirect_uri.insert(0, "http://localhost:8080")
        )
        default_uri_button.grid(row=2, column=2, padx=5)
        
        # Help text in a scrollable frame
        help_frame = ttk.LabelFrame(spotify_frame, text="Spotify Developer Setup Instructions")
        help_frame.grid(row=1, column=0, columnspan=2, sticky=tk.W+tk.E+tk.N+tk.S, pady=10, padx=5)
        help_frame.columnconfigure(0, weight=1)
        help_frame.rowconfigure(0, weight=1)
        
        # Detailed instructions
        help_text = (
            "To connect Spotube with your Spotify account:\n\n"
            "1. Go to https://developer.spotify.com/dashboard/ and log in\n"
            "2. Click 'Create App' button\n"
            "3. Fill in the following details:\n"
            "   • App name: Spotube (or any name you prefer)\n"
            "   • App description: Personal YouTube music video player\n"
            "   • Website: You can leave this blank\n"
            "   • Redirect URI: http://localhost:8080\n"
            "4. Check the Developer Terms of Service and click 'Create'\n"
            "5. On your app's dashboard, you'll see your Client ID\n"
            "6. Click 'Show Client Secret' to reveal your Client Secret\n"
            "7. Copy both values to the fields above\n\n"
            "Important: Keep your Client Secret private. Never share it publicly.\n\n"
            "When you first run Spotube, a browser window will open asking you to\n"
            "authorize the app to access your Spotify account. This is normal and\n"
            "required for Spotube to see what you're currently playing."
        )
        
        # Add scrollable text widget
        from tkinter import scrolledtext
        help_text_widget = scrolledtext.ScrolledText(
        help_frame, 
        wrap=tk.WORD, 
        width=40, 
        height=12, 
        font=("Helvetica", 9),
        background=self.bg_color,
        foreground=self.text_color,
        borderwidth=1,
        highlightbackground=self.border_color,
        highlightcolor=self.border_color,
        highlightthickness=1
        )
        help_text_widget.insert(tk.INSERT, help_text)
        help_text_widget.config(state=tk.DISABLED)  # Make read-only
        help_text_widget.grid(row=0, column=0, sticky=tk.W+tk.E+tk.N+tk.S, padx=5, pady=5)
        
        # Add a direct link button
        button_frame = ttk.Frame(help_frame)
        button_frame.grid(row=1, column=0, sticky=tk.E+tk.W, pady=5)
        
        link_button = ttk.Button(
            button_frame, 
            text="Open Spotify Developer Dashboard",
            command=lambda: webbrowser.open("https://developer.spotify.com/dashboard/")
        )
        link_button.pack(side=tk.LEFT, padx=5)
        
        # Add a test connection button
        test_button = ttk.Button(
            button_frame, 
            text="Test Connection",
            command=self.test_spotify_connection
        )
        test_button.pack(side=tk.RIGHT, padx=5)
        
        # =====================
        # YouTube tab
        # =====================
        youtube_frame = ttk.Frame(notebook, padding=10)
        notebook.add(youtube_frame, text="YouTube")
        
        # API Key field
        api_key_frame = ttk.LabelFrame(youtube_frame, text="YouTube API Key")
        api_key_frame.grid(row=0, column=0, sticky=tk.W+tk.E, pady=5, padx=5)
        api_key_frame.columnconfigure(1, weight=1)
        
        ttk.Label(api_key_frame, text="API Key:").grid(row=0, column=0, sticky=tk.W, pady=5, padx=5)
        self.youtube_api_key = ttk.Entry(api_key_frame, width=40)
        self.youtube_api_key.grid(row=0, column=1, sticky=tk.W+tk.E, pady=5, padx=5)
        self.youtube_api_key.insert(0, self.config["youtube"]["api_key"])
        
        # Help text in a scrollable frame
        yt_help_frame = ttk.LabelFrame(youtube_frame, text="YouTube API Setup Instructions")
        yt_help_frame.grid(row=1, column=0, sticky=tk.W+tk.E+tk.N+tk.S, pady=10, padx=5)
        yt_help_frame.columnconfigure(0, weight=1)
        yt_help_frame.rowconfigure(0, weight=1)
        
        # Detailed instructions
        yt_help_text = (
            "To get a YouTube Data API key:\n\n"
            "1. Go to https://console.cloud.google.com/\n"
            "2. Sign in with your Google account\n"
            "3. Create a new project (click on project dropdown at top → New Project)\n"
            "4. Once in your project, go to 'APIs & Services' → 'Library'\n"
            "5. Search for 'YouTube Data API v3' and select it\n"
            "6. Click 'Enable' to activate the API for your project\n"
            "7. Go to 'APIs & Services' → 'Credentials'\n"
            "8. Click 'Create Credentials' → 'API key'\n"
            "9. Copy your new API key and paste it in the field above\n\n"
            "Note: The free tier allows 10,000 queries per day, which is plenty for personal use."
        )
        
        # Add scrollable text widget
        yt_help_text_widget = scrolledtext.ScrolledText(
        yt_help_frame, 
        wrap=tk.WORD, 
        width=40, 
        height=12, 
        font=("Helvetica", 9),
        background=self.bg_color,
        foreground=self.text_color,
        borderwidth=1,
        highlightbackground=self.border_color,
        highlightcolor=self.border_color,
        highlightthickness=1
        )
        
        yt_help_text_widget.insert(tk.INSERT, yt_help_text)
        yt_help_text_widget.config(state=tk.DISABLED)  # Make read-only
        yt_help_text_widget.grid(row=0, column=0, sticky=tk.W+tk.E+tk.N+tk.S, padx=5, pady=5)
        
        # Add a direct link button
        yt_button_frame = ttk.Frame(yt_help_frame)
        yt_button_frame.grid(row=1, column=0, sticky=tk.E+tk.W, pady=5)
        
        yt_link_button = ttk.Button(
            yt_button_frame, 
            text="Open Google Cloud Console",
            command=lambda: webbrowser.open("https://console.cloud.google.com/")
        )
        yt_link_button.pack(side=tk.LEFT, padx=5)
        
        # Add a test button
        yt_test_button = ttk.Button(
            yt_button_frame, 
            text="Test API Key",
            command=self.test_youtube_api_key
        )
        yt_test_button.pack(side=tk.RIGHT, padx=5)
        
        # =====================
        # App Settings tab
        # =====================
        app_frame = ttk.Frame(notebook, padding=10)
        notebook.add(app_frame, text="App Settings")
        
        # Playback settings
        playback_frame = ttk.LabelFrame(app_frame, text="Playback Settings")
        playback_frame.grid(row=0, column=0, sticky=tk.W+tk.E+tk.N, pady=5, padx=5)
        playback_frame.columnconfigure(1, weight=1)
        
        ttk.Label(playback_frame, text="Check Interval (seconds):").grid(row=0, column=0, sticky=tk.W, pady=5, padx=5)
        self.check_interval = ttk.Spinbox(playback_frame, from_=1, to=30, width=5)
        self.check_interval.grid(row=0, column=1, sticky=tk.W, pady=5, padx=5)
        self.check_interval.insert(0, str(self.config["app"]["check_interval"]))
        
        self.mute_spotify_var = tk.BooleanVar(value=self.config["app"]["mute_spotify"])
        mute_spotify_check = ttk.Checkbutton(
            playback_frame, 
            text="Mute Spotify while playing videos",
            variable=self.mute_spotify_var
        )
        mute_spotify_check.grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=5, padx=5)
        
        # Video window settings
        window_frame = ttk.LabelFrame(app_frame, text="Video Window Settings")
        window_frame.grid(row=1, column=0, sticky=tk.W+tk.E+tk.N, pady=5, padx=5)
        window_frame.columnconfigure(1, weight=1)
        
        self.mpv_fullscreen_var = tk.BooleanVar(value=self.config["app"]["mpv_fullscreen"])
        mpv_fullscreen_check = ttk.Checkbutton(
            window_frame, 
            text="Play videos in fullscreen",
            variable=self.mpv_fullscreen_var
        )
        mpv_fullscreen_check.grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=5, padx=5)
        
        ttk.Label(window_frame, text="Video Window Width:").grid(row=1, column=0, sticky=tk.W, pady=5, padx=5)
        self.mpv_window_width = ttk.Spinbox(window_frame, from_=320, to=3840, width=5)
        self.mpv_window_width.grid(row=1, column=1, sticky=tk.W, pady=5, padx=5)
        self.mpv_window_width.insert(0, str(self.config["app"]["mpv_window_width"]))
        
        ttk.Label(window_frame, text="Video Window Height:").grid(row=2, column=0, sticky=tk.W, pady=5, padx=5)
        self.mpv_window_height = ttk.Spinbox(window_frame, from_=240, to=2160, width=5)
        self.mpv_window_height.grid(row=2, column=1, sticky=tk.W, pady=5, padx=5)
        self.mpv_window_height.insert(0, str(self.config["app"]["mpv_window_height"]))
        
        # About section
        about_frame = ttk.LabelFrame(app_frame, text="About Spotube")
        about_frame.grid(row=2, column=0, sticky=tk.W+tk.E+tk.N+tk.S, pady=5, padx=5)
        
        about_text = (
            "Spotube plays YouTube music videos that match your currently playing Spotify tracks.\n\n"
            "Requirements:\n"
            "• MPV Player (https://mpv.io/)\n"
            "• Spotify Premium account\n"
            "• YouTube Data API key\n\n"
            "Version: 1.0.0"
        )
        
        about_label = ttk.Label(about_frame, text=about_text, wraplength=400, justify=tk.LEFT)
        about_label.pack(padx=5, pady=5, anchor=tk.W)
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(button_frame, text="Save", command=self.save).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=self.cancel).pack(side=tk.RIGHT, padx=5)
        
    def toggle_secret_visibility(self):
        """Toggle visibility of the client secret."""
        if self.show_secret_var.get():
            self.spotify_client_secret.config(show="")
        else:
            self.spotify_client_secret.config(show="*")

    def test_spotify_connection(self):
        """Test the Spotify API connection with current credentials."""
        # Save current values to config temporarily
        temp_client_id = self.config["spotify"]["client_id"]
        temp_client_secret = self.config["spotify"]["client_secret"]
        temp_redirect_uri = self.config["spotify"]["redirect_uri"]
        
        try:
            # Update config with current values
            self.config["spotify"]["client_id"] = self.spotify_client_id.get()
            self.config["spotify"]["client_secret"] = self.spotify_client_secret.get()
            self.config["spotify"]["redirect_uri"] = self.spotify_redirect_uri.get()
            
            # Create a temporary Spotify client
            sp = spotipy.Spotify(
                auth_manager=SpotifyOAuth(
                    client_id=self.config["spotify"]["client_id"],
                    client_secret=self.config["spotify"]["client_secret"],
                    redirect_uri=self.config["spotify"]["redirect_uri"],
                    scope="user-read-playback-state",
                    open_browser=True
                )
            )
            
            # Try to get current user info
            user_info = sp.current_user()
            
            # If we get here, connection was successful
            messagebox.showinfo(
                "Connection Successful", 
                f"Successfully connected to Spotify as {user_info['display_name']}!"
            )
        except Exception as e:
            messagebox.showerror("Connection Failed", f"Failed to connect to Spotify: {e}")
        finally:
            # Restore original config values
            self.config["spotify"]["client_id"] = temp_client_id
            self.config["spotify"]["client_secret"] = temp_client_secret
            self.config["spotify"]["redirect_uri"] = temp_redirect_uri

    def test_youtube_api_key(self):
        """Test the YouTube API key."""
        # Save current value to config temporarily
        temp_api_key = self.config["youtube"]["api_key"]
        
        try:
            # Update config with current value
            self.config["youtube"]["api_key"] = self.youtube_api_key.get()
            
            # Create a YouTube API client
            youtube = build(
                "youtube", "v3", developerKey=self.config["youtube"]["api_key"]
            )
            
            # Try to search for a video
            request = youtube.search().list(
                part="snippet", q="test", type="video", maxResults=1
            )
            response = request.execute()
            
            # If we get here, connection was successful
            if "items" in response and len(response["items"]) > 0:
                video_title = response["items"][0]["snippet"]["title"]
                messagebox.showinfo(
                    "API Key Valid", 
                    f"Successfully connected to YouTube API!\nFound video: {video_title}"
                )
            else:
                messagebox.showinfo(
                    "API Key Valid", 
                    "Successfully connected to YouTube API, but no videos were found."
                )
        except Exception as e:
            messagebox.showerror("API Key Invalid", f"Failed to connect to YouTube API: {e}")
        finally:
            # Restore original config value
            self.config["youtube"]["api_key"] = temp_api_key

    def save(self):
        """Save the configuration and close the dialog."""
        try:
            # Update Spotify config
            self.config["spotify"]["client_id"] = self.spotify_client_id.get()
            self.config["spotify"]["client_secret"] = self.spotify_client_secret.get()
            self.config["spotify"]["redirect_uri"] = self.spotify_redirect_uri.get()
            
            # Update YouTube config
            self.config["youtube"]["api_key"] = self.youtube_api_key.get()
            
            # Update app config
            self.config["app"]["check_interval"] = int(self.check_interval.get())
            self.config["app"]["mute_spotify"] = self.mute_spotify_var.get()
            self.config["app"]["mpv_fullscreen"] = self.mpv_fullscreen_var.get()
            self.config["app"]["mpv_window_width"] = int(self.mpv_window_width.get())
            self.config["app"]["mpv_window_height"] = int(self.mpv_window_height.get())
            
            self.result = self.config
            self.dialog.destroy()
        except ValueError as e:
            messagebox.showerror("Invalid Input", f"Please check your inputs: {e}")
    
    def cancel(self):
        """Cancel and close the dialog."""
        self.dialog.destroy()

def load_image_from_url(url):
    """Load an image from a URL and return a PIL Image object."""
    try:
        with urllib.request.urlopen(url) as response:
            image_data = response.read()
        return Image.open(io.BytesIO(image_data))
    except Exception as e:
        print(f"Error loading image from URL: {e}")
        return None

def main():
    """Main entry point for the application."""
    root = tk.Tk()
    root.title("Spotube")
    
    # Create app instance first
    app = SpotubeGUI(root)
    

    # Set icon if available
    try:
        icon_path = Path(__file__).parent / "icon.png"
        if icon_path.exists():
            img = Image.open(icon_path)
            photo = ImageTk.PhotoImage(img)
            root.iconphoto(True, photo)
    except Exception:
        pass
        
    root.mainloop()

if __name__ == "__main__":
    main()

