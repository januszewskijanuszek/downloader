import tkinter as tk
from tkinter import ttk, messagebox
import threading
import io
import urllib.request
import time
import os

from PIL import Image, ImageTk
import yt_dlp

from youtube_downloader import (
    get_video_info,
    download_video,
    download_audio,
    HAS_FFMPEG,
    FFMPEG_PATH,
)

# ── Helpers ──────────────────────────────────────────────────────────────────

def _fetch_youtube_details(url):
    """Return extended info dict for a YouTube URL (title, thumbnail, formats)."""
    opts = {"quiet": True, "skip_download": True}
    if HAS_FFMPEG:
        opts["ffmpeg_location"] = FFMPEG_PATH
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
    return info


def _estimate_size(info, quality, is_video):
    """Rough size estimate based on format list."""
    if not is_video:
        # audio only – find bestaudio
        for f in reversed(info.get("formats") or []):
            if f.get("acodec") != "none" and f.get("vcodec") == "none":
                fs = f.get("filesize") or f.get("filesize_approx")
                if fs:
                    return fs
        return None

    target_h = None if quality == "best" else int(quality)
    best_video = None
    best_audio = None
    for f in reversed(info.get("formats") or []):
        if f.get("vcodec") and f.get("vcodec") != "none":
            h = f.get("height") or 0
            if target_h is None or h <= target_h:
                if best_video is None or h > (best_video.get("height") or 0):
                    best_video = f
        if f.get("acodec") and f.get("acodec") != "none" and f.get("vcodec") == "none":
            if best_audio is None:
                best_audio = f

    total = 0
    if best_video:
        total += best_video.get("filesize") or best_video.get("filesize_approx") or 0
    if best_audio:
        total += best_audio.get("filesize") or best_audio.get("filesize_approx") or 0
    return total if total > 0 else None


def _format_size(nbytes):
    if nbytes is None:
        return "unknown"
    if nbytes < 1024 ** 2:
        return f"{nbytes / 1024:.0f} KB"
    if nbytes < 1024 ** 3:
        return f"{nbytes / 1024 ** 2:.1f} MB"
    return f"{nbytes / 1024 ** 3:.2f} GB"


def _format_duration(seconds):
    if seconds is None:
        return "unknown"
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


