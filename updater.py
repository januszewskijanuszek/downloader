"""Keeps bundled dependencies current.

YouTube rotates its player logic every few weeks, which makes an older yt-dlp
fail with "HTTP Error 403: Forbidden". A frozen exe cannot pip-install into
itself, so updated wheels are unpacked into a writable `lib/` folder beside the
app and imported ahead of the bundled copies.

Only pure-Python packages can be swapped into a frozen app; anything with a
compiled extension is built against the frozen interpreter's ABI and needs a
rebuild instead.
"""

import hashlib
import importlib
import importlib.abc
import importlib.metadata
import io
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from collections import namedtuple
from importlib.machinery import PathFinder

PYPI_JSON = "https://pypi.org/pypi/{}/json"
TRUSTED_HOST = "https://files.pythonhosted.org/"
IS_FROZEN = getattr(sys, "frozen", False)

Package = namedtuple("Package", "name module pure")

MANAGED = (
    Package("yt-dlp", "yt_dlp", True),
    Package("spotipy", "spotipy", True),
    Package("requests", "requests", True),
    Package("urllib3", "urllib3", True),
    Package("certifi", "certifi", True),
    Package("pillow", "PIL", False),
    Package("imageio-ffmpeg", "imageio_ffmpeg", False),
)

Result = namedtuple("Result", "package current latest url sha256 outdated blocked")


def _app_dir():
    if IS_FROZEN:
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


LIB_DIR = os.path.join(_app_dir(), "lib")


class _UpdatedPackageFinder(importlib.abc.MetaPathFinder):
    """Resolves updated packages from LIB_DIR, outranking the frozen importer."""

    def __init__(self, roots):
        self._roots = roots

    def find_spec(self, fullname, path=None, target=None):
        if fullname.partition(".")[0] not in self._roots:
            return None
        return PathFinder.find_spec(fullname, [LIB_DIR] if path is None else path, target)


def activate():
    """Enable downloaded updates. Must run before the managed packages are imported."""
    if not os.path.isdir(LIB_DIR):
        return
    roots = {
        pkg.module for pkg in MANAGED
        if pkg.module not in sys.modules and os.path.exists(os.path.join(LIB_DIR, pkg.module))
    }
    if roots:
        sys.meta_path.insert(0, _UpdatedPackageFinder(roots))


def installed_version(pkg):
    """Version actually loaded at runtime, or None if the package is absent."""
    try:
        version = getattr(importlib.import_module(pkg.module), "__version__", None)
        if version:
            return str(version)
    except Exception:
        pass
    try:
        return importlib.metadata.version(pkg.name)
    except Exception:
        return None


def _as_tuple(version):
    return tuple(int(n) for n in re.findall(r"\d+", version))


def is_newer(latest, current):
    return _as_tuple(latest) > _as_tuple(current)


def latest_release(name, timeout=15):
    """Return (version, wheel_url, sha256) for the newest release of `name`."""
    req = urllib.request.Request(PYPI_JSON.format(name),
                                 headers={"User-Agent": "clanky-downloader"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.load(resp)

    version = data["info"]["version"]
    for file in data["urls"]:
        if file["packagetype"] == "bdist_wheel" and file["filename"].endswith("-py3-none-any.whl"):
            return version, file["url"], file["digests"]["sha256"]
    return version, None, None


def check_all(progress=None):
    """Query PyPI for every managed package. Returns a list of Result."""
    results = []
    for pkg in MANAGED:
        current = installed_version(pkg)
        if current is None:
            continue
        if progress:
            progress(pkg.name)
        try:
            latest, url, sha256 = latest_release(pkg.name)
        except Exception as e:
            results.append(Result(pkg, current, None, None, None, False, str(e)))
            continue

        outdated = is_newer(latest, current)
        blocked = None
        if outdated and IS_FROZEN and not pkg.pure:
            blocked = "compiled extension - rebuild app.exe to update"
        elif outdated and url is None:
            blocked = "no universal wheel published"
        results.append(Result(pkg, current, latest, url, sha256, outdated, blocked))
    return results


def _download_wheel(url, sha256, timeout=120):
    if not url.startswith(TRUSTED_HOST):
        raise RuntimeError(f"refusing to download from untrusted host: {url}")
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        blob = resp.read()
    if hashlib.sha256(blob).hexdigest() != sha256:
        raise RuntimeError("wheel checksum mismatch - download rejected")
    return blob


def _install_wheel(blob):
    """Unpack a wheel into LIB_DIR, replacing only its own top-level entries."""
    staging = LIB_DIR + ".new"
    shutil.rmtree(staging, ignore_errors=True)
    os.makedirs(staging, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(blob)) as zf:
        zf.extractall(staging)

    os.makedirs(LIB_DIR, exist_ok=True)
    for entry in os.listdir(staging):
        dest = os.path.join(LIB_DIR, entry)
        if os.path.isdir(dest):
            shutil.rmtree(dest, ignore_errors=True)
        elif os.path.exists(dest):
            os.remove(dest)
        shutil.move(os.path.join(staging, entry), dest)
    shutil.rmtree(staging, ignore_errors=True)


def install_all(results, progress=None):
    """Install every updatable result. Returns (updated_names, failures)."""
    pending = [r for r in results if r.outdated and not r.blocked]
    if not pending:
        return [], []

    updated, failures = [], []

    if not IS_FROZEN:
        specs = [f"{r.package.name}=={r.latest}" for r in pending]
        if progress:
            progress(", ".join(r.package.name for r in pending))
        proc = subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", *specs],
                              capture_output=True, text=True)
        if proc.returncode == 0:
            return [r.package.name for r in pending], []
        detail = proc.stderr.strip().splitlines()[-1] if proc.stderr.strip() else "pip failed"
        return [], [("pip", detail)]

    for r in pending:
        if progress:
            progress(r.package.name)
        try:
            _install_wheel(_download_wheel(r.url, r.sha256))
            updated.append(r.package.name)
        except Exception as e:
            failures.append((r.package.name, str(e)))
    return updated, failures


def restart():
    """Relaunch the app so the updated packages are imported."""
    args = [sys.executable] if IS_FROZEN else [sys.executable, os.path.abspath(sys.argv[0])]
    subprocess.Popen(args, cwd=_app_dir())
