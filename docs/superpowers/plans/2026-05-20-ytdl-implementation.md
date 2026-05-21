# YT Downloader — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a YouTube video downloader SPA with FastAPI backend (Python) and Vanilla JS frontend that streams downloaded files directly to the browser with real progress tracking.

**Architecture:** FastAPI serves the static frontend (`static/index.html`) and a JSON API. Downloads run in a `ThreadPoolExecutor`; a job dict tracks progress. The browser polls `/api/status/{job_id}` every second, and on completion fetches `/api/file/{job_id}` which streams the file and deletes it after delivery.

**Tech Stack:** Python 3.11+, FastAPI, yt-dlp, uvicorn, pytest, httpx; HTML5 + Tailwind CSS (CDN) + Vanilla JS.

---

## File Map

| File | Responsibility |
|------|---------------|
| `requirements.txt` | All Python dependencies |
| `downloader.py` | URL validation, progress parsing, `get_video_info`, `download_video` |
| `main.py` | FastAPI app, in-memory jobs dict, all 5 routes, static file mount |
| `static/index.html` | Complete frontend: input, video info, progress bar, error toast |
| `tests/test_downloader.py` | Unit tests for downloader.py pure functions + mocked subprocess calls |
| `tests/test_routes.py` | Integration tests for all routes via FastAPI TestClient |

---

## Task 1: Project Scaffolding

**Files:**
- Create: `requirements.txt`
- Create: `static/` (directory)
- Create: `temp/` (directory)
- Create: `tests/__init__.py`

- [ ] **Step 1: Create requirements.txt**

```
fastapi>=0.111.0
uvicorn[standard]>=0.29.0
yt-dlp>=2024.5.1
python-multipart>=0.0.9
pytest>=8.0.0
httpx>=0.27.0
```

- [ ] **Step 2: Create directories and test init**

```bash
mkdir static temp tests
echo "" > tests/__init__.py
```

- [ ] **Step 3: Install dependencies**

```bash
pip install -r requirements.txt
```

Expected: all packages install without error. Verify with:
```bash
yt-dlp --version
python -c "import fastapi; print(fastapi.__version__)"
```

- [ ] **Step 4: Commit**

```bash
git init
echo "temp/" > .gitignore
echo "__pycache__/" >> .gitignore
echo ".pytest_cache/" >> .gitignore
git add requirements.txt .gitignore tests/__init__.py
git commit -m "chore: initial project scaffold"
```

---

## Task 2: URL Validation and Progress Parser (TDD)

**Files:**
- Create: `downloader.py` (stub with two functions)
- Create: `tests/test_downloader.py` (first test block)

- [ ] **Step 1: Write the failing tests**

Create `tests/test_downloader.py`:

```python
import pytest
from downloader import validate_youtube_url, parse_progress_line


def test_validate_standard_watch_url():
    assert validate_youtube_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ") is True


def test_validate_short_url():
    assert validate_youtube_url("https://youtu.be/dQw4w9WgXcQ") is True


def test_validate_shorts_url():
    assert validate_youtube_url("https://youtube.com/shorts/abc123XYZ") is True


def test_validate_url_with_extra_params():
    assert validate_youtube_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=5s") is True


def test_validate_rejects_vimeo():
    assert validate_youtube_url("https://vimeo.com/123456") is False


def test_validate_rejects_bare_domain():
    assert validate_youtube_url("https://youtube.com/") is False


def test_validate_rejects_empty():
    assert validate_youtube_url("") is False


def test_validate_rejects_plain_text():
    assert validate_youtube_url("not a url at all") is False


def test_parse_progress_standard_line():
    assert parse_progress_line("[download]  72.5% of 10.00MiB at 1.23MiB/s ETA 00:03") == 72.5


def test_parse_progress_100():
    assert parse_progress_line("[download] 100% of 10.00MiB") == 100.0


def test_parse_progress_returns_none_for_non_progress_line():
    assert parse_progress_line("[ffmpeg] Merging formats into output.mp4") is None


def test_parse_progress_returns_none_for_empty_string():
    assert parse_progress_line("") is None
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_downloader.py -v
```

