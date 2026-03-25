from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound, TranscriptsDisabled
from urllib.parse import urlparse, parse_qs
import re

app = FastAPI(
    title="YouTube Transcript API",
    description="Extracts subtitles from YouTube videos",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


def extract_video_id(value: str) -> str:
    """Extract video ID from URL or return as-is if already an ID."""
    patterns = [
        r"(?:v=|youtu\.be/|embed/|shorts/)([a-zA-Z0-9_-]{11})",
    ]
    for pattern in patterns:
        match = re.search(pattern, value)
        if match:
            return match.group(1)
    # Assume it's already a video ID
    if re.match(r"^[a-zA-Z0-9_-]{11}$", value):
        return value
    raise ValueError(f"Cannot extract video ID from: {value}")


@app.get("/")
def root():
    return {
        "service": "YouTube Transcript API",
        "endpoints": {
            "GET /transcript/{video_id}": "Get transcript by video ID",
            "GET /transcript?url=...": "Get transcript by full YouTube URL",
        },
        "example": "/transcript/J53r2F7w6QQ?lang=ru",
    }


@app.get("/transcript/{video_id}")
def get_transcript_by_id(
    video_id: str,
    lang: str = Query(default="ru", description="Preferred language code (e.g. ru, en)"),
    format: str = Query(default="full", description="Response format: 'full' or 'text'"),
):
    return _fetch_transcript(video_id, lang, format)


@app.get("/transcript")
def get_transcript_by_url(
    url: str = Query(..., description="Full YouTube video URL"),
    lang: str = Query(default="ru", description="Preferred language code (e.g. ru, en)"),
    format: str = Query(default="full", description="Response format: 'full' or 'text'"),
):
    try:
        video_id = extract_video_id(url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _fetch_transcript(video_id, lang, format)


def _fetch_transcript(video_id: str, lang: str, format: str):
    api = YouTubeTranscriptApi()
    try:
        # Try preferred language first, fallback to English, then any available
        try:
            raw = api.fetch(video_id, languages=[lang])
        except NoTranscriptFound:
            try:
                raw = api.fetch(video_id, languages=["en"])
            except NoTranscriptFound:
                # Get whatever is available
                transcript_list = api.list(video_id)
                transcript = transcript_list.find_generated_transcript(
                    list(transcript_list._generated_transcripts.keys())
                    or list(transcript_list._manually_created_transcripts.keys())
                )
                raw = transcript.fetch()

        chunks = [{"text": s.text, "start": s.start, "duration": s.duration} for s in raw]
        text = " ".join([c["text"] for c in chunks])

        if format == "text":
            return {"video_id": video_id, "text": text}

        return {
            "video_id": video_id,
            "text": text,
            "duration_seconds": round(chunks[-1]["start"] + chunks[-1]["duration"]) if chunks else 0,
            "chunks_count": len(chunks),
            "chunks": chunks,
        }

    except TranscriptsDisabled:
        raise HTTPException(status_code=403, detail="Субтитры отключены для этого видео")
    except NoTranscriptFound:
        raise HTTPException(status_code=404, detail=f"Субтитры не найдены (запрошен язык: {lang})")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))