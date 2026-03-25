"""
Tests for YouTube Transcript microservice.

Unit tests - без сетевых запросов (YouTubeTranscriptApi замокан).
Integration test - реальный запрос к YouTube (маркер `real`).
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from youtube_transcript_api import NoTranscriptFound, TranscriptsDisabled

from main import app, extract_video_id

client = TestClient(app)


# ---------------------------------------------------------------------------
# Мок-данные
# ---------------------------------------------------------------------------

class Snippet:
    """Имитирует FetchedTranscriptSnippet из youtube-transcript-api >= 1.x."""
    def __init__(self, text, start, duration):
        self.text = text
        self.start = start
        self.duration = duration


MOCK_SNIPPETS = [
    Snippet("Привет мир", 0.0, 2.5),
    Snippet("Это тестовое видео", 2.5, 3.0),
]


def make_api_mock(fetch_return=None, fetch_side_effect=None):
    """Создаёт мок YouTubeTranscriptApi() с нужным поведением fetch()."""
    mock_instance = MagicMock()
    if fetch_side_effect is not None:
        mock_instance.fetch.side_effect = fetch_side_effect
    else:
        mock_instance.fetch.return_value = fetch_return
    return mock_instance


# ---------------------------------------------------------------------------
# Unit: extract_video_id
# ---------------------------------------------------------------------------


class TestExtractVideoId:
    def test_standard_url(self):
        assert extract_video_id("https://www.youtube.com/watch?v=J53r2F7w6QQ") == "J53r2F7w6QQ"

    def test_short_url(self):
        assert extract_video_id("https://youtu.be/J53r2F7w6QQ") == "J53r2F7w6QQ"

    def test_embed_url(self):
        assert extract_video_id("https://www.youtube.com/embed/J53r2F7w6QQ") == "J53r2F7w6QQ"

    def test_shorts_url(self):
        assert extract_video_id("https://www.youtube.com/shorts/J53r2F7w6QQ") == "J53r2F7w6QQ"

    def test_raw_video_id(self):
        assert extract_video_id("J53r2F7w6QQ") == "J53r2F7w6QQ"

    def test_url_with_extra_params(self):
        assert extract_video_id("https://www.youtube.com/watch?v=J53r2F7w6QQ&t=120s") == "J53r2F7w6QQ"

    def test_invalid_url_raises(self):
        with pytest.raises(ValueError):
            extract_video_id("https://example.com/notayoutube")

    def test_short_string_raises(self):
        with pytest.raises(ValueError):
            extract_video_id("short")


# ---------------------------------------------------------------------------
# API: GET /
# ---------------------------------------------------------------------------


class TestRoot:
    def test_returns_service_info(self):
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "YouTube Transcript API"
        assert "endpoints" in data


# ---------------------------------------------------------------------------
# API: GET /transcript/{video_id}
# ---------------------------------------------------------------------------


class TestGetTranscriptById:
    @patch("main.YouTubeTranscriptApi", return_value=make_api_mock(MOCK_SNIPPETS))
    def test_full_format_default(self, MockApi):
        response = client.get("/transcript/J53r2F7w6QQ")
        assert response.status_code == 200
        data = response.json()
        assert data["video_id"] == "J53r2F7w6QQ"
        assert "text" in data
        assert "chunks" in data
        assert "chunks_count" in data
        assert data["chunks_count"] == 2
        assert "duration_seconds" in data

    @patch("main.YouTubeTranscriptApi", return_value=make_api_mock(MOCK_SNIPPETS))
    def test_text_format(self, MockApi):
        response = client.get("/transcript/J53r2F7w6QQ?format=text")
        assert response.status_code == 200
        data = response.json()
        assert data["video_id"] == "J53r2F7w6QQ"
        assert "text" in data
        assert "chunks" not in data

    @patch("main.YouTubeTranscriptApi", return_value=make_api_mock(MOCK_SNIPPETS))
    def test_text_contains_joined_chunks(self, MockApi):
        response = client.get("/transcript/J53r2F7w6QQ?format=text")
        data = response.json()
        assert "Привет мир" in data["text"]
        assert "Это тестовое видео" in data["text"]

    @patch("main.YouTubeTranscriptApi", return_value=make_api_mock(
        fetch_side_effect=TranscriptsDisabled("vid")
    ))
    def test_transcripts_disabled_returns_403(self, MockApi):
        response = client.get("/transcript/J53r2F7w6QQ")
        assert response.status_code == 403

    @patch("main.YouTubeTranscriptApi")
    def test_no_transcript_found_returns_404(self, MockApi):
        mock_instance = MagicMock()
        mock_instance.fetch.side_effect = NoTranscriptFound("vid", ["ru"], {})
        mock_instance.list.side_effect = NoTranscriptFound("vid", [], {})
        MockApi.return_value = mock_instance

        response = client.get("/transcript/J53r2F7w6QQ?lang=ru")
        assert response.status_code == 404

    @patch("main.YouTubeTranscriptApi")
    def test_lang_param_passed_to_api(self, MockApi):
        mock_instance = make_api_mock(MOCK_SNIPPETS)
        MockApi.return_value = mock_instance

        client.get("/transcript/J53r2F7w6QQ?lang=en")
        mock_instance.fetch.assert_called_once_with("J53r2F7w6QQ", languages=["en"])


# ---------------------------------------------------------------------------
# API: GET /transcript?url=...
# ---------------------------------------------------------------------------


class TestGetTranscriptByUrl:
    @patch("main.YouTubeTranscriptApi", return_value=make_api_mock(MOCK_SNIPPETS))
    def test_accepts_full_url(self, MockApi):
        response = client.get("/transcript?url=https://www.youtube.com/watch?v=J53r2F7w6QQ")
        assert response.status_code == 200
        assert response.json()["video_id"] == "J53r2F7w6QQ"

    @patch("main.YouTubeTranscriptApi", return_value=make_api_mock(MOCK_SNIPPETS))
    def test_accepts_short_url(self, MockApi):
        response = client.get("/transcript?url=https://youtu.be/J53r2F7w6QQ")
        assert response.status_code == 200
        assert response.json()["video_id"] == "J53r2F7w6QQ"

    def test_invalid_url_returns_400(self):
        response = client.get("/transcript?url=https://example.com/not-youtube")
        assert response.status_code == 400

    def test_missing_url_param_returns_422(self):
        response = client.get("/transcript")
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# Fallback: переключение языка
# ---------------------------------------------------------------------------


class TestLanguageFallback:
    @patch("main.YouTubeTranscriptApi")
    def test_falls_back_to_english_when_lang_not_found(self, MockApi):
        mock_instance = MagicMock()
        # Первый вызов (ru) кидает NoTranscriptFound, второй (en) — успешен
        mock_instance.fetch.side_effect = [
            NoTranscriptFound("vid", ["ru"], {}),
            MOCK_SNIPPETS,
        ]
        MockApi.return_value = mock_instance

        response = client.get("/transcript/J53r2F7w6QQ?lang=ru")
        assert response.status_code == 200
        assert mock_instance.fetch.call_count == 2


# ---------------------------------------------------------------------------
# Real integration test — требует сети (запускать вручную: pytest -m real)
# ---------------------------------------------------------------------------


@pytest.mark.real
def test_real_youtube_transcript():
    """Реальный запрос к YouTube. Видео: Rick Astley - Never Gonna Give You Up."""
    response = client.get("/transcript/dQw4w9WgXcQ?lang=en&format=text")
    assert response.status_code == 200
    data = response.json()
    assert data["video_id"] == "dQw4w9WgXcQ"
    assert len(data["text"]) > 100