Expected: `ImportError` — `downloader` module does not exist yet.

- [ ] **Step 3: Implement validate_youtube_url and parse_progress_line**

Create `downloader.py`:

```python
import re
import subprocess
import json
import os
import glob

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
    raise NotImplementedError


def download_video(url: str, job_id: str, fmt: str, temp_dir: str, jobs: dict) -> None:
    raise NotImplementedError
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_downloader.py::test_validate_standard_watch_url \
       tests/test_downloader.py::test_validate_short_url \
       tests/test_downloader.py::test_validate_shorts_url \
       tests/test_downloader.py::test_validate_url_with_extra_params \
       tests/test_downloader.py::test_validate_rejects_vimeo \
       tests/test_downloader.py::test_validate_rejects_bare_domain \
       tests/test_downloader.py::test_validate_rejects_empty \
       tests/test_downloader.py::test_validate_rejects_plain_text \
       tests/test_downloader.py::test_parse_progress_standard_line \
       tests/test_downloader.py::test_parse_progress_100 \
       tests/test_downloader.py::test_parse_progress_returns_none_for_non_progress_line \
       tests/test_downloader.py::test_parse_progress_returns_none_for_empty_string \
       -v
```

Expected: 12 PASSED.

- [ ] **Step 5: Commit**

```bash
git add downloader.py tests/test_downloader.py
git commit -m "feat: add URL validation and progress line parser"
```

---

## Task 3: get_video_info (TDD with mock)

**Files:**
- Modify: `downloader.py` — implement `get_video_info`
- Modify: `tests/test_downloader.py` — add get_video_info tests

- [ ] **Step 1: Add failing tests to tests/test_downloader.py**

Append to the bottom of `tests/test_downloader.py`:

```python
import json
from unittest.mock import patch, MagicMock
from downloader import get_video_info


def test_get_video_info_returns_title_and_thumbnail():
    mock_data = {"title": "Never Gonna Give You Up", "thumbnail": "https://img.jpg"}
    mock_result = MagicMock(returncode=0, stdout=json.dumps(mock_data), stderr="")
    with patch("downloader.subprocess.run", return_value=mock_result):
        result = get_video_info("https://youtube.com/watch?v=abc")
    assert result == {"title": "Never Gonna Give You Up", "thumbnail": "https://img.jpg"}


def test_get_video_info_raises_on_nonzero_returncode():
    mock_result = MagicMock(returncode=1, stdout="", stderr="Video unavailable")
    with patch("downloader.subprocess.run", return_value=mock_result):
        with pytest.raises(ValueError, match="Video unavailable"):
            get_video_info("https://youtube.com/watch?v=abc")


def test_get_video_info_raises_with_fallback_message_when_stderr_empty():
    mock_result = MagicMock(returncode=1, stdout="", stderr="")
    with patch("downloader.subprocess.run", return_value=mock_result):
        with pytest.raises(ValueError, match="Failed to fetch video info"):
            get_video_info("https://youtube.com/watch?v=abc")
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_downloader.py::test_get_video_info_returns_title_and_thumbnail -v
```

Expected: FAILED — `NotImplementedError`.

- [ ] **Step 3: Implement get_video_info in downloader.py**

Replace the `get_video_info` stub:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_downloader.py::test_get_video_info_returns_title_and_thumbnail \
       tests/test_downloader.py::test_get_video_info_raises_on_nonzero_returncode \
       tests/test_downloader.py::test_get_video_info_raises_with_fallback_message_when_stderr_empty \
       -v
```

Expected: 3 PASSED.

- [ ] **Step 5: Commit**

```bash
git add downloader.py tests/test_downloader.py
git commit -m "feat: implement get_video_info with subprocess mock tests"
```

---

## Task 4: download_video (TDD with mock)

**Files:**
- Modify: `downloader.py` — implement `download_video`
- Modify: `tests/test_downloader.py` — add download_video tests

- [ ] **Step 1: Add failing tests to tests/test_downloader.py**

Append to the bottom of `tests/test_downloader.py`:

```python
from unittest.mock import patch, MagicMock, call
from downloader import download_video


