# Spotube

**Spotube** is a Python-based application that syncs your Spotify playback with YouTube, automatically finding and playing the corresponding music video for the currently playing Spotify track.  

So you don't have to... awkwardly search for it yourself.  

![Spotube](https://raw.githubusercontent.com/dullmace/spottube/main/appicon.png)

---

## ✨ Features

- **Spotify Integration**: Automatically detects the currently playing track on Spotify.
- **YouTube Sync**: Searches for and plays the official music video on YouTube.
- **MPV Player Support**: Plays YouTube videos seamlessly using the MPV media player.
- **Customizable Settings**: Configure Spotify, YouTube, and playback preferences.
- **GUI Interface**: User-friendly interface built with Tkinter.
- **Cross-Platform**: Works on Windows, macOS, and Linux.

---

## 📋 Requirements

1. **Spotify Premium Account**: Required for playback control.
2. **YouTube Data API Key**: To search for videos on YouTube.
3. **MPV Media Player**: For video playback. [Download MPV](https://mpv.io/).
4. **Python 3.7+**: Ensure you have Python installed.

---

## 🚀 Installation

### Quick Start

1. Clone the repository:
   ```bash
   git clone https://github.com/your-username/spotube.git
   cd spotube
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Install MPV:
   - **Windows**: Download the installer from [MPV's website](https://mpv.io/installation/).
   - **macOS**: Install via Homebrew:
     ```bash
     brew install mpv
     ```
   - **Linux**: Install via your package manager:
     ```bash
     sudo apt install mpv  # For Debian/Ubuntu
     ```

4. Run the application:
   ```bash
   python spotube.py
   ```

---

## ⚙️ Configuration

Spotube requires API credentials to connect with Spotify and YouTube.  
On the first run, it will create a `config.json` file that you'll need to configure through the Settings dialog.

### Spotify API Setup

1. Go to the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard/).
2. Click **Create App**.
3. Fill in the following details:
   - **App name**: Spotube (or any name you prefer)
   - **App description**: Personal YouTube music video player
   - **Redirect URI**: `http://localhost:8080`
4. Check the Developer Terms of Service and click **Create**.
5. Copy your **Client ID** and **Client Secret**.
6. Enter these details in the Spotube app's settings.

> **Note**: When you first run Spotube, a browser window will open asking you to authorize the app to access your Spotify account. This is normal and required for Spotube to see what you're currently playing.

### YouTube Data API Key Setup

1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Sign in with your Google account.
3. Create a new project (click on the project dropdown at the top → **New Project**).
4. Go to **APIs & Services** → **Library**.
5. Search for **YouTube Data API v3** and enable it.
6. Go to **APIs & Services** → **Credentials**.
7. Click **Create Credentials** → **API key**.
8. Copy your new API key and paste it into the app's settings.

> **Note**: The free tier allows 10,000 queries per day, which is plenty for personal use.

---

## 🎮 Usage

1. Start playing music on Spotify.
2. Launch Spotube and click **Start Monitoring**.
3. Spotube will detect your current track and find the matching YouTube video.
4. The video will play in an MPV window, synchronized with your Spotify playback.
5. As you change tracks in Spotify, Spotube automatically updates the video.

---

## 🔧 Advanced Configuration

You can edit the `config.json` file or use the Settings dialog to customize:

```json
{
  "spotify": {
    "client_id": "YOUR_SPOTIFY_CLIENT_ID",
    "client_secret": "YOUR_SPOTIFY_CLIENT_SECRET",
    "redirect_uri": "http://localhost:8080",
    "scope": "user-read-playback-state user-modify-playback-state"
  },
  "youtube": {
    "api_key": "YOUR_YOUTUBE_API_KEY"
  },
  "app": {
    "check_interval": 5,
    "mute_spotify": true,
    "mpv_fullscreen": false,
    "mpv_window_width": 1280,
    "mpv_window_height": 720
  }
}
```

---

## 🔍 Troubleshooting

| Issue                          | Solution                                                                 |
|--------------------------------|-------------------------------------------------------------------------|
| **MPV Not Found**              | Ensure MPV is installed and in your system PATH.                        |
| **Spotify Authentication Failed** | Verify your Spotify API credentials and check that your redirect URI matches exactly. |
| **YouTube API Errors**         | Confirm your API key is valid and has the YouTube Data API enabled.     |
| **No Videos Playing**          | Make sure you have an active Spotify playback session.                  |
| **High CPU Usage**             | Increase the check interval in settings.                               |

---

## 🛠️ Development

Spotube is built with:
- **Tkinter** for the GUI
- **Spotipy** for Spotify API integration
- **Google API Client** for YouTube API access
- **MPV** for video playback

---

## 📄 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- [Spotipy](https://github.com/plamere/spotipy) for the excellent Spotify API wrapper.
- [MPV](https://mpv.io/) for the powerful and lightweight video player.
- [Google API Python Client](https://github.com/googleapis/google-api-python-client) for YouTube API access.

---

**Disclaimer**: Spotube is an unofficial application and is not affiliated with, endorsed by, or connected to Spotify or YouTube.  

Enjoy syncing your Spotify tracks with YouTube videos effortlessly! 🎵🎥
