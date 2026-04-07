"""Tests for youtube_transcript_downloader."""

import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from youtube_transcript_downloader import (
    extract_video_id,
    fetch_metadata,
    fetch_transcript,
    format_duration,
    main,
    save_transcript,
    yaml_escape,
)

# --- extract_video_id ---


@pytest.mark.parametrize(
    ("input_val", "expected"),
    [
        ("https://www.youtube.com/watch?v=xdxgLTzfCWI", "xdxgLTzfCWI"),
        ("https://youtu.be/xdxgLTzfCWI", "xdxgLTzfCWI"),
        ("https://www.youtube.com/embed/xdxgLTzfCWI", "xdxgLTzfCWI"),
        ("xdxgLTzfCWI", "xdxgLTzfCWI"),
        ("https://www.youtube.com/watch?v=xdxgLTzfCWI&t=120", "xdxgLTzfCWI"),
        ("https://www.youtube.com/v/xdxgLTzfCWI", "xdxgLTzfCWI"),
    ],
)
def test_extract_video_id(input_val: str, expected: str) -> None:
    assert extract_video_id(input_val) == expected


def test_extract_video_id_invalid() -> None:
    with pytest.raises(ValueError, match="Could not extract video ID"):
        extract_video_id("not-a-video-id")


# --- format_duration ---


@pytest.mark.parametrize(
    ("iso", "expected"),
    [
        ("PT1H2M3S", "1:02:03"),
        ("PT5M30S", "5:30"),
        ("PT45S", "0:45"),
        ("PT2H", "2:00:00"),
        ("PT0S", "0:00"),
        ("garbage", "garbage"),
    ],
)
def test_format_duration(iso: str, expected: str) -> None:
    assert format_duration(iso) == expected


# --- yaml_escape ---


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("Hello World", "Hello World"),
        ("Title: Subtitle", '"Title: Subtitle"'),
        ('He said "hi"', '"He said \\"hi\\""'),
        ("A & B", '"A & B"'),
        ("Just text", "Just text"),
    ],
)
def test_yaml_escape(value: str, expected: str) -> None:
    assert yaml_escape(value) == expected


# --- save_transcript ---


def test_save_transcript(tmp_path: Path) -> None:
    meta = {
        "title": "Test Video Title",
        "channel": "Test Channel",
        "date": "2024-01-15",
        "duration": "5:30",
        "views": 1000,
        "likes": 50,
        "comments": 10,
        "video_id": "abc123def45",
    }
    transcript = "Hello world\nThis is a test transcript"

    filepath = save_transcript(meta, transcript, tmp_path)

    assert filepath.exists()
    assert filepath.name == "2024-01-15_Test Video Title.md"

    content = filepath.read_text()
    assert content.startswith("---\n")
    assert "video_id: abc123def45" in content
    assert "title: Test Video Title" in content
    assert "Hello world\nThis is a test transcript" in content


def test_save_transcript_sanitizes_title(tmp_path: Path) -> None:
    meta = {
        "title": 'Bad<>:"/\\|?*Title',
        "channel": "Ch",
        "date": "2024-01-01",
        "duration": "1:00",
        "views": 0,
        "likes": 0,
        "comments": 0,
        "video_id": "abc123def45",
    }
    filepath = save_transcript(meta, "text", tmp_path)
    assert "<" not in filepath.name
    assert ">" not in filepath.name


# --- fetch_metadata ---


def test_fetch_metadata() -> None:
    mock_youtube = MagicMock()
    mock_youtube.videos().list().execute.return_value = {
        "items": [
            {
                "id": "vid123456789",
                "snippet": {
                    "title": "Test Video",
                    "channelTitle": "Test Channel",
                    "publishedAt": "2024-01-15T10:00:00Z",
                },
                "contentDetails": {"duration": "PT5M30S"},
                "statistics": {"viewCount": "1000", "likeCount": "50", "commentCount": "10"},
            }
        ]
    }

    result = fetch_metadata(mock_youtube, ["vid123456789"])

    assert "vid123456789" in result
    meta = result["vid123456789"]
    assert meta["title"] == "Test Video"
    assert meta["duration"] == "5:30"
    assert meta["views"] == 1000
    assert meta["date"] == "2024-01-15"


# --- fetch_transcript ---


@patch("youtube_transcript_downloader.youtube_transcript_downloader.YouTubeTranscriptApi")
def test_fetch_transcript(mock_api_class: MagicMock) -> None:
    mock_instance = mock_api_class.return_value
    mock_instance.fetch.return_value = [
        SimpleNamespace(text="Hello"),
        SimpleNamespace(text="World"),
    ]

    result = fetch_transcript("vid123456789")

    assert result == "Hello\nWorld"
    mock_instance.fetch.assert_called_once_with("vid123456789", languages=["en"])


