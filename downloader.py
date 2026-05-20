import re
import json
import subprocess
import glob
import os
import contextlib
import threading

YOUTUBE_REGEX = re.compile(
    r"^(https?://)?(www\.)?(youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/)[\w-]+"
)

PROGRESS_REGEX = re.compile(r"\[download\]\s+([\d.]+)%")


def validate_youtube_url(url: str) -> bool:
    """Validate if a URL is a YouTube video link (watch, youtu.be, or shorts)."""
    return bool(YOUTUBE_REGEX.match(url))


def parse_progress_line(line: str) -> float | None:
    """Extract download progress percentage from a yt-dlp output line."""
    match = PROGRESS_REGEX.search(line)
    if match:
        return float(match.group(1))
    return None


def get_video_info(url: str) -> dict:
    """Fetch video title and thumbnail URL from YouTube via yt-dlp."""
    result = subprocess.run(
        ["yt-dlp", "--dump-json", "--no-playlist", url],
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
    """Download a YouTube video/audio using yt-dlp, tracking progress in the jobs dict."""
    _lock = lock or contextlib.nullcontext()
    out_template = os.path.join(temp_dir, f"{job_id}.%(ext)s")

    if fmt == "mp3":
        cmd = [
            "yt-dlp", "--no-playlist", "--newline",
            "--extract-audio", "--audio-format", "mp3", "--audio-quality", "0",
            "-o", out_template, url,
        ]
    else:
        cmd = [
            "yt-dlp", "--no-playlist", "--newline",
            "--format", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]",
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
