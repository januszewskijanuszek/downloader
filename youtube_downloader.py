import shutil

import yt_dlp
import os

HAS_FFMPEG = shutil.which("ffmpeg") is not None


def get_video_info(url):
    """Fetch video title, duration, and available formats without downloading."""
    with yt_dlp.YoutubeDL({"quiet": True}) as ydl:
        info = ydl.extract_info(url, download=False)
    return {
        "title": info.get("title"),
        "duration": info.get("duration"),
        "uploader": info.get("uploader"),
        "url": url,
    }


def download_video(url, output_dir="downloads", quality="best"):
    """Download a YouTube video to the given directory."""
    os.makedirs(output_dir, exist_ok=True)

    if HAS_FFMPEG:
        format_spec = "bestvideo+bestaudio/best"
        if quality != "best":
            format_spec = f"bestvideo[height<={quality}]+bestaudio/best[height<={quality}]"
    else:
        # No ffmpeg → pick the best single file that already has video+audio
        format_spec = "best"
        if quality != "best":
            format_spec = f"best[height<={quality}]"
        print("Note: ffmpeg not found – downloading best single-stream format (install ffmpeg for higher quality).")

    opts = {
        "format": format_spec,
        "outtmpl": os.path.join(output_dir, "%(title)s.%(ext)s"),
        "quiet": False,
    }
    if HAS_FFMPEG:
        opts["merge_output_format"] = "mp4"

    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([url])

    print(f"\nDone! Saved to '{output_dir}/'")


def download_audio(url, output_dir="downloads"):
    """Download only the audio track, convert to mp3 if ffmpeg is available."""
    os.makedirs(output_dir, exist_ok=True)

    opts = {
        "format": "bestaudio/best",
        "outtmpl": os.path.join(output_dir, "%(title)s.%(ext)s"),
        "quiet": False,
    }

    if HAS_FFMPEG:
        opts["postprocessors"] = [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ]
    else:
        print("Note: ffmpeg not found – audio will be saved in its original format (install ffmpeg for mp3 conversion).")

    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([url])

    print(f"\nDone! Audio saved to '{output_dir}/'")


def main():
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="YouTube Downloader")
    parser.add_argument("url", type=str, help="YouTube video URL to download")
    parser.add_argument("-q", "--quality", type=str, default="best",
                        help="Video quality: best, 720, 480, 360 (default: best)")
    parser.add_argument("-v", "--video", action="store_true",
                        help="Download as video instead of mp3")
    parser.add_argument("-o", "--output", type=str, default="downloads",
                        help="Output directory (default: downloads)")
    parser.add_argument("-i", "--info", action="store_true",
                        help="Show video info without downloading")

    args = parser.parse_args()
    url = args.url

    if args.info:
        info = get_video_info(url)
        print(f"Title:    {info['title']}")
        print(f"Uploader: {info['uploader']}")
        print(f"Duration: {info['duration']}s")
        return

    if args.video:
        download_video(url, output_dir=args.output, quality=args.quality)
    else:
        download_audio(url, output_dir=args.output)


if __name__ == "__main__":
    main()
