#!/usr/bin/env python3
"""Link to MP4 - a private, local browser interface for yt-dlp and FFmpeg.

Run this file with Python 3.10+ or use a Start launcher. No web hosting needed.
"""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import hmac
import importlib.metadata
import ipaddress
import json
import os
from pathlib import Path
import platform
import re
import secrets
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unicodedata
import urllib.parse
import urllib.request
import venv
import webbrowser
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

VERSION = "1.0.1"
APP = Path(__file__).resolve().parent
ROOT = APP.parent
RUNTIME = ROOT / ".runtime"
DATA = ROOT / ".data"
TERMINAL = {"complete", "failed", "cancelled", "interrupted"}
ACTIVE = {"starting", "downloading", "merging", "converting", "saving"}
DEPENDENCIES = ["yt-dlp[default]", "imageio-ffmpeg"]
CREATE_FLAGS = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0


def runtime_python():
    return RUNTIME / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def checked_run(args, **kwargs):
    return subprocess.run([str(x) for x in args], check=True, creationflags=CREATE_FLAGS, **kwargs)


def js_runtime():
    """Use a supported, existing JS runtime; never enable remote script downloads."""
    deno = RUNTIME / "tools" / ("deno.exe" if os.name == "nt" else "deno")
    candidates = [("deno", str(deno)), ("deno", shutil.which("deno")), ("node", shutil.which("node"))]
    for name, path in candidates:
        if not path or not Path(path).is_file():
            continue
        try:
            output = checked_run([path, "--version"], capture_output=True, text=True, timeout=8).stdout
            match = re.search(r"(\d+)\.(\d+)\.(\d+)", output)
            minimum = (2, 3, 0) if name == "deno" else (22, 0, 0)
            if match and tuple(map(int, match.groups())) >= minimum:
                return {name: {"path": path}}
        except (OSError, subprocess.SubprocessError):
            continue
    return {}


def fetch_bytes(url, limit):
    req = urllib.request.Request(url, headers={"User-Agent": "LinkToMP4-Setup/1.0"})
    with urllib.request.urlopen(req, timeout=45) as response:
        if not response.url.startswith("https://"):
            raise ValueError("Setup requires HTTPS downloads.")
        data = response.read(limit + 1)
        if len(data) > limit:
            raise ValueError("The setup download exceeded its size limit.")
        return data, response.url


def install_js_runtime():
    if js_runtime():
        return
    machine = platform.machine().lower()
    arch = {"amd64": "x86_64", "x86_64": "x86_64", "arm64": "aarch64", "aarch64": "aarch64"}.get(machine)
    system = {"Windows": "pc-windows-msvc", "Darwin": "apple-darwin", "Linux": "unknown-linux-gnu"}.get(platform.system())
    if not arch or not system:
        raise ValueError("Install Deno 2.3+ from https://deno.com, then restart the app.")
    asset = f"deno-{arch}-{system}.zip"
    base = "https://github.com/denoland/deno/releases/latest/download/"
    print("Installing the JavaScript runtime for YouTube from the official Deno release...")
    checksum, resolved = fetch_bytes(base + asset + ".sha256sum", 4096)
    digest = checksum.decode("ascii").split()[0]
    if not re.fullmatch(r"[a-fA-F0-9]{64}", digest):
        raise ValueError("Invalid Deno download checksum.")
    # Pin the archive to the same release as its checksum, even if 'latest' changes.
    archive_url = resolved.removesuffix(".sha256sum")
    if "release-assets.githubusercontent.com" in urllib.parse.urlparse(archive_url).hostname:
        # GitHub redirects checksum assets to signed URLs; use the official latest
        # archive URL and require the matching SHA-256 before installing anything.
        archive_url = base + asset
    archive, _ = fetch_bytes(archive_url, 150 * 1024 * 1024)
    if not hmac.compare_digest(hashlib.sha256(archive).hexdigest(), digest.lower()):
        raise ValueError("Deno checksum did not match. Please run setup again.")
    import io
    name = "deno.exe" if os.name == "nt" else "deno"
    tools_dir = RUNTIME / "tools"
    tools_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(archive)) as bundle:
        member = bundle.getinfo(name)
        if member.file_size > 250 * 1024 * 1024:
            raise ValueError("Unexpected Deno executable size.")
        target = tools_dir / name
        target.write_bytes(bundle.read(member))
        target.chmod(0o755)
    if not js_runtime():
        raise ValueError("Deno could not start. Install Deno manually and restart.")


