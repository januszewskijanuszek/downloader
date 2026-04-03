# Media Downloader

A command-line tool for downloading music from **YouTube** and **Spotify**.

## Project Structure

```
downloader/
├── youtube_downloader.py   # YouTube download functions + CLI
├── spotify_downloader.py   # Spotify download functions + CLI
├── spotify_secret.py       # Your Spotify API credentials (gitignored)
├── downloads/              # Downloaded files saved here
├── .gitignore
└── README.md
```

---

## Setup

### 1. Install Python

Python 3.9 or newer is required.

### 2. Install dependencies

```bash
pip install yt-dlp spotipy imageio-ffmpeg
```

### 3. ffmpeg

ffmpeg is needed for mp3 conversion, merging video+audio streams, and re-encoding audio to AAC for maximum player compatibility.

The tool **auto-detects ffmpeg** in this order:
1. System PATH (e.g. installed via `winget install --id Gyan.FFmpeg`)
2. Bundled binary from the `imageio-ffmpeg` Python package (installed above)

> No manual ffmpeg setup is needed if you installed `imageio-ffmpeg`.
> Without ffmpeg the tools still work but videos are limited to low-quality single-stream formats (e.g. 360p).

---

## YouTube Downloader

No API keys needed. Works out of the box.

### Download as mp3 (default)

```bash
python youtube_downloader.py "https://www.youtube.com/watch?v=VIDEO_ID"
```

### Download as video (up to 4K)

```bash
python youtube_downloader.py "https://www.youtube.com/watch?v=VIDEO_ID" -v
```

With ffmpeg available, this downloads the best video + best audio streams and merges them into an MP4 with AAC audio for universal player compatibility.

### Choose video quality

```bash
python youtube_downloader.py "URL" -v -q 1080
```

### Show video info only

```bash
python youtube_downloader.py "URL" -i
```

### Custom output folder

```bash
python youtube_downloader.py "URL" -o my_folder
```

### All YouTube flags

| Flag | Description |
|------|-------------|
| (none) | Downloads as mp3 by default |
| `-v` | Download as video (mp4) instead of mp3 |
| `-q 1080` | Video quality: `best`, `2160`, `1440`, `1080`, `720`, `480`, `360` |
| `-o DIR` | Output directory (default: `downloads`) |
| `-i` | Show video info without downloading |

---

## Spotify Downloader

Requires free Spotify API credentials. Downloads audio by searching YouTube for the track.

### 1. Get Spotify API credentials

1. Go to **https://developer.spotify.com/dashboard**
2. Log in and click **Create App**
3. Copy your **Client ID** and **Client Secret**

### 2. Set credentials

Set environment variables before running:

**PowerShell:**
```powershell
$env:SPOTIFY_CLIENT_ID="your_client_id_here"
$env:SPOTIFY_CLIENT_SECRET="your_client_secret_here"
```

**Bash / macOS / Linux:**
```bash
export SPOTIFY_CLIENT_ID="your_client_id_here"
export SPOTIFY_CLIENT_SECRET="your_client_secret_here"
```

> To make them permanent, add the export lines to your shell profile (`~/.bashrc`, `~/.zshrc`, or PowerShell `$PROFILE`).

### 3. Download a track

```bash
python spotify_downloader.py "https://open.spotify.com/track/TRACK_ID"
```

### Download an album

```bash
python spotify_downloader.py "https://open.spotify.com/album/ALBUM_ID"
```

### Download a playlist

```bash
python spotify_downloader.py "https://open.spotify.com/playlist/PLAYLIST_ID"
```

### Choose audio format

```bash
python spotify_downloader.py "URL" -f flac
```

### Show track info only

```bash
python spotify_downloader.py "URL" -i
```

### All Spotify flags

| Flag | Description |
|------|-------------|
| (none) | Downloads as mp3 by default |
| `-f FORMAT` | Audio format: `mp3`, `flac`, `ogg`, `opus`, `m4a`, `wav` |
| `-o DIR` | Output directory (default: `downloads`) |
| `-i` | Show track/album/playlist info without downloading |

---

## Notes

- All downloads are saved to the `downloads/` folder by default.
- Respect the Terms of Service of YouTube and Spotify.
- Download content only when you have permission.