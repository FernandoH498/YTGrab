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


def test_file_returns_404_when_file_missing_from_disk(tmp_path):
    import main
    client = get_client()
    main.jobs["ghost-job"] = {
        "status": "done", "progress": 100,
        "filepath": str(tmp_path / "nonexistent.mp4"), "error": None
    }
    response = client.get("/api/file/ghost-job")
    assert response.status_code == 404
    del main.jobs["ghost-job"]
