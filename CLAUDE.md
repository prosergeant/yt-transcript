# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Stateless FastAPI microservice that extracts transcripts from YouTube videos. Single file (`main.py`) with no subdirectory structure.

## Development Commands

### Local (without Docker)
```bash
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### Docker
```bash
docker build -t yt-transcript .
docker run -p 8000:8000 yt-transcript
```

### API docs
Available at `http://localhost:8000/docs` when running locally.

## Architecture

All logic lives in `main.py`:

- `extract_video_id(value)` — Parses YouTube video IDs from all URL formats (standard, youtu.be, embed, shorts) via regex, or validates a raw 11-char ID.
- `_fetch_transcript(video_id, lang, format)` — Core transcript fetcher with 3-level language fallback: requested lang → English → any available. Returns either `full` format (chunks with timing + duration) or `text` format (plain string).

### Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /transcript/{video_id}` | Fetch by video ID |
| `GET /transcript?url=...` | Fetch by full YouTube URL |

Both accept `lang` (default: `ru`) and `format` (default: `full`, or `text`) query params.

## Stack

- **Python 3.11**, **FastAPI 0.115.0**, **uvicorn**
- **youtube-transcript-api 0.6.3** — core dependency for fetching transcripts
- CORS enabled for all origins (GET only)
- Deployed via Docker on Render.com