def bootstrap(update=False):
    if sys.version_info < (3, 10):
        raise RuntimeError("Python 3.10 or newer is required: https://www.python.org/downloads/")
    python = runtime_python()
    if not python.is_file():
        print("First-time setup: creating the app's private Python environment...")
        venv.EnvBuilder(with_pip=True).create(RUNTIME)
    ready = RUNTIME / "ready.json"
    if update or not ready.exists():
        print("Installing download tools. This needs internet and may take a few minutes.")
        checked_run([python, "-m", "pip", "install", "--disable-pip-version-check", "--upgrade", *DEPENDENCIES])
        checked_run([python, "-c", "import yt_dlp, imageio_ffmpeg; imageio_ffmpeg.get_ffmpeg_exe()"])
        ready.write_text(json.dumps({"installed": time.time()}), encoding="utf-8")
    try:
        install_js_runtime()
    except Exception as exc:
        print(f"\nJavaScript runtime setup needs attention: {exc}\nOther supported sites may still work.\n")
    return python


def validate_url(value):
    if not isinstance(value, str) or not 1 <= len(value) <= 8192:
        raise ValueError("Paste a complete video link.")
    url = value.strip()
    if any(ord(c) < 32 or c in "\\<>" for c in url):
        raise ValueError("That link contains invalid characters.")
    try:
        parsed = urllib.parse.urlsplit(url)
        hostname = parsed.hostname or ""
        port = parsed.port
    except ValueError:
        raise ValueError("That link is not a valid URL.") from None
    if parsed.scheme not in {"https", "http"} or not hostname or parsed.username or parsed.password:
        raise ValueError("Use a public http:// or https:// video link, without a username or password.")
    if port not in {None, 80, 443}:
        raise ValueError("Use a public website link on its normal HTTP or HTTPS port.")
    if hostname.lower() == "localhost" or hostname.lower().endswith((".local", ".localhost", ".internal")):
        raise ValueError("Local network links are not supported.")
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        if "." not in hostname or re.fullmatch(r"[0-9.]+", hostname):
            raise ValueError("Use a public website address.")
    else:
        if not address.is_global:
            raise ValueError("Local and private network links are not supported.")
    return url


def safe_name(value):
    name = unicodedata.normalize("NFKC", str(value or "Video"))
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f\x7f]', "_", name)
    name = re.sub(r"\s+", " ", name).strip(" .")[:110].rstrip(" .") or "Video"
    name = name.encode("utf-8")[:180].decode("utf-8", errors="ignore").rstrip(" .") or "Video"
    if re.fullmatch(r"(?i)(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?", name):
        name = "Video " + name
    return name


def output_folder(value):
    if not isinstance(value, str) or not value.strip() or len(value) > 2048:
        raise ValueError("Choose a download folder.")
    path = Path(value.strip()).expanduser()
    if not path.is_absolute():
        raise ValueError("Enter the full folder path, or use Choose folder.")
    if path.is_file():
        raise ValueError("Choose a folder, not a file.")
    path.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryFile(dir=path):
        pass
    return str(path.resolve())


def format_selector(cap):
    if cap not in {0, 2160, 1440, 1080, 720, 480}:
        raise ValueError("Choose one of the available quality limits.")
    limit = f"[height<=?{cap}]" if cap else ""
    return f"bv*{limit}+ba/b{limit}"


def emit(kind, **fields):
    print(json.dumps({"kind": kind, **fields}, ensure_ascii=True), flush=True)


class QuietLogger:
    def debug(self, message):
        pass

    def warning(self, message):
        pass

    def error(self, message):
        pass


def tool_options():
    import imageio_ffmpeg
    return {
        "quiet": True, "no_warnings": True, "logger": QuietLogger(),
        "noplaylist": True, "cachedir": False, "socket_timeout": 25,
        "retries": 3, "fragment_retries": 3, "concurrent_fragment_downloads": 1,
        "ffmpeg_location": imageio_ffmpeg.get_ffmpeg_exe(),
        "js_runtimes": js_runtime(), "remote_components": set(),
        "overwrites": False, "windowsfilenames": True,
    }