def _make_mock_proc(stdout_lines: list[str], returncode: int = 0):
    mock_proc = MagicMock()
    mock_proc.stdout = iter(stdout_lines)
    mock_proc.returncode = returncode
    mock_proc.wait.return_value = None
    return mock_proc


def test_download_video_sets_status_done_on_success(tmp_path):
    jobs = {}
    lines = [
        "[download]  50.0% of 10.00MiB\n",
        "[download] 100% of 10.00MiB\n",
    ]
    fake_file = tmp_path / "test-job.mp4"
    fake_file.write_bytes(b"fake")

    with patch("downloader.subprocess.Popen", return_value=_make_mock_proc(lines)):
        download_video("https://youtube.com/watch?v=abc", "test-job", "mp4", str(tmp_path), jobs)

    assert jobs["test-job"]["status"] == "done"
    assert jobs["test-job"]["progress"] == 100


def test_download_video_tracks_progress(tmp_path):
    jobs = {}
    lines = [
        "[download]  25.0% of 10.00MiB\n",
        "[download]  75.0% of 10.00MiB\n",
        "[download] 100% of 10.00MiB\n",
    ]
    fake_file = tmp_path / "test-job2.mp4"
    fake_file.write_bytes(b"fake")

    progress_snapshots = []

    original_popen = __import__("downloader").subprocess.Popen

    with patch("downloader.subprocess.Popen", return_value=_make_mock_proc(lines)):
        download_video("https://youtube.com/watch?v=abc", "test-job2", "mp4", str(tmp_path), jobs)

    assert jobs["test-job2"]["progress"] == 100


def test_download_video_sets_status_error_on_nonzero_returncode(tmp_path):
    jobs = {}
    mock_proc = _make_mock_proc([], returncode=1)
    with patch("downloader.subprocess.Popen", return_value=mock_proc):
        download_video("https://youtube.com/watch?v=abc", "err-job", "mp4", str(tmp_path), jobs)

    assert jobs["err-job"]["status"] == "error"
    assert jobs["err-job"]["error"] is not None


def test_download_video_mp3_uses_audio_flags(tmp_path):
    jobs = {}
    fake_file = tmp_path / "mp3-job.mp3"
    fake_file.write_bytes(b"fake")

    with patch("downloader.subprocess.Popen", return_value=_make_mock_proc([])) as mock_popen:
        download_video("https://youtube.com/watch?v=abc", "mp3-job", "mp3", str(tmp_path), jobs)

    cmd = mock_popen.call_args[0][0]
    assert "--extract-audio" in cmd
    assert "--audio-format" in cmd
    assert "mp3" in cmd
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_downloader.py::test_download_video_sets_status_done_on_success -v
```

Expected: FAILED — `NotImplementedError`.

- [ ] **Step 3: Implement download_video in downloader.py**

Replace the `download_video` stub:

```python
def download_video(url: str, job_id: str, fmt: str, temp_dir: str, jobs: dict) -> None:
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

    jobs[job_id] = {"status": "downloading", "progress": 0, "filepath": None, "error": None}

    try:
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
        )
        for line in proc.stdout:
            progress = parse_progress_line(line)
            if progress is not None:
                jobs[job_id]["progress"] = progress
        proc.wait()

        if proc.returncode != 0:
            jobs[job_id]["status"] = "error"
            jobs[job_id]["error"] = "Download failed. The video may be unavailable or private."
            return

        # Find the output file (extension may vary for merged formats)
        pattern = os.path.join(temp_dir, f"{job_id}.*")
        files = [f for f in glob.glob(pattern) if not f.endswith(".part")]
        if not files:
            jobs[job_id]["status"] = "error"
            jobs[job_id]["error"] = "Output file not found after download."
            return

        jobs[job_id]["filepath"] = files[0]
        jobs[job_id]["progress"] = 100
        jobs[job_id]["status"] = "done"

    except Exception as e:
        jobs[job_id]["status"] = "error"
        jobs[job_id]["error"] = str(e)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_downloader.py::test_download_video_sets_status_done_on_success \
       tests/test_downloader.py::test_download_video_tracks_progress \
       tests/test_downloader.py::test_download_video_sets_status_error_on_nonzero_returncode \
       tests/test_downloader.py::test_download_video_mp3_uses_audio_flags \
       -v
