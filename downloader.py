import re
import sys
import shutil
import json
import subprocess
import glob
import os
import contextlib
import threading

_YTDLP = [sys.executable, "-m", "yt_dlp"]


def _find_ffmpeg_dir() -> str | None:
    exe = shutil.which("ffmpeg")
    if exe:
        return os.path.dirname(exe)
    candidate = r"C:\ffmpeg\ffmpeg-8.1.1-essentials_build\bin"
    if os.path.exists(os.path.join(candidate, "ffmpeg.exe")):
        return candidate
    return None


_FFMPEG_DIR = _find_ffmpeg_dir()
_FFMPEG_ARGS = ["--ffmpeg-location", _FFMPEG_DIR] if _FFMPEG_DIR else []
_JS_RUNTIME_ARGS = ["--js-runtimes", "node"]
_EXTRACTOR_ARGS = ["--extractor-args", "youtube:player_client=mweb,android"]
_COOKIES_FILE = "cookies.txt"
def _get_cookies_args() -> list[str]:
    return ["--cookies", _COOKIES_FILE] if os.path.exists(_COOKIES_FILE) else []

YOUTUBE_REGEX = re.compile(
    r"^(https?://)?(www\.)?(youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/)[\w-]+"
)

PROGRESS_REGEX = re.compile(r"\[download\]\s+([\d.]+)%")


def validate_youtube_url(url: str) -> bool:
    return bool(YOUTUBE_REGEX.match(url))


def parse_progress_line(line: str) -> float | None:
    match = PROGRESS_REGEX.search(line)
    if match:
        return float(match.group(1))
    return None


def get_video_info(url: str) -> dict:
    result = subprocess.run(
        [*_YTDLP, *_FFMPEG_ARGS, *_JS_RUNTIME_ARGS, *_EXTRACTOR_ARGS, *_get_cookies_args(), "--dump-json", "--no-playlist", url],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        raise ValueError(result.stderr.strip() or "Failed to fetch video info")
    data = json.loads(result.stdout)
    return {
        "title": data.get("title", "Unknown"),
        "thumbnail": data.get("thumbnail", ""),
    }


def download_video(url: str, job_id: str, fmt: str, temp_dir: str, jobs: dict, lock: "threading.Lock | None" = None) -> None:
    _lock = lock or contextlib.nullcontext()
    out_template = os.path.join(temp_dir, f"{job_id}.%(ext)s")

    cookies_args = _get_cookies_args()
    if fmt == "mp3":
        cmd = [
            *_YTDLP, *_FFMPEG_ARGS, *_JS_RUNTIME_ARGS, *_EXTRACTOR_ARGS, *cookies_args, "--no-playlist", "--newline",
            "--extract-audio", "--audio-format", "mp3", "--audio-quality", "0",
            "-o", out_template, url,
        ]
    else:
        cmd = [
            *_YTDLP, *_FFMPEG_ARGS, *_JS_RUNTIME_ARGS, *_EXTRACTOR_ARGS, *cookies_args, "--no-playlist", "--newline",
            "--format", "bestvideo[ext=mp4][height<=720]+bestaudio/best[height<=720][ext=mp4]/best[ext=mp4]",
            "--merge-output-format", "mp4",
            "-o", out_template, url,
        ]

    with _lock:
        jobs[job_id]["status"] = "downloading"

    try:
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
        )
        for line in proc.stdout:
            progress = parse_progress_line(line)
            if progress is not None:
                with _lock:
                    jobs[job_id]["progress"] = progress
        proc.wait()

        if proc.returncode != 0:
            with _lock:
                jobs[job_id]["status"] = "error"
                jobs[job_id]["error"] = "Download failed. The video may be unavailable or private."
            return

        pattern = os.path.join(temp_dir, f"{job_id}.*")
        files = [f for f in glob.glob(pattern) if not f.endswith(".part")]
        if not files:
            with _lock:
                jobs[job_id]["status"] = "error"
                jobs[job_id]["error"] = "Output file not found after download."
            return

        with _lock:
            jobs[job_id]["filepath"] = files[0]
            jobs[job_id]["progress"] = 100
            jobs[job_id]["status"] = "done"

    except Exception as e:
        with _lock:
            jobs[job_id]["status"] = "error"
            jobs[job_id]["error"] = str(e)
