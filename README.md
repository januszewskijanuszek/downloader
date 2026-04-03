# YouTube Downloader App

A simple Python app for downloading YouTube videos to your computer.

## Overview

This project is a lightweight command-line YouTube downloader.
It is intended to:

- Download single videos from a YouTube URL
- Save videos locally in your chosen quality/format
- Provide a clean base you can extend with playlists, audio-only mode, and a UI

## Tech Stack

- Python 3.9+
- yt-dlp (recommended YouTube download library)

## Project Structure

```text
downloader/
	main.py
	README.md
```

## Setup

1. Install Python 3.9 or newer.
2. Create and activate a virtual environment (recommended).
3. Install dependencies:

```bash
pip install yt-dlp
```

## Basic Usage

Run the app:

```bash
python main.py
```

You can then provide a YouTube URL and download the video.

## Example Download Command (with yt-dlp)

If you want to test downloading directly before integrating full app logic:

```bash
yt-dlp "https://www.youtube.com/watch?v=VIDEO_ID"
```

## Suggested Features

- Download best available quality automatically
- Let user choose output folder
- Audio-only mode (mp3/m4a)
- Playlist support
- Download progress display
- Better error handling for invalid/private URLs

## Notes

- Respect YouTube's Terms of Service and local copyright laws.
- Download content only when you have permission.

## Current Status

The repository currently includes starter files. Expand `main.py` with downloader logic using `yt-dlp`.