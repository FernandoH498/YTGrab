import re
import json
import subprocess

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


def download_video(url: str, job_id: str, fmt: str, temp_dir: str, jobs: dict) -> None:
    raise NotImplementedError