def ensure_single_video(info):
    if not info or info.get("_type") in {"playlist", "multi_video"} or "entries" in info:
        raise ValueError("Paste a link to one video. To download several, paste one video link per line.")
    if info.get("is_live") or info.get("live_status") in {"is_live", "is_upcoming", "post_live"}:
        raise ValueError("Live and upcoming streams are not supported. Try again after the recording is available.")
    if not any(f.get("vcodec") != "none" for f in info.get("formats", [info])):
        raise ValueError("This link does not contain a downloadable video.")


def summarize(info):
    heights = sorted({int(f["height"]) for f in info.get("formats", []) if f.get("height") and f.get("vcodec") != "none"}, reverse=True)
    return {"title": str(info.get("title") or "Video")[:300], "duration": info.get("duration"),
            "platform": str(info.get("extractor_key") or info.get("extractor") or "Website"),
            "heights": heights, "id": str(info.get("id") or "")[:100]}


def inspect_video(url):
    import yt_dlp
    with yt_dlp.YoutubeDL(tool_options()) as ydl:
        info = ydl.extract_info(url, download=False)
        ensure_single_video(info)
        return summarize(info)


def friendly_error(exc):
    message = re.sub(r"\x1b\[[0-9;]*m", "", str(exc)).replace("ERROR: ", "").strip()
    # Keep signed URLs, credentials and local temp paths out of displayed errors.
    message = re.sub(r"https?://\S+", "[link]", message)
    low = message.lower()
    if any(s in low for s in ("sign in", "login", "log in", "private video", "cookies", "403", "401", "bot")):
        return "This site requires access or blocked the request. This version downloads publicly accessible videos and does not import login cookies. Try a public link or the site's own download option."
    if "unsupported url" in low:
        return "This link is not supported by the current download engine. Try the video's own page link, or update the engine in Help."
    if "requested format is not available" in low:
        return "No video matched that quality limit. Try Best available, or update the engine in Help."
    if any(s in low for s in ("no space", "disk full", "not enough space")):
        return "The download drive is full. Free some space or choose another folder, then retry."
    if "drm" in low:
        return "This video is protected with DRM and cannot be downloaded by this app."
    if "timed out" in low:
        return "The site did not respond in time. Check your connection and retry."
    return message[:700] or "The download could not finish. Try again or update the engine in Help."


