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
pip install yt-dlp spotipy
```

### 3. Install ffmpeg (recommended)

ffmpeg is needed for mp3 conversion and merging video+audio streams.

```bash
winget install --id Gyan.FFmpeg
```

> After installing, **restart your terminal** so ffmpeg is on PATH.
> Without ffmpeg the tools still work but with limited format options.

---

## YouTube Downloader

No API keys needed. Works out of the box.

### Download as mp3 (default)

```bash
python youtube_downloader.py "https://www.youtube.com/watch?v=VIDEO_ID"
```

### Download as video

```bash
python youtube_downloader.py "https://www.youtube.com/watch?v=VIDEO_ID" -v
```

### Choose video quality

```bash
python youtube_downloader.py "URL" -v -q 720
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
| `-q 720` | Video quality: `best`, `720`, `480`, `360` |
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