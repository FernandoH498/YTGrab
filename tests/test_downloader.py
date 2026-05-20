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