def run_ffmpeg(source, target, mode, duration, selected, ffmpeg, event=emit):
    video = next((f for f in selected if f.get("vcodec") not in {None, "none"}), {})
    audio = next((f for f in selected if f.get("acodec") not in {None, "none"}), {})
    vcodec, acodec = video.get("vcodec", ""), audio.get("acodec", "")
    # Generic video URLs often have no codec metadata. Inspect the local media
    # with FFmpeg itself, so an already-compatible MP4 is not needlessly encoded.
    probe = subprocess.run([ffmpeg, "-hide_banner", "-nostdin", "-i", str(source)],
                           stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True,
                           errors="replace", timeout=30, creationflags=CREATE_FLAGS)
    video_line = next((line for line in probe.stderr.splitlines() if "Stream #" in line and "Video:" in line), "")
    audio_line = next((line for line in probe.stderr.splitlines() if "Stream #" in line and "Audio:" in line), "")
    actual_video = re.search(r"Video: (\w+)", video_line)
    actual_audio = re.search(r"Audio: (\w+)", audio_line)
    if actual_video:
        vcodec = actual_video[1]
    if actual_audio:
        acodec = actual_audio[1]
    compatible = (vcodec.startswith(("avc1", "h264"))
                  and bool(re.search(r"\byuv420p\b", video_line))
                  and (not audio_line or acodec.startswith(("mp4a", "aac"))))
    transcode = mode == "compatible" and not compatible
    if transcode and (video.get("dynamic_range") not in {None, "SDR"}
                      or any(transfer in video_line for transfer in ("smpte2084", "arib-std-b67"))):
        raise ValueError("This video uses HDR. Choose Preserve quality to keep its colors and avoid an automatic HDR-to-SDR conversion.")
    event("progress", status="converting" if transcode else "saving", percent=0, detail="Converting to H.264 + AAC" if transcode else "Packing MP4 without re-encoding")
    args = [ffmpeg, "-hide_banner", "-nostdin", "-loglevel", "error", "-n", "-i", str(source),
            "-map", "0:v:0", "-map", "0:a:0?", "-sn", "-dn"]
    if transcode:
        args += ["-c:v", "libx264", "-crf", "18", "-preset", "medium", "-pix_fmt", "yuv420p",
                 "-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2", "-c:a", "aac", "-b:a", "192k"]
    else:
        args += ["-c", "copy"]
    args += ["-movflags", "+faststart", "-progress", "pipe:1", str(target)]
    with tempfile.TemporaryFile(mode="w+", encoding="utf-8") as errors:
        proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=errors, text=True, creationflags=CREATE_FLAGS)
        for line in proc.stdout:
            if line.startswith("out_time_us=") and duration:
                try:
                    percent = min(99, max(0, int(line.split("=", 1)[1]) / (duration * 10000)))
                    event("progress", status="converting" if transcode else "saving", percent=percent)
                except ValueError:
                    pass
        code = proc.wait()
        proc.stdout.close()
        if code:
            errors.seek(0)
            error = errors.read(8000)
            if "space" in error.lower():
                raise RuntimeError("The download drive has no space left.")
            if mode == "preserve":
                raise ValueError("These streams could not be packed into MP4 without conversion. Retry with Compatible MP4. Conversion can change quality.")
            raise RuntimeError("FFmpeg could not convert this video. Try Preserve quality or another link.")
    if not target.exists() or target.stat().st_size < 100:
        raise ValueError("The video output was empty; no file was marked as complete.")
    return transcode


def publish_file(source, folder, title, event=emit):
    """Never replace an existing file, including a same-named file from outside the app."""
    stem = safe_name(title)
    for number in range(1, 10000):
        name = f"{stem}{f' ({number})' if number > 1 else ''}.mp4"
        target = folder / name
        try:
            if os.name == "nt":
                os.rename(source, target)  # Windows rename fails if the target exists.
            else:
                os.link(source, target)    # Atomic, no-overwrite publication on POSIX.
                source.unlink()
            return target
        except FileExistsError:
            continue
        except OSError as exc:
            # Some external drives do not support hard links. Reserve exclusively,
            # report ownership before copying so cancellation can remove this file.
            if os.name == "nt" or exc.errno not in {1, 18, 38, 95}:
                raise
            try:
                with target.open("xb") as dest:
                    event("owned_output", path=str(target))
                    try:
                        with source.open("rb") as original:
                            shutil.copyfileobj(original, dest, 1024 * 1024)
                        dest.flush()
                        os.fsync(dest.fileno())
                    except BaseException:
                        target.unlink(missing_ok=True)
                        raise
                source.unlink()
                return target
            except FileExistsError:
                continue
    raise ValueError("Too many files have the same name. Choose another folder.")


def download_video(job, event=emit):
    import yt_dlp
    folder = Path(job["folder"])
    work = folder / f".link-to-mp4-{job['id']}"
    work.mkdir(exist_ok=False)
    last = [0.0]
    opts = tool_options()

    def progress(data):
        if data["status"] == "downloading" and time.monotonic() - last[0] >= 0.25:
            last[0] = time.monotonic()
            total = data.get("total_bytes") or data.get("total_bytes_estimate") or 0
            downloaded = data.get("downloaded_bytes") or 0
            info = data.get("info_dict") or {}
            component = "Audio" if info.get("vcodec") == "none" else "Video"
            event("progress", status="downloading", percent=min(99, downloaded / total * 100) if total else None,
                  downloaded=downloaded, total=total, speed=data.get("speed"), eta=data.get("eta"), detail=f"{component} stream")
        elif data["status"] == "finished":
            event("progress", status="merging", percent=None, detail="Preparing downloaded streams")

    opts.update({"format": format_selector(job["cap"]), "merge_output_format": "mkv",
                 "outtmpl": str(work / "source.%(ext)s"), "progress_hooks": [progress]})
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(job["url"], download=False)
            ensure_single_video(info)
            event("metadata", **summarize(info))
            # Download this already-resolved video without a second page request.
            ydl.process_ie_result(info, download=True)
        sources = [p for p in work.glob("source.*") if p.is_file() and p.suffix not in {".part", ".ytdl", ".temp"}]
        source = work / "source.mkv"
        if not source.exists():
            if len(sources) != 1:
                raise ValueError("The audio and video streams could not be combined. Update the engine and try again.")
            source = sources[0]
        prepared = work / "finished.mp4"
        selected = info.get("requested_formats") or [info]
        transcoded = run_ffmpeg(source, prepared, job["mode"], info.get("duration"), selected, opts["ffmpeg_location"], event)
        final = publish_file(prepared, folder, info.get("title") or "Video", event)
        event("complete", path=str(final), size=final.stat().st_size, transcoded=transcoded,
              title=info.get("title") or "Video", percent=100)
    finally:
        shutil.rmtree(work, ignore_errors=True)


