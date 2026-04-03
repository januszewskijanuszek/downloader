import shutil
import os
import sys

import yt_dlp
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

HAS_FFMPEG = shutil.which("ffmpeg") is not None

SPOTIFY_CLIENT_ID = os.environ.get("SPOTIFY_CLIENT_ID", "")
SPOTIFY_CLIENT_SECRET = os.environ.get("SPOTIFY_CLIENT_SECRET", "")


def _get_spotify_client():
    if not SPOTIFY_CLIENT_ID or not SPOTIFY_CLIENT_SECRET:
        print("Error: Set SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET environment variables.",
              file=sys.stderr)
        print("Get them free at https://developer.spotify.com/dashboard",
              file=sys.stderr)
        sys.exit(1)
    return spotipy.Spotify(auth_manager=SpotifyClientCredentials(
        client_id=SPOTIFY_CLIENT_ID,
        client_secret=SPOTIFY_CLIENT_SECRET,
    ))


def _parse_spotify_url(url):
    """Extract track/album/playlist info from a Spotify URL."""
    sp = _get_spotify_client()
    if "track" in url:
        track = sp.track(url)
        artist = track["artists"][0]["name"]
        title = track["name"]
        return [{"query": f"{artist} - {title}", "title": title, "artist": artist}]
    elif "album" in url:
        album = sp.album(url)
        tracks = []
        for item in album["tracks"]["items"]:
            artist = item["artists"][0]["name"]
            title = item["name"]
            tracks.append({"query": f"{artist} - {title}", "title": title, "artist": artist})
        return tracks
    elif "playlist" in url:
        results = sp.playlist_items(url)
        tracks = []
        for item in results["items"]:
            t = item.get("track")
            if t:
                artist = t["artists"][0]["name"]
                title = t["name"]
                tracks.append({"query": f"{artist} - {title}", "title": title, "artist": artist})
        return tracks
    else:
        raise ValueError("Unsupported Spotify URL. Use a track, album, or playlist link.")


def get_track_info(url):
    """Show track info from a Spotify URL without downloading."""
    tracks = _parse_spotify_url(url)
    for i, t in enumerate(tracks, 1):
        print(f"{i}. {t['artist']} - {t['title']}")
    print(f"\nTotal: {len(tracks)} track(s)")
    return tracks


def download_track(url, output_dir="downloads", audio_format="mp3"):
    """Download Spotify track(s) by searching YouTube and saving as audio."""
    os.makedirs(output_dir, exist_ok=True)
    tracks = _parse_spotify_url(url)

    print(f"Found {len(tracks)} track(s). Downloading to '{output_dir}/' as {audio_format}...\n")

    opts = {
        "format": "bestaudio/best",
        "outtmpl": os.path.join(output_dir, "%(title)s.%(ext)s"),
        "quiet": False,
        "default_search": "ytsearch",
        "noplaylist": True,
    }

    if HAS_FFMPEG:
        opts["postprocessors"] = [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": audio_format,
                "preferredquality": "192",
            }
        ]
    else:
        print("Note: ffmpeg not found – audio will be saved in its original format.\n")

    with yt_dlp.YoutubeDL(opts) as ydl:
        for i, track in enumerate(tracks, 1):
            print(f"\n[{i}/{len(tracks)}] {track['query']}")
            try:
                ydl.download([f"ytsearch:{track['query']}"])
            except Exception as e:
                print(f"  Failed: {e}")

    print(f"\nDone! Saved to '{output_dir}/'")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Spotify Downloader")
    parser.add_argument("url", type=str, help="Spotify URL (track, album, or playlist)")
    parser.add_argument("-f", "--format", type=str, default="mp3",
                        choices=["mp3", "flac", "ogg", "opus", "m4a", "wav"],
                        help="Audio format (default: mp3)")
    parser.add_argument("-o", "--output", type=str, default="downloads",
                        help="Output directory (default: downloads)")
    parser.add_argument("-i", "--info", action="store_true",
                        help="Show track info without downloading")

    args = parser.parse_args()

    if args.info:
        get_track_info(args.url)
        return

    download_track(args.url, output_dir=args.output, audio_format=args.format)


if __name__ == "__main__":
    main()
