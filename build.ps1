# Rebuilds app.exe. Always refreshes yt-dlp first: a stale bundled yt-dlp
# causes "HTTP Error 403: Forbidden" once YouTube rotates its player logic.

$ErrorActionPreference = "Stop"

python -m pip install --upgrade pip
python -m pip install --upgrade yt-dlp spotipy imageio-ffmpeg pillow requests pyinstaller

$ytdlp = python -c "import yt_dlp; print(yt_dlp.version.__version__)"
Write-Host "Bundling yt-dlp $ytdlp" -ForegroundColor Cyan

Remove-Item -Recurse -Force build, dist -ErrorAction SilentlyContinue

python -m PyInstaller `
    --noconfirm `
    --onefile `
    --windowed `
    --name app `
    --collect-all yt_dlp `
    --collect-all imageio_ffmpeg `
    --hidden-import requests `
    --hidden-import urllib3 `
    app.py

Copy-Item .\dist\app.exe .\app.exe -Force
Write-Host "Done -> app.exe (yt-dlp $ytdlp)" -ForegroundColor Green