def spawn_worker(mode, payload):
    kwargs = {"creationflags": CREATE_FLAGS} if os.name == "nt" else {"start_new_session": True}
    process = subprocess.Popen([sys.executable, str(APP / "app.py"), mode],
                               stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                               text=True, encoding="utf-8", **kwargs)
    process.stdin.write(json.dumps(payload) + "\n")
    process.stdin.close()
    return process


def stop_process(process):
    if process.poll() is not None:
        return
    with contextlib.suppress(OSError, subprocess.SubprocessError):
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                           capture_output=True, timeout=15, creationflags=CREATE_FLAGS)
        else:
            os.killpg(process.pid, signal.SIGTERM)
        try:
            process.wait(timeout=4)
        except subprocess.TimeoutExpired:
            if os.name != "nt":
                os.killpg(process.pid, signal.SIGKILL)
            else:
                process.kill()


class Manager:
    def __init__(self, data_dir=DATA):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.state_file = self.data_dir / "state.json"
        self.lock = threading.RLock()
        self.jobs = []
        self.folder = str(Path.home() / "Downloads" / "Link to MP4")
        self.paused = False
        self.closing = False
        self.process = None
        self.active_id = None
        self.maintenance = None
        self.inspect_lock = threading.Lock()
        self.runtime = js_runtime()
        if self.state_file.exists():
            try:
                saved = json.loads(self.state_file.read_text(encoding="utf-8"))
                self.folder = saved.get("folder", self.folder)
                self.jobs = saved.get("jobs", [])[-200:]
                self.paused = bool(saved.get("paused"))
                for job in self.jobs:
                    if job["status"] not in TERMINAL:
                        job.update(status="interrupted", error="The helper stopped before this job finished. Retry to start again.")
                        self.cleanup(job)
            except (OSError, ValueError, KeyError, TypeError):
                self.jobs = []
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()

    def save(self):
        with self.lock:
            tmp = self.state_file.with_suffix(".tmp")
            tmp.write_text(json.dumps({"folder": self.folder, "paused": self.paused, "jobs": self.jobs}, ensure_ascii=True), encoding="utf-8")
            os.replace(tmp, self.state_file)

    def state(self):
        with self.lock:
            return {"version": VERSION, "folder": self.folder, "jobs": json.loads(json.dumps(self.jobs)),
                    "paused": self.paused, "maintenance": self.maintenance, "js_ready": bool(self.runtime),
                    "engine": importlib.metadata.version("yt-dlp")}

    def add(self, payload):
        urls = payload.get("urls")
        if not isinstance(urls, list) or not 1 <= len(urls) <= 50:
            raise ValueError("Add 1–50 video links at a time, one per line.")
        urls = list(dict.fromkeys(validate_url(u) for u in urls))
        mode, cap = payload.get("mode", "preserve"), payload.get("cap", 0)
        if mode not in {"preserve", "compatible"} or type(cap) is not int:
            raise ValueError("Choose a valid output option.")
        format_selector(cap)
        folder = output_folder(payload.get("folder", self.folder))
        with self.lock:
            if self.maintenance and self.maintenance.get("running"):
                raise ValueError("Wait for the engine update to finish.")
            if sum(j["status"] not in TERMINAL for j in self.jobs) + len(urls) > 50:
                raise ValueError("The queue can hold 50 unfinished videos. Let some finish first.")
            self.folder = folder
            ids = []
            for url in urls:
                job = {"id": secrets.token_hex(8), "url": url, "folder": folder, "mode": mode, "cap": cap,
                       "title": urllib.parse.urlsplit(url).hostname, "status": "queued", "percent": 0,
                       "created": time.time(), "error": ""}
                self.jobs.append(job)
                ids.append(job["id"])
            while len(self.jobs) > 200:
                oldest_finished = next((j for j in self.jobs if j["status"] in TERMINAL), None)
                if oldest_finished is None:
                    break
                self.jobs.remove(oldest_finished)
            self.save()
            return {"added": len(ids), "ids": ids}

    def get_job(self, identifier):
        job = next((j for j in self.jobs if j["id"] == identifier), None)
        if not job:
            raise ValueError("That queue item no longer exists.")
        return job

    def cancel(self, identifier):
        with self.lock:
            job = self.get_job(identifier)
            if job["status"] in TERMINAL:
                return
            job["cancel_requested"] = True
            if job["status"] == "queued":
                job["status"] = "cancelled"
            proc = self.process if self.active_id == identifier else None
            self.save()
        if proc:
            stop_process(proc)

    def retry(self, identifier):
        with self.lock:
            job = self.get_job(identifier)
            if job["status"] not in {"failed", "cancelled", "interrupted"}:
                raise ValueError("Only failed or cancelled items can be retried.")
            payload = {"urls": [job["url"]], "folder": job["folder"], "mode": job["mode"], "cap": job["cap"]}
            result = self.add(payload)
            self.jobs.remove(job)
            self.save()
            return result

    def cleanup(self, job):
        # Only remove paths owned by this exact job; never remove a completed video.
        if re.fullmatch(r"[0-9a-f]{16}", job.get("id", "")):
            shutil.rmtree(Path(job["folder"]) / f".link-to-mp4-{job['id']}", ignore_errors=True)
        owned = job.get("owned_output")
        if owned and job.get("status") != "complete":
            path = Path(owned)
            if path.parent == Path(job["folder"]) and path.suffix == ".mp4":
                with contextlib.suppress(OSError):
                    path.unlink(missing_ok=True)

    def run(self):
        while not self.closing:
            with self.lock:
                job = next((j for j in self.jobs if j["status"] == "queued"), None)
                if self.paused or (self.maintenance and self.maintenance.get("running")):
                    job = None
                if job:
                    job["status"] = "starting"
                    self.active_id = job["id"]
                    self.save()
            if not job:
                time.sleep(0.25)
                continue
            try:
                proc = spawn_worker("--worker", job)
                with self.lock:
                    self.process = proc
                    cancelled = job.get("cancel_requested") or self.closing
                if cancelled:
                    stop_process(proc)
                for line in proc.stdout:
                    try:
                        event = json.loads(line)
                    except ValueError:
                        continue
                    with self.lock:
                        kind = event.pop("kind", None)
                        if kind == "complete":
                            job.update(event, status="complete", finished=time.time(), error="")
                            job.pop("owned_output", None)
                        elif kind == "owned_output":
                            job["owned_output"] = event["path"]
                            self.save()
                        elif kind == "error":
                            job.update(status="failed", error=event["message"])
                        elif kind in {"progress", "metadata"}:
                            job.update(event)
                code = proc.wait()
                proc.stdout.close()
                with self.lock:
                    if job["status"] != "complete":
                        if job.get("cancel_requested"):
                            job.update(status="cancelled", error="Cancelled. Retry starts a fresh download.")
                        elif job["status"] != "failed":
                            job.update(status="failed", error=f"The download helper stopped unexpectedly (code {code}). Retry or update the engine.")
            except Exception as exc:
                with self.lock:
                    job.update(status="failed", error=friendly_error(exc))
            finally:
                with self.lock:
                    self.cleanup(job)
                    self.process, self.active_id = None, None
                    self.save()

    def inspect(self, url):
        url = validate_url(url)
        if self.maintenance and self.maintenance.get("running"):
            raise ValueError("Wait for the engine update to finish before checking a link.")
        if not self.inspect_lock.acquire(blocking=False):
            raise ValueError("A link check is already running. Please wait.")
        proc = None
        try:
            proc = spawn_worker("--inspect", {"url": url})
            # stdin has already been closed; communicate must not try to flush it.
            proc.stdin = None
            out, _ = proc.communicate(timeout=110)
            for line in reversed(out.splitlines()):
                try:
                    event = json.loads(line)
                except ValueError:
                    continue
                if event.get("kind") == "metadata":
                    return event
                if event.get("kind") == "error":
                    raise ValueError(event["message"])
            raise ValueError("The site returned no video information. Try another link or update the engine.")
        except subprocess.TimeoutExpired:
            stop_process(proc)
            raise ValueError("Checking this link took too long. Try again later.") from None
        finally:
            self.inspect_lock.release()

    def update(self):
        with self.lock:
            if self.inspect_lock.locked():
                raise ValueError("Wait for the link check to finish before updating.")
            if any(j["status"] not in TERMINAL for j in self.jobs):
                raise ValueError("Finish or cancel the queue before updating the engine.")
            if self.maintenance and self.maintenance.get("running"):
                raise ValueError("An update is already running.")
            self.maintenance = {"running": True, "message": "Updating download tools…"}
        def work():
            try:
                checked_run([sys.executable, "-m", "pip", "install", "--disable-pip-version-check", "--upgrade", *DEPENDENCIES], capture_output=True, timeout=600)
                install_js_runtime()
                self.runtime = js_runtime()
                self.maintenance = {"running": False, "message": "The download engine is up to date."}
            except Exception:
                self.maintenance = {"running": False, "message": "Update could not finish. Check your internet, close the app, and run your Start launcher with --update. See README."}
        threading.Thread(target=work, daemon=True).start()

    def close(self):
        self.closing = True
        with self.lock:
            proc = self.process
            if self.active_id:
                self.get_job(self.active_id)["cancel_requested"] = True
        if proc:
            stop_process(proc)
        self.thread.join(timeout=6)
        self.save()