# ── GUI ──────────────────────────────────────────────────────────────────────

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Clanky Downloader v1.0")
        self.geometry("620x820")
        self.resizable(False, False)
        self.configure(bg="#1e1e2e")

        self._video_info = None  # cached yt-dlp info dict
        self._thumb_image = None  # prevent GC

        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TFrame", background="#1e1e2e")
        style.configure("TLabel", background="#1e1e2e", foreground="#cdd6f4", font=("Segoe UI", 10))
        style.configure("Header.TLabel", font=("Segoe UI", 13, "bold"), foreground="#89b4fa")
        style.configure("TRadiobutton", background="#1e1e2e", foreground="#cdd6f4", font=("Segoe UI", 10))
        style.configure("Accent.TButton", font=("Segoe UI", 11, "bold"))

        self._build_ui()

    # ── Layout ───────────────────────────────────────────────────────────

    def _build_ui(self):
        pad = {"padx": 14, "pady": 4}

        ttk.Label(self, text="Clanky Downloader v1.0", style="Header.TLabel").pack(anchor="w", padx=14, pady=(14, 2))
        url_frame = ttk.Frame(self)
        url_frame.pack(fill="x", **pad)

        # URL entry
        ttk.Label(self, text="Paste URL", style="Header.TLabel").pack(anchor="w", padx=14, pady=(14, 2))
        url_frame = ttk.Frame(self)
        url_frame.pack(fill="x", **pad)

        self.url_var = tk.StringVar()
        self.url_entry = ttk.Entry(url_frame, textvariable=self.url_var, font=("Segoe UI", 11))
        self.url_entry.pack(side="left", fill="x", expand=True)

        self.search_btn = ttk.Button(url_frame, text="Search", command=self._on_search)
        self.search_btn.pack(side="left", padx=(8, 0))

        # Source selector (YouTube / Spotify)
        src_frame = ttk.Frame(self)
        src_frame.pack(fill="x", padx=14, pady=(6, 2))
        ttk.Label(src_frame, text="Source:").pack(side="left")
        self.source_var = tk.StringVar(value="youtube")
        ttk.Radiobutton(src_frame, text="YouTube", variable=self.source_var, value="youtube",
                        command=self._on_source_change).pack(side="left", padx=(10, 4))
        ttk.Radiobutton(src_frame, text="Spotify", variable=self.source_var, value="spotify",
                        command=self._on_source_change).pack(side="left")

        # Thumbnail + info area
        self.info_frame = ttk.Frame(self)
        self.info_frame.pack(fill="x", padx=14, pady=(6, 2))

        self.thumb_label = ttk.Label(self.info_frame)
        self.thumb_label.pack(side="left", padx=(0, 12))

        self.info_text = ttk.Label(self.info_frame, text="", wraplength=350, justify="left")
        self.info_text.pack(side="left", anchor="nw")

        # ── YouTube options ──────────────────────────────────────────────
        self.yt_frame = ttk.Frame(self)
        self.yt_frame.pack(fill="x", padx=14, pady=(4, 0))

        # Format
        ttk.Label(self.yt_frame, text="Format:", style="Header.TLabel").grid(row=0, column=0, sticky="w", pady=(6, 2))
        self.format_var = tk.StringVar(value="mp4")
        fmt_frame = ttk.Frame(self.yt_frame)
        fmt_frame.grid(row=0, column=1, sticky="w", padx=10, pady=(6, 2))
        ttk.Radiobutton(fmt_frame, text="MP4 (video)", variable=self.format_var, value="mp4",
                        command=self._on_format_change).pack(side="left", padx=(0, 12))
        ttk.Radiobutton(fmt_frame, text="MP3 (audio)", variable=self.format_var, value="mp3",
                        command=self._on_format_change).pack(side="left")

        # Quality
        ttk.Label(self.yt_frame, text="Quality:", style="Header.TLabel").grid(row=1, column=0, sticky="w", pady=2)
        self.quality_var = tk.StringVar(value="best")
        q_frame = ttk.Frame(self.yt_frame)
        q_frame.grid(row=1, column=1, sticky="w", padx=10, pady=2)
        for q in ("best", "1080", "720", "360"):
            ttk.Radiobutton(q_frame, text=q if q == "best" else f"{q}p",
                            variable=self.quality_var, value=q,
                            command=self._update_size).pack(side="left", padx=(0, 10))

        # ── Spotify options (hidden by default) ──────────────────────────
        self.sp_frame = ttk.Frame(self)
        ttk.Label(self.sp_frame, text="Audio format:", style="Header.TLabel").pack(anchor="w")
        self.sp_format_var = tk.StringVar(value="mp3")
        sf = ttk.Frame(self.sp_frame)
        sf.pack(anchor="w", pady=2)
        for f in ("mp3", "flac", "ogg", "wav"):
            ttk.Radiobutton(sf, text=f, variable=self.sp_format_var, value=f).pack(side="left", padx=(0, 10))

        # Size label
        self.size_label = ttk.Label(self, text="", font=("Segoe UI", 10))
        self.size_label.pack(anchor="w", padx=14, pady=(6, 2))

        # Download button
        self.dl_btn = ttk.Button(self, text="Download", style="Accent.TButton", command=self._on_download)
        self.dl_btn.pack(pady=(10, 4))

        # Progress bars
        prog_style = ttk.Style(self)
        prog_style.configure("Video.Horizontal.TProgressbar", troughcolor="#313244", background="#89b4fa")
        prog_style.configure("Audio.Horizontal.TProgressbar", troughcolor="#313244", background="#a6e3a1")
        prog_style.configure("Merge.Horizontal.TProgressbar", troughcolor="#313244", background="#f9e2af")

        # Video progress
        self.vid_lbl = ttk.Label(self, text="Video", font=("Segoe UI", 9, "bold"))
        self.vid_lbl.pack(anchor="w", padx=14, pady=(8, 0))
        self.video_prog_var = tk.DoubleVar(value=0)
        self.video_prog_bar = ttk.Progressbar(self, variable=self.video_prog_var, maximum=100,
                                              length=580, style="Video.Horizontal.TProgressbar")
        self.video_prog_bar.pack(padx=14, pady=(2, 0))
        self.video_prog_label = ttk.Label(self, text="", font=("Segoe UI", 9))
        self.video_prog_label.pack(anchor="w", padx=14)

        # Audio progress
        self.aud_lbl = ttk.Label(self, text="Audio", font=("Segoe UI", 9, "bold"))
        self.aud_lbl.pack(anchor="w", padx=14, pady=(4, 0))
        self.audio_prog_var = tk.DoubleVar(value=0)
        self.audio_prog_bar = ttk.Progressbar(self, variable=self.audio_prog_var, maximum=100,
                                              length=580, style="Audio.Horizontal.TProgressbar")
        self.audio_prog_bar.pack(padx=14, pady=(2, 0))
        self.audio_prog_label = ttk.Label(self, text="", font=("Segoe UI", 9))
        self.audio_prog_label.pack(anchor="w", padx=14)

        # Merge progress
        self.merge_lbl = ttk.Label(self, text="Merge", font=("Segoe UI", 9, "bold"))
        self.merge_lbl.pack(anchor="w", padx=14, pady=(4, 0))
        self.merge_prog_var = tk.DoubleVar(value=0)
        self.merge_prog_bar = ttk.Progressbar(self, variable=self.merge_prog_var, maximum=100,
                                              length=580, style="Merge.Horizontal.TProgressbar")
        self.merge_prog_bar.pack(padx=14, pady=(2, 0))
        self.merge_prog_label = ttk.Label(self, text="", font=("Segoe UI", 9))
        self.merge_prog_label.pack(anchor="w", padx=14)

        # Status / progress
        self.status_var = tk.StringVar(value="")
        self.status_label = ttk.Label(self, textvariable=self.status_var, foreground="#a6e3a1",
                                      wraplength=580, justify="left")
        self.status_label.pack(anchor="w", padx=14, pady=(2, 10))

    # ── Callbacks ────────────────────────────────────────────────────────

    def _on_source_change(self):
        if self.source_var.get() == "youtube":
            self.sp_frame.pack_forget()
            self.yt_frame.pack(fill="x", padx=14, pady=(4, 0), after=self.info_frame)
        else:
            self.yt_frame.pack_forget()
            self.sp_frame.pack(fill="x", padx=14, pady=(4, 0), after=self.info_frame)
        self._clear_preview()

    def _on_format_change(self):
        self._update_size()

    def _clear_preview(self):
        self._video_info = None
        self._thumb_image = None
        self.thumb_label.configure(image="")
        self.info_text.configure(text="")
        self.size_label.configure(text="")

    def _set_busy(self, busy, msg=""):
        self.search_btn.configure(state="disabled" if busy else "normal")
        self.dl_btn.configure(state="disabled" if busy else "normal")
        self.status_var.set(msg)
        if not busy:
            self.video_prog_var.set(0)
            self.video_prog_label.configure(text="")
            self.audio_prog_var.set(0)
            self.audio_prog_label.configure(text="")
            self.merge_prog_var.set(0)
            self.merge_prog_label.configure(text="")
            self._download_index = 0
        self.update_idletasks()

    def _progress_hook(self, d):
        """yt-dlp progress callback — routes to video or audio bar."""
        info = d.get("info_dict") or {}
        vcodec = info.get("vcodec") or "none"
        acodec = info.get("acodec") or "none"
        if vcodec != "none" and acodec == "none":
            target = "video"
        elif acodec != "none" and vcodec == "none":
            target = "audio"
        else:
            target = "video" if getattr(self, "_download_index", 0) == 0 else "audio"

        if d.get("status") == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            downloaded = d.get("downloaded_bytes") or 0
            speed = d.get("speed") or 0
            pct = (downloaded / total * 100) if total > 0 else 0
            txt = f"{_format_size(downloaded)} / {_format_size(total)}  •  {_format_size(speed)}/s" if total else f"{_format_size(downloaded)}  •  {_format_size(speed)}/s"
            self.after(0, self._update_bar, target, pct, txt)
        elif d.get("status") == "finished":
            self.after(0, self._update_bar, target, 100, "Done")
            self._download_index = getattr(self, "_download_index", 0) + 1

    def _update_bar(self, target, pct, text):
        if target == "video":
            self.video_prog_var.set(pct)
            self.video_prog_label.configure(text=text)
        elif target == "audio":
            self.audio_prog_var.set(pct)
            self.audio_prog_label.configure(text=text)
        elif target == "merge":
            self.merge_prog_var.set(pct)
            self.merge_prog_label.configure(text=text)
        self.update_idletasks()

    # ── Search ───────────────────────────────────────────────────────────

    def _on_search(self):
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("No URL", "Please paste a URL first.")
            return
        self._set_busy(True, "Fetching info…")
        threading.Thread(target=self._fetch_info, args=(url,), daemon=True).start()

    def _fetch_info(self, url):
        try:
            if self.source_var.get() == "youtube":
                info = _fetch_youtube_details(url)
                self._video_info = info
                title = info.get("title", "Unknown")
                uploader = info.get("uploader", "")
                duration = _format_duration(info.get("duration"))
                thumb_url = info.get("thumbnail")

                # Load thumbnail
                thumb_img = None
                if thumb_url:
                    try:
                        req = urllib.request.Request(thumb_url, headers={"User-Agent": "Mozilla/5.0"})
                        data = urllib.request.urlopen(req, timeout=10).read()
                        img = Image.open(io.BytesIO(data))
                        img.thumbnail((200, 140))
                        thumb_img = ImageTk.PhotoImage(img)
                    except Exception:
                        thumb_img = None

                size = _estimate_size(info, self.quality_var.get(), self.format_var.get() == "mp4")
                self.after(0, self._show_youtube_info, title, uploader, duration, thumb_img, size)
            else:
                # Spotify
                from spotify_downloader import _parse_spotify_url
                tracks = _parse_spotify_url(url)
                summary = "\n".join(f"  {i}. {t['artist']} – {t['title']}" for i, t in enumerate(tracks, 1))
                text = f"{len(tracks)} track(s) found:\n{summary}"
                self.after(0, self._show_spotify_info, text)
        except Exception as e:
            self.after(0, self._set_busy, False, f"Error: {e}")

    def _show_youtube_info(self, title, uploader, duration, thumb_img, size):
        if thumb_img:
            self._thumb_image = thumb_img
            self.thumb_label.configure(image=thumb_img)
        else:
            self.thumb_label.configure(image="")

        self.info_text.configure(text=f"{title}\n{uploader}\nDuration: {duration}")
        self.size_label.configure(text=f"Estimated size: {_format_size(size)}")
        self._set_busy(False, "Ready")

    def _show_spotify_info(self, text):
        self.thumb_label.configure(image="")
        self._thumb_image = None
        self.info_text.configure(text=text)
        self.size_label.configure(text="")
        self._set_busy(False, "Ready")

    def _update_size(self):
        if self._video_info is None:
            return
        is_video = self.format_var.get() == "mp4"
        size = _estimate_size(self._video_info, self.quality_var.get(), is_video)
        self.size_label.configure(text=f"Estimated size: {_format_size(size)}")

    # ── Download ─────────────────────────────────────────────────────────

    def _on_download(self):
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("No URL", "Please paste a URL first.")
            return
        self._set_busy(True, "Downloading…")
        threading.Thread(target=self._do_download, args=(url,), daemon=True).start()

    def _do_download(self, url):
        try:
            if self.source_var.get() == "youtube":
                quality = self.quality_var.get()
                if self.format_var.get() == "mp4":
                    self._yt_download_video(url, quality)
                else:
                    self._yt_download_audio(url)
                self.after(0, self._set_busy, False, "Download complete! Saved to downloads/")
            else:
                from spotify_downloader import download_track
                fmt = self.sp_format_var.get()
                download_track(url, audio_format=fmt)
                self.after(0, self._set_busy, False, "Download complete! Saved to downloads/")
        except Exception as e:
            self.after(0, self._set_busy, False, f"Error: {e}")

    def _yt_download_video(self, url, quality="best"):
        """Download video with progress hook + merge tracking."""
        os.makedirs("downloads", exist_ok=True)
        self._download_index = 0
        self._merge_stop = threading.Event()
        self._downloaded_bytes = 0  # sum of video+audio raw sizes

        if HAS_FFMPEG:
            fmt = "bestvideo+bestaudio/best"
            if quality != "best":
                fmt = f"bestvideo[height<={quality}]+bestaudio/best[height<={quality}]"
        else:
            fmt = "best" if quality == "best" else f"best[height<={quality}]"

        def _vid_progress(d):
            """Route video/audio to their bars and track total bytes."""
            info = d.get("info_dict") or {}
            vcodec = info.get("vcodec") or "none"
            acodec = info.get("acodec") or "none"
            if vcodec != "none" and acodec == "none":
                target = "video"
            elif acodec != "none" and vcodec == "none":
                target = "audio"
            else:
                target = "video" if self._download_index == 0 else "audio"

            if d.get("status") == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                downloaded = d.get("downloaded_bytes") or 0
                speed = d.get("speed") or 0
                pct = (downloaded / total * 100) if total > 0 else 0
                txt = f"{_format_size(downloaded)} / {_format_size(total)}  •  {_format_size(speed)}/s" if total else f"{_format_size(downloaded)}  •  {_format_size(speed)}/s"
                self.after(0, self._update_bar, target, pct, txt)
            elif d.get("status") == "finished":
                size = d.get("total_bytes") or d.get("total_bytes_estimate") or d.get("downloaded_bytes") or 0
                self._downloaded_bytes += size
                self.after(0, self._update_bar, target, 100, "Done")
                self._download_index += 1

        def _pp_hook(d):
            """Fires when a postprocessor starts/finishes — used to track merge."""
            status = d.get("status")
            pp = d.get("postprocessor")
            if pp == "Merger":
                if status == "started":
                    out_file = d.get("info_dict", {}).get("filepath") or ""
                    expected = self._downloaded_bytes
                    self._merge_stop.clear()
                    threading.Thread(
                        target=self._monitor_merge, args=(out_file, expected), daemon=True
                    ).start()
                elif status == "finished":
                    self._merge_stop.set()
                    self.after(0, self._update_bar, "merge", 100, "Done")

        opts = {
            "format": fmt,
            "outtmpl": os.path.join("downloads", "%(title)s.%(ext)s"),
            "quiet": True,
            "no_warnings": True,
            "progress_hooks": [_vid_progress],
            "postprocessor_hooks": [_pp_hook],
        }
        if HAS_FFMPEG:
            opts["merge_output_format"] = "mp4"
            opts["ffmpeg_location"] = FFMPEG_PATH
            opts["postprocessor_args"] = {"merger": ["-c:v", "copy", "-c:a", "aac", "-b:a", "192k"]}

        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])
        self._merge_stop.set()

    def _monitor_merge(self, out_path, expected_size):
        """Poll the temp file size during ffmpeg merge."""
        import glob

        # yt-dlp writes merge output to a temp file: "Title.temp.mp4"
        # Derive temp path from the final output path
        if out_path:
            base, ext = os.path.splitext(out_path)
            temp_path = f"{base}.temp{ext}"
        else:
            temp_path = ""

        # Find whichever file to monitor: temp file first, then final
        target = ""
        for _ in range(50):
            if self._merge_stop.is_set():
                return
            if temp_path and os.path.exists(temp_path):
                target = temp_path
                break
            # Fallback: look for any .temp.mp4 in downloads/
            temps = glob.glob(os.path.join("downloads", "*.temp.mp4"))
            if temps:
                target = temps[0]
                break
            time.sleep(0.1)

        if not target or not expected_size:
            self.after(0, self._update_bar, "merge", 0, "Merging…")
            while not self._merge_stop.is_set():
                time.sleep(0.2)
            return

        prev_size = 0
        stall_count = 0
        while not self._merge_stop.is_set():
            try:
                current = os.path.getsize(target)
            except OSError:
                current = prev_size  # file may have been renamed (merge done)
            pct = min(current / expected_size * 100, 99) if expected_size > 0 else 0
            txt = f"{_format_size(current)} / ~{_format_size(expected_size)}"
            self.after(0, self._update_bar, "merge", pct, txt)
            if current == prev_size:
                stall_count += 1
            else:
                stall_count = 0
            prev_size = current
            time.sleep(0.15)

    def _yt_download_audio(self, url):
        """Download audio with progress hook."""
        os.makedirs("downloads", exist_ok=True)
        def _audio_hook(d):
            if d.get("status") == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                downloaded = d.get("downloaded_bytes") or 0
                speed = d.get("speed") or 0
                pct = (downloaded / total * 100) if total > 0 else 0
                txt = f"{_format_size(downloaded)} / {_format_size(total)}  •  {_format_size(speed)}/s" if total else f"{_format_size(downloaded)}  •  {_format_size(speed)}/s"
                self.after(0, self._update_bar, "audio", pct, txt)
            elif d.get("status") == "finished":
                self.after(0, self._update_bar, "audio", 100, "Converting…")
        opts = {
            "format": "bestaudio/best",
            "outtmpl": os.path.join("downloads", "%(title)s.%(ext)s"),
            "quiet": True,
            "no_warnings": True,
            "progress_hooks": [_audio_hook],
        }
        if HAS_FFMPEG:
            opts["ffmpeg_location"] = FFMPEG_PATH
            opts["postprocessors"] = [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }]
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])


if __name__ == "__main__":
    App().mainloop()