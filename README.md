# Spotube

**Spotube** is a Python-based application that syncs your Spotify playback with YouTube, automatically finding and playing the corresponding music video for the currently playing Spotify track.  

So you don't have to... awkwardly search for it yourself.  

![Spotube](https://raw.githubusercontent.com/dullmace/spottube/main/appicon.png)

---
<br>

## ✨ Features

- **Spotify Integration**: Automatically detects the currently playing track on Spotify.
- **YouTube Sync**: Searches for and plays the official music video on YouTube.
- **MPV Player Support**: Plays YouTube videos seamlessly using the MPV media player.
- **Customizable Settings**: Configure Spotify, YouTube, and playback preferences.
- **GUI Interface**: User-friendly interface built with Tkinter.
- **Cross-Platform**: Works on Windows, macOS, and Linux.

  
---
<br>

## 📋 Requirements

1. **Spotify Premium Account**: Required for playback control.
2. **YouTube Data API Key**: To search for videos on YouTube.
3. **MPV Media Player**: For video playback. [Download MPV](https://mpv.io/).
4. **Python 3.7+**: Ensure you have Python installed.

  
---
  <br>
  
## 🚀 Installation

Welcome! Follow these steps to get started with Spotube. Whether you're a beginner or an experienced developer, this guide will walk you through the process.
  <br>
  
### 🏃‍♂️ Quick Start

#### Option 1: **Clone the repository using Git**  
If you have Git installed, you can download the Spotube code by running the following commands in your terminal:

```bash
git clone https://github.com/your-username/spotube.git
cd spotube
```

> 💡 *Tip*: If you don’t have Git installed, [download it here](https://git-scm.com/downloads) and follow the installation instructions.

#### Option 2: **Manually download the code**  
If you don’t want to use Git, you can manually download the code:

1. Go to the [Spotube GitHub repository](https://github.com/dullmace/spotube).  
2. Click the green **Code** button near the top right of the page.  
3. Select **Download ZIP** from the dropdown menu.  
4. Once the ZIP file is downloaded, extract it to a folder of your choice.  
5. Open a terminal and navigate to the extracted folder. For example:

   ```bash
   cd path/to/spotube
   ```
   
  <br>
  
---

### 🖥️ Install Dependencies

Spotube uses Python, so you'll need to install the required libraries. Run the following command in the terminal (inside the Spotube folder):

```bash
pip install -r requirements.txt
```

> 💡 *Tip*: Make sure you have Python installed. If not, [download it here](https://www.python.org/downloads/). During installation, check the box to "Add Python to PATH."
   
  <br>
  
---

### 🖥️ Installing MPV

#### **Windows**

The easiest way to install MPV on Windows is by using **Chocolatey**, a package manager for Windows.

1. **Open a terminal as Administrator**  
   - Press **Win+X** and select one of the following:
     - Windows PowerShell (Admin)
     - Command Prompt (Admin)
     - Terminal (Admin)

2. **Install Chocolatey** (if you don’t already have it):  
   Copy and paste the following command into the terminal and press Enter:

   ```powershell
   Set-ExecutionPolicy Bypass -Scope Process -Force; `
   [System.Net.ServicePointManager]::SecurityProtocol = `
   [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; `
   iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
   ```

   > 💡 *Tip*: If you already have Chocolatey installed, you can skip this step.

3. **Install MPV using Chocolatey**:  
   Run the following command:

   ```bash
   choco install mpv
   ```

4. **Verify the installation**:  
   Check if MPV is installed correctly by running:

   ```bash
   mpv --version
   ```

   If you see the version number, you're good to go!

---

#### **macOS**

1. Install **Homebrew**, a package manager for macOS, if you don’t already have it. Follow the instructions at [brew.sh](https://brew.sh/).  
2. Use Homebrew to install MPV:

   ```bash
   brew install mpv
   ```

3. Verify the installation:

   ```bash
   mpv --version
   ```

---

#### **Linux**

1. Use your system's package manager to install MPV. For example:

   - **Debian/Ubuntu**:

     ```bash
     sudo apt install mpv
     ```

   - **Fedora**:

     ```bash
     sudo dnf install mpv
     ```

   - **Arch Linux**:

     ```bash
     sudo pacman -S mpv
     ```

2. Verify the installation:

   ```bash
   mpv --version
   ```
   
  <br>
  
---

### 🎉 Run the Application

Once everything is set up, you’re ready to run Spotube! Simply execute:

```bash
python spotube.py
```

> 💡 *Tip*: If you encounter any issues, double-check the steps above or visit the [Spotube GitHub Issues page](https://github.com/dullmace/spotube/issues) for help.
   
  <br>
  
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
   
  <br>
  
---

## 🎮 Usage

1. Start playing music on Spotify.
2. Launch Spotube and click **Start Monitoring**.
3. Spotube will detect your current track and find the matching YouTube video.
4. The video will play in an MPV window, synchronized with your Spotify playback.
5. As you change tracks in Spotify, Spotube automatically updates the video.
   
  <br>
  
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
   
  <br>
  
---
  
## 🔍 Troubleshooting

| Issue                          | Solution                                                                 |
|--------------------------------|-------------------------------------------------------------------------|
| **MPV Not Found**              | Ensure MPV is installed and in your system PATH.                        |
| **Spotify Authentication Failed** | Verify your Spotify API credentials and check that your redirect URI matches exactly. |
| **YouTube API Errors**         | Confirm your API key is valid and has the YouTube Data API enabled.     |
| **No Videos Playing**          | Make sure you have an active Spotify playback session.                  |
| **High CPU Usage**             | Increase the check interval in settings.                               |
   
  <br>
  
---
  
## 🛠️ Development

Spotube is built with:
- **Tkinter** for the GUI
- **Spotipy** for Spotify API integration
- **Google API Client** for YouTube API access
- **MPV** for video playback
   
  <br>
  
---
  
## 📄 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
   
  <br>
  
---
  
## 🙏 Acknowledgments

- [Spotipy](https://github.com/plamere/spotipy) for the excellent Spotify API wrapper.
- [MPV](https://mpv.io/) for the powerful and lightweight video player.
- [Google API Python Client](https://github.com/googleapis/google-api-python-client) for YouTube API access.
   
  <br>
  
---
  
**Disclaimer**: Spotube is an unofficial application and is not affiliated with, endorsed by, or connected to Spotify or YouTube.  

Enjoy syncing your Spotify tracks with YouTube videos effortlessly! 🎵🎥