def open_folder(path):
    path = str(Path(path).resolve())
    if not Path(path).is_dir():
        raise ValueError("That folder no longer exists.")
    if os.name == "nt":
        os.startfile(path)
    elif sys.platform == "darwin":
        subprocess.Popen(["open", path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        subprocess.Popen(["xdg-open", path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def make_handler(manager, token):
    class Handler(BaseHTTPRequestHandler):
        server_version = "LinkToMP4"

        def log_message(self, *_):
            pass

        def allowed(self, authenticated=True):
            origin = f"http://127.0.0.1:{self.server.server_port}"
            if self.headers.get("Host") != urllib.parse.urlsplit(origin).netloc:
                return False
            if self.headers.get("Origin") not in {None, origin}:
                return False
            if self.headers.get("Sec-Fetch-Site") == "cross-site":
                return False
            return not authenticated or hmac.compare_digest(self.headers.get("X-App-Token", ""), token)

        def send(self, status, value, html=False):
            body = value if isinstance(value, bytes) else json.dumps(value, ensure_ascii=True).encode()
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8" if html else "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
            self.end_headers()
            with contextlib.suppress(BrokenPipeError, ConnectionResetError):
                self.wfile.write(body)

        def do_GET(self):
            if not self.allowed(authenticated=self.path != "/"):
                return self.send(403, {"error": "Open the app from its Start launcher to connect securely."})
            if self.path == "/":
                return self.send(200, (APP / "index.html").read_bytes(), html=True)
            if self.path == "/api/state":
                return self.send(200, manager.state())
            self.send(404, {"error": "Not found"})

        def do_POST(self):
            if not self.allowed():
                return self.send(403, {"error": "Open the app from its Start launcher to reconnect."})
            try:
                if self.headers.get("Content-Type", "").split(";")[0] != "application/json":
                    raise ValueError("A JSON request is required.")
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 < size <= 512000:
                    raise ValueError("Request is empty or too large.")
                payload = json.loads(self.rfile.read(size))
                if not isinstance(payload, dict):
                    raise ValueError("Invalid request.")
                route = self.path
                result = {"ok": True}
                if route == "/api/add":
                    result = manager.add(payload)
                elif route == "/api/inspect":
                    result = manager.inspect(payload.get("url"))
                elif route == "/api/cancel":
                    manager.cancel(payload.get("id"))
                elif route == "/api/retry":
                    result = manager.retry(payload.get("id"))
                elif route == "/api/pause":
                    with manager.lock:
                        manager.paused = bool(payload.get("paused"))
                        manager.save()
                elif route == "/api/clear":
                    with manager.lock:
                        manager.jobs = [j for j in manager.jobs if j["status"] not in TERMINAL]
                        manager.save()
                elif route == "/api/folder":
                    folder = output_folder(payload.get("folder"))
                    with manager.lock:
                        manager.folder = folder
                        manager.save()
                    result = {"folder": folder}
                elif route == "/api/choose-folder":
                    try:
                        picked = checked_run([sys.executable, str(APP / "app.py"), "--pick-folder"], capture_output=True, text=True, timeout=150).stdout.strip()
                    except Exception:
                        raise ValueError("The folder picker is unavailable. Paste the full folder path into Save to instead.") from None
                    if picked:
                        manager.folder = output_folder(picked)
                        manager.save()
                    result = {"folder": manager.folder, "cancelled": not bool(picked)}
                elif route == "/api/open-folder":
                    if payload.get("id"):
                        with manager.lock:
                            folder = manager.get_job(payload["id"])["folder"]
                    else:
                        folder = manager.folder
                    open_folder(folder)
                elif route == "/api/update":
                    manager.update()
                elif route == "/api/shutdown":
                    self.send(200, {"ok": True})
                    threading.Thread(target=self.server.shutdown, daemon=True).start()
                    return
                else:
                    return self.send(404, {"error": "Not found"})
                self.send(200, result)
            except (ValueError, OSError, KeyError, TypeError) as exc:
                self.send(400, {"error": friendly_error(exc)})
            except Exception:
                self.send(500, {"error": "The local helper could not complete that action. Check its console or restart the app."})
    return Handler


def main():
    parser = argparse.ArgumentParser(description="Link to MP4 - local video downloader")
    parser.add_argument("--ready", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--inspect", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--pick-folder", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--no-browser", action="store_true", help="Show the local address without opening a browser")
    parser.add_argument("--update", action="store_true", help="Update the local download tools before starting")
    args = parser.parse_args()
    if args.pick_folder:
        import tkinter
        from tkinter import filedialog
        root = tkinter.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        folder = filedialog.askdirectory(title="Choose where to save your videos", mustexist=True)
        root.destroy()
        print(folder)
        return
    if args.worker or args.inspect:
        try:
            payload = json.loads(sys.stdin.readline())
            if args.inspect:
                emit("metadata", **inspect_video(payload["url"]))
            else:
                download_video(payload)
        except Exception as exc:
            emit("error", message=friendly_error(exc))
            sys.exit(1)
        return
    if not args.ready:
        python = bootstrap(args.update)
        command = [str(python), str(APP / "app.py"), "--ready"]
        if args.no_browser:
            command.append("--no-browser")
        sys.exit(subprocess.call(command))
    # A stable port also prevents two app instances from modifying the queue.
    port = 8765
    server = ThreadingHTTPServer(("127.0.0.1", port), BaseHTTPRequestHandler, bind_and_activate=False)
    try:
        server.server_bind()
        server.server_activate()
    except OSError:
        print("\nLink to MP4 could not start: port 8765 is already in use.\nClose the other app/helper window, then run Start again.")
        server.server_close()
        return
    manager = Manager()
    token = secrets.token_urlsafe(32)
    server.RequestHandlerClass = make_handler(manager, token)
    url = f"http://127.0.0.1:{port}/#{token}"
    print(f"\nLink to MP4 {VERSION}\nOpen this address in your browser:\n{url}\n\nKeep this window open. Ctrl+C or Exit helper in Help stops the app.\n")
    if not args.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever(poll_interval=0.3)
    except KeyboardInterrupt:
        pass
    finally:
        manager.close()
        server.server_close()
        print("Link to MP4 stopped.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"\nCould not start Link to MP4: {exc}\nSee README.md for setup help.")
        sys.exit(1)