@patch("youtube_transcript_downloader.youtube_transcript_downloader.YouTubeTranscriptApi")
def test_fetch_transcript_with_language(mock_api_class: MagicMock) -> None:
    mock_instance = mock_api_class.return_value
    mock_instance.fetch.return_value = [
        SimpleNamespace(text="Hallo"),
        SimpleNamespace(text="Welt"),
    ]

    result = fetch_transcript("vid123456789", languages=["de", "en"])

    assert result == "Hallo\nWelt"
    mock_instance.fetch.assert_called_once_with("vid123456789", languages=["de", "en"])


@patch("youtube_transcript_downloader.youtube_transcript_downloader.YouTubeTranscriptApi")
def test_fetch_transcript_error(mock_api_class: MagicMock) -> None:
    mock_instance = mock_api_class.return_value
    mock_instance.fetch.side_effect = Exception("No transcript")

    result = fetch_transcript("vid123456789")

    assert result is None


# --- CLI integration ---


@patch("youtube_transcript_downloader.youtube_transcript_downloader.YouTubeTranscriptApi")
@patch("youtube_transcript_downloader.youtube_transcript_downloader.build")
def test_main_cli(mock_build: MagicMock, mock_api_class: MagicMock, tmp_path: Path) -> None:
    mock_youtube = MagicMock()
    mock_build.return_value = mock_youtube
    mock_youtube.videos().list().execute.return_value = {
        "items": [
            {
                "id": "xdxgLTzfCWI",
                "snippet": {
                    "title": "Test Video",
                    "channelTitle": "Test Channel",
                    "publishedAt": "2024-01-15T10:00:00Z",
                },
                "contentDetails": {"duration": "PT5M30S"},
                "statistics": {"viewCount": "1000", "likeCount": "50", "commentCount": "10"},
            }
        ]
    }
    mock_instance = mock_api_class.return_value
    mock_instance.fetch.return_value = [SimpleNamespace(text="Hello transcript")]

    runner = CliRunner()
    result = runner.invoke(
        main, ["xdxgLTzfCWI", "--api-key", "fake-key", "--output-dir", str(tmp_path)]
    )

    assert result.exit_code == 0
    files = list(tmp_path.glob("*.md"))
    assert len(files) == 1
    assert "video_id: xdxgLTzfCWI" in files[0].read_text()
    mock_instance.fetch.assert_called_once_with("xdxgLTzfCWI", languages=["en"])


@patch("youtube_transcript_downloader.youtube_transcript_downloader.YouTubeTranscriptApi")
@patch("youtube_transcript_downloader.youtube_transcript_downloader.build")
def test_main_cli_with_language(
    mock_build: MagicMock, mock_api_class: MagicMock, tmp_path: Path
) -> None:
    mock_youtube = MagicMock()
    mock_build.return_value = mock_youtube
    mock_youtube.videos().list().execute.return_value = {
        "items": [
            {
                "id": "xdxgLTzfCWI",
                "snippet": {
                    "title": "Test Video",
                    "channelTitle": "Test Channel",
                    "publishedAt": "2024-01-15T10:00:00Z",
                },
                "contentDetails": {"duration": "PT5M30S"},
                "statistics": {"viewCount": "1000", "likeCount": "50", "commentCount": "10"},
            }
        ]
    }
    mock_instance = mock_api_class.return_value
    mock_instance.fetch.return_value = [SimpleNamespace(text="Hallo transcript")]

    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "xdxgLTzfCWI",
            "--api-key",
            "fake-key",
            "--output-dir",
            str(tmp_path),
            "--language",
            "de,en",
        ],
    )

    assert result.exit_code == 0
    mock_instance.fetch.assert_called_once_with("xdxgLTzfCWI", languages=["de", "en"])


# --- End-to-end test ---


@pytest.mark.skipif(
    not os.environ.get("YOUTUBE_API_KEY"),
    reason="YOUTUBE_API_KEY not set; skipping e2e test",
)
def test_e2e_download(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        main,
        ["xdxgLTzfCWI", "--api-key", os.environ["YOUTUBE_API_KEY"], "--output-dir", str(tmp_path)],
    )

    assert result.exit_code == 0, f"CLI failed: {result.output}"
    files = list(tmp_path.glob("*.md"))
    assert len(files) == 1
    content = files[0].read_text()
    assert "video_id: xdxgLTzfCWI" in content
    assert "---" in content