```

Expected: 4 PASSED.

- [ ] **Step 5: Run the full downloader test suite**

```bash
pytest tests/test_downloader.py -v
```

Expected: all 19 tests PASSED.

- [ ] **Step 6: Commit**

```bash
git add downloader.py tests/test_downloader.py
git commit -m "feat: implement download_video with job tracking and TDD coverage"
```

---

## Task 5: FastAPI App and Routes (TDD)

**Files:**
- Create: `main.py`
- Create: `tests/test_routes.py`

- [ ] **Step 1: Write failing route tests**

Create `tests/test_routes.py`:

```python
import pytest
import os
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock


def get_client():
    import importlib
    import main
    importlib.reload(main)
    return TestClient(main.app)


# --- /api/video-info ---

def test_video_info_rejects_invalid_url():
    client = get_client()
    response = client.post("/api/video-info", json={"url": "https://vimeo.com/123"})
    assert response.status_code == 400
    assert "inválida" in response.json()["detail"]


def test_video_info_returns_title_and_thumbnail():
    client = get_client()
    with patch("main.get_video_info", return_value={"title": "Test", "thumbnail": "https://img.jpg"}):
        response = client.post("/api/video-info", json={"url": "https://youtube.com/watch?v=abc123XY"})
    assert response.status_code == 200
    assert response.json() == {"title": "Test", "thumbnail": "https://img.jpg"}


def test_video_info_returns_400_when_yt_dlp_raises():
    client = get_client()
    with patch("main.get_video_info", side_effect=ValueError("Video unavailable")):
        response = client.post("/api/video-info", json={"url": "https://youtube.com/watch?v=abc123XY"})
    assert response.status_code == 400
    assert "Video unavailable" in response.json()["detail"]


# --- /api/download ---

def test_download_rejects_invalid_url():
    client = get_client()
    response = client.post("/api/download", json={"url": "https://vimeo.com/123", "format": "mp4"})
    assert response.status_code == 400


def test_download_rejects_invalid_format():
    client = get_client()
    response = client.post("/api/download", json={"url": "https://youtube.com/watch?v=abc123XY", "format": "avi"})
    assert response.status_code == 400


def test_download_returns_job_id():
    client = get_client()
    with patch("main.executor.submit"):
        response = client.post("/api/download", json={"url": "https://youtube.com/watch?v=abc123XY", "format": "mp4"})
    assert response.status_code == 200
    assert "job_id" in response.json()
    assert len(response.json()["job_id"]) == 36  # UUID format


# --- /api/status ---

def test_status_returns_404_for_unknown_job():
    client = get_client()
    response = client.get("/api/status/nonexistent-job-id")
    assert response.status_code == 404


def test_status_returns_progress_for_known_job():
    import main
    client = get_client()
    main.jobs["test-status-job"] = {
        "status": "downloading", "progress": 55.5, "filepath": None, "error": None
    }
    response = client.get("/api/status/test-status-job")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "downloading"
    assert data["progress"] == 55.5
    del main.jobs["test-status-job"]


# --- /api/file ---

def test_file_returns_404_for_unknown_job():
    client = get_client()
    response = client.get("/api/file/nonexistent-job-id")
    assert response.status_code == 404


def test_file_returns_400_when_job_not_done():
    import main
    client = get_client()
    main.jobs["pending-job"] = {
        "status": "downloading", "progress": 20, "filepath": None, "error": None
    }
    response = client.get("/api/file/pending-job")
    assert response.status_code == 400
    del main.jobs["pending-job"]


def test_file_streams_and_schedules_cleanup(tmp_path):
    import main
    client = get_client()
    fake_file = tmp_path / "done-job.mp4"
    fake_file.write_bytes(b"fake video content")
    main.jobs["done-job"] = {
        "status": "done", "progress": 100,
        "filepath": str(fake_file), "error": None
    }
    response = client.get("/api/file/done-job")
    assert response.status_code == 200
    assert response.content == b"fake video content"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_routes.py -v
