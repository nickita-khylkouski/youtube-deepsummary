# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a YouTube transcript downloader toolkit with multiple implementation approaches to handle various network restrictions and dependencies.

## Core Scripts

### Primary Scripts
- **`download_transcript.py`** - Main implementation using `youtube-transcript-api` library with proxy support
- **`simple_transcript.py`** - Alternative implementation using `yt-dlp` for broader compatibility
- **`download_transcript_manual.py`** - Manual web scraping fallback (no external dependencies)

### Web Application & Summarization
- **`app.py`** - Flask web application for viewing transcripts with optional AI summarization
- **`transcript_summarizer.py`** - OpenAI-powered transcript summarization module

### Architecture
All scripts follow the same pattern:
1. Extract video ID from YouTube URL using regex patterns
2. Download transcript data using different methods
3. Format transcript with timestamps as `[time] text`
4. Save to `transcript_{video_id}.txt`

## Common Development Commands

### Setup
```bash
# Install dependencies for main script
pip install youtube-transcript-api

# Alternative: Install yt-dlp for simple_transcript.py
pip install yt-dlp

# For web application and summarization
pip install flask openai python-dotenv
```

### Running Scripts
```bash
# Main script (with optional proxy)
python3 download_transcript.py "https://www.youtube.com/watch?v=VIDEO_ID" [proxy_ip]

# yt-dlp version
python3 simple_transcript.py "https://www.youtube.com/watch?v=VIDEO_ID"

# Manual fallback
python3 download_transcript_manual.py "https://www.youtube.com/watch?v=VIDEO_ID"

# Web application (requires .env configuration)
python3 app.py
```

## Network Considerations

- Cloud provider IPs are commonly blocked by YouTube
- `download_transcript.py` supports HTTP proxy configuration (port 8080)
- `simple_transcript.py` uses yt-dlp which may have better network handling
- Manual script attempts direct web scraping but has limited success

## Key Implementation Details

- All scripts extract 11-character YouTube video IDs from various URL formats
- Transcript format: `[timestamp] text` with timestamps in seconds
- Error handling focuses on network connectivity and transcript availability
- Scripts output first 500 characters for verification before saving full transcript

## Environment Configuration

The web application and summarization features require environment variables:

```bash
# Required for summarization
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-3.5-turbo  # Optional, defaults to gpt-3.5-turbo
OPENAI_MAX_TOKENS=2000      # Optional, defaults to 2000
OPENAI_TEMPERATURE=0.7      # Optional, defaults to 0.7

# Optional proxy configuration
YOUTUBE_PROXY=proxy_ip:8080

# Flask configuration
FLASK_HOST=0.0.0.0          # Optional, defaults to 0.0.0.0
FLASK_PORT=33079            # Optional, defaults to 33079
FLASK_DEBUG=True            # Optional, defaults to True
```

## Web Application Features

### Endpoints
- **`/`** - Home page with instructions
- **`/watch?v=VIDEO_ID`** - Display transcript for YouTube video
- **`/watch?v=VIDEO_ID&summarize=true`** - Display transcript with AI summary
- **`/api/transcript/VIDEO_ID`** - JSON API for transcript data
- **`/api/summary/VIDEO_ID`** - JSON API for transcript summary

### Summarization Features
- AI-powered summaries using OpenAI's GPT models
- Structured summary format with sections:
  - Overview
  - Main Topics Covered
  - Key Takeaways & Insights
  - Actionable Strategies
  - Specific Details & Examples
  - Warnings & Common Mistakes
  - Resources & Next Steps