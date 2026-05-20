import json
import pytest
from unittest.mock import MagicMock, patch

from downloader import download_video, get_video_info, parse_progress_line, validate_youtube_url


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