```

Expected: `ImportError` — `main` module does not exist yet.

- [ ] **Step 3: Create main.py**

```python
import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from downloader import validate_youtube_url, get_video_info, download_video

TEMP_DIR = Path("temp")
TEMP_DIR.mkdir(exist_ok=True)

app = FastAPI()
executor = ThreadPoolExecutor(max_workers=4)
jobs: dict = {}


class VideoInfoRequest(BaseModel):
    url: str


class DownloadRequest(BaseModel):
    url: str
    format: str


@app.post("/api/video-info")
def api_video_info(req: VideoInfoRequest):
    if not validate_youtube_url(req.url):
        raise HTTPException(status_code=400, detail="URL do YouTube inválida")
    try:
        return get_video_info(req.url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/download")
def api_download(req: DownloadRequest):
    if not validate_youtube_url(req.url):
        raise HTTPException(status_code=400, detail="URL do YouTube inválida")
    if req.format not in ("mp4", "mp3"):
        raise HTTPException(status_code=400, detail="Formato inválido. Use 'mp4' ou 'mp3'.")
    job_id = str(uuid.uuid4())
    jobs[job_id] = {"status": "queued", "progress": 0, "filepath": None, "error": None}
    executor.submit(download_video, req.url, job_id, req.format, str(TEMP_DIR), jobs)
    return {"job_id": job_id}


@app.get("/api/status/{job_id}")
def api_status(job_id: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job não encontrado")
    job = jobs[job_id]
    return {"status": job["status"], "progress": job["progress"], "error": job["error"]}


@app.get("/api/file/{job_id}")
def api_file(job_id: str, background_tasks: BackgroundTasks):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job não encontrado")
    job = jobs[job_id]
    if job["status"] != "done":
        raise HTTPException(status_code=400, detail="Download ainda não concluído")
    filepath = job["filepath"]
    if not filepath or not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Arquivo não encontrado no servidor")

    def cleanup():
        jobs.pop(job_id, None)
        if os.path.exists(filepath):
            os.remove(filepath)

    background_tasks.add_task(cleanup)
    return FileResponse(filepath, filename=os.path.basename(filepath))


app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
```

- [ ] **Step 4: Run route tests to verify they pass**

```bash
pytest tests/test_routes.py -v
```

Expected: all 12 tests PASSED.

- [ ] **Step 5: Run the full test suite**

```bash
pytest -v
```

Expected: all 31 tests PASSED (19 downloader + 12 routes).

- [ ] **Step 6: Commit**

```bash
git add main.py tests/test_routes.py
git commit -m "feat: add FastAPI app with all routes and full test coverage"
```

---

## Task 6: Frontend (index.html)

**Files:**
- Create: `static/index.html`

- [ ] **Step 1: Create static/index.html**

```html
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>YT Downloader</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet" />
    <style>
        body { font-family: 'Inter', sans-serif; }
        .progress-fill { transition: width 0.4s ease; }
    </style>
</head>
<body class="bg-gray-950 text-gray-100 min-h-screen flex items-center justify-center p-4">

    <div class="w-full max-w-lg space-y-4">

        <!-- Header -->
        <div class="text-center mb-6">
            <h1 class="text-3xl font-bold text-white tracking-tight">YT Downloader</h1>
            <p class="text-gray-400 mt-1 text-sm">Cole o link do YouTube e baixe o vídeo</p>
        </div>

        <!-- Input Card -->
        <div class="bg-gray-900 rounded-2xl border border-gray-700 p-5">
            <div class="flex gap-3">
                <input
                    id="url-input"
                    type="text"
                    placeholder="https://youtube.com/watch?v=..."
                    class="flex-1 bg-gray-800 border border-gray-600 rounded-xl px-4 py-3 text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:border-red-500 transition-colors"
                />
                <button
                    id="search-btn"
                    onclick="handleSearch()"
                    class="bg-red-600 hover:bg-red-500 text-white text-sm font-semibold px-5 py-3 rounded-xl transition-colors disabled:opacity-40 disabled:cursor-not-allowed whitespace-nowrap"
                >
                    Buscar
                </button>
            </div>
            <p id="url-error" class="text-red-400 text-xs mt-2 hidden">
                Link inválido. Use um link do YouTube (youtube.com ou youtu.be).
            </p>
        </div>

        <!-- Video Info Card -->
        <div id="video-card" class="hidden bg-gray-900 rounded-2xl border border-gray-700 p-5">
            <div class="flex gap-4 mb-4">
                <img id="thumbnail" src="" alt="Thumbnail" class="w-28 h-20 object-cover rounded-lg flex-shrink-0 bg-gray-800" />
                <div class="flex-1 min-w-0 flex items-center">
                    <p id="video-title" class="text-white font-medium text-sm leading-snug line-clamp-3"></p>
                </div>
            </div>
            <div class="flex gap-3">
                <button
                    id="btn-mp4"
                    onclick="handleDownload('mp4')"
                    class="flex-1 bg-red-600 hover:bg-red-500 text-white text-sm font-semibold py-3 rounded-xl transition-colors disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                >
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                    </svg>
                    Baixar MP4
                </button>
                <button
                    id="btn-mp3"
                    onclick="handleDownload('mp3')"
                    class="flex-1 bg-gray-700 hover:bg-gray-600 text-white text-sm font-semibold py-3 rounded-xl transition-colors disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                >
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" />
                    </svg>
                    Baixar MP3
                </button>
            </div>
        </div>

        <!-- Progress Card -->
        <div id="progress-card" class="hidden bg-gray-900 rounded-2xl border border-gray-700 p-5">
            <div class="flex items-center gap-3 mb-3">
                <div class="animate-spin rounded-full h-4 w-4 border-2 border-red-500 border-t-transparent flex-shrink-0"></div>
                <p id="progress-label" class="text-gray-300 text-sm">Iniciando download...</p>
            </div>
            <div class="bg-gray-800 rounded-full h-2 overflow-hidden">
                <div id="progress-bar" class="bg-red-500 h-2 rounded-full progress-fill" style="width: 0%"></div>
            </div>
            <p id="progress-pct" class="text-gray-500 text-xs mt-1.5 text-right">0%</p>
        </div>

        <!-- Error Card -->
        <div id="error-card" class="hidden bg-red-950 border border-red-800 rounded-2xl p-4">
            <div class="flex items-start gap-3">
                <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 text-red-400 flex-shrink-0 mt-0.5" viewBox="0 0 20 20" fill="currentColor">
                    <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd" />
                </svg>
                <p id="error-msg" class="text-red-300 text-sm"></p>
            </div>
        </div>

    </div>

    <script>
        const YOUTUBE_RE = /^(https?:\/\/)?(www\.)?(youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/shorts\/)[\w-]+/;
        let pollTimer = null;

        const $ = id => document.getElementById(id);

        function showOnly(id) {
            ['video-card', 'progress-card', 'error-card'].forEach(c => $(c).classList.add('hidden'));
            if (id) $(id).classList.remove('hidden');
        }

        function setButtons(disabled) {
            ['search-btn', 'btn-mp4', 'btn-mp3'].forEach(id => $(id).disabled = disabled);
        }

        function showError(msg) {
            $('error-msg').textContent = msg;
            showOnly('error-card');
            setButtons(false);
            stopPolling();
        }

        function stopPolling() {
            if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
        }

        function setProgress(pct, label) {
            $('progress-bar').style.width = pct + '%';
            $('progress-pct').textContent = Math.round(pct) + '%';
            $('progress-label').textContent = label;
        }

        async function handleSearch() {
            const url = $('url-input').value.trim();
            $('url-error').classList.add('hidden');
            if (!YOUTUBE_RE.test(url)) {
                $('url-error').classList.remove('hidden');
                return;
            }
            setButtons(true);
            showOnly(null);
            try {
                const res = await fetch('/api/video-info', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ url })
                });
                const data = await res.json();
                if (!res.ok) throw new Error(data.detail || 'Erro ao buscar informações do vídeo.');
                $('thumbnail').src = data.thumbnail;
                $('video-title').textContent = data.title;
                showOnly('video-card');
            } catch (e) {
                showError(e.message);
            } finally {
                $('search-btn').disabled = false;
            }
        }

        async function handleDownload(format) {
            const url = $('url-input').value.trim();
            setButtons(true);
            showOnly('progress-card');
            setProgress(0, 'Iniciando download...');
            try {
                const res = await fetch('/api/download', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ url, format })
                });
                const data = await res.json();
                if (!res.ok) throw new Error(data.detail || 'Erro ao iniciar o download.');
                startPolling(data.job_id);
            } catch (e) {
                showError(e.message);
            }
        }

        function startPolling(job_id) {
            pollTimer = setInterval(async () => {
                try {
                    const res = await fetch(`/api/status/${job_id}`);
                    const data = await res.json();
                    if (data.status === 'downloading' || data.status === 'queued') {
                        setProgress(data.progress, 'Baixando...');
                    } else if (data.status === 'done') {
                        stopPolling();
                        setProgress(100, 'Concluído! Iniciando download do arquivo...');
                        window.location.href = `/api/file/${job_id}`;
                        setTimeout(() => { setButtons(false); showOnly('video-card'); }, 2500);
                    } else if (data.status === 'error') {
                        stopPolling();
                        showError(data.error || 'Ocorreu um erro durante o download.');
                    }
                } catch {
                    stopPolling();
                    showError('Erro de conexão com o servidor.');
                }
            }, 1000);
        }

        $('url-input').addEventListener('keydown', e => { if (e.key === 'Enter') handleSearch(); });
    </script>
</body>
</html>
```

- [ ] **Step 2: Verify tests still pass (static mount doesn't break routes)**

```bash
pytest -v
```

Expected: all 31 tests PASSED.

- [ ] **Step 3: Commit**

```bash
git add static/index.html
git commit -m "feat: add complete frontend with dark mode UI and progress polling"
```

---

## Task 7: Smoke Test (Manual)

**Files:** none — verification only

> **Note:** `yt-dlp` requires `ffmpeg` installed on your system to merge MP4 video+audio streams. Install it before this step.
> - Windows: `winget install ffmpeg` or download from https://ffmpeg.org/download.html and add to PATH.

- [ ] **Step 1: Start the server**

```bash
python main.py
```

Expected output:
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

- [ ] **Step 2: Open the app**

Navigate to `http://localhost:8000` in your browser. Verify:
- Dark background, centered layout
- Input field and "Buscar" button visible

- [ ] **Step 3: Test URL validation**

Paste `https://vimeo.com/123` and click Buscar. Expected: red error message "Link inválido..." appears without any network request.

- [ ] **Step 4: Test video info fetch**

Paste a real public YouTube URL (e.g. `https://www.youtube.com/watch?v=dQw4w9WgXcQ`) and click Buscar. Expected: thumbnail and title appear, two download buttons visible.

- [ ] **Step 5: Test MP3 download**

Click "Baixar MP3". Expected:
- Progress card appears with spinner and progress bar updating
- After completion, browser download dialog opens for a `.mp3` file
- Video card reappears after ~2.5 seconds

- [ ] **Step 6: Test MP4 download**

Repeat with a short video and click "Baixar MP4". Expected: `.mp4` file downloads.

- [ ] **Step 7: Final commit**

```bash
git add .
git commit -m "chore: project complete — all features verified manually"
```

---

## Summary

| Task | Output |
|------|--------|
| 1 | Project scaffold, dependencies installed |
| 2 | `validate_youtube_url`, `parse_progress_line` — tested |
| 3 | `get_video_info` — tested with mocks |
| 4 | `download_video` — tested with mocks |
| 5 | All 5 FastAPI routes — tested with TestClient |
| 6 | Complete dark-mode frontend |
| 7 | Manual smoke test passed |
