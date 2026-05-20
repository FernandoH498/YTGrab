import json
import pytest
from unittest.mock import MagicMock, patch

from downloader import get_video_info, parse_progress_line, validate_youtube_url


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
