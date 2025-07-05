# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

YouTube Deep Summary is a comprehensive toolkit for downloading YouTube transcripts with multiple implementation approaches, AI-powered summarization using GPT-4.1, intelligent caching, and a responsive web interface. The project handles various network restrictions and provides both command-line tools and a web application.

## Core Scripts

### Primary Scripts
- **`download_transcript.py`** - Main implementation using `youtube-transcript-api` library with proxy support
- **`simple_transcript.py`** - Alternative implementation using `yt-dlp` for broader compatibility
- **`download_transcript_manual.py`** - Manual web scraping fallback (no external dependencies)

### Web Application & Advanced Features
- **`app.py`** - Flask web application with transcript viewing, AI summarization, and caching
- **`transcript_summarizer.py`** - OpenAI GPT-4.1 powered summarization with chapter support
- **`transcript_cache.py`** - Intelligent file-based caching system with 24-hour TTL

### Architecture
The system follows a layered architecture:
1. **Data Layer**: Extract video ID from YouTube URLs using regex patterns
2. **Caching Layer**: Check local cache (24h TTL) before downloading
3. **Acquisition Layer**: Download transcript and video metadata using multiple methods
4. **Processing Layer**: Format transcript into readable paragraphs with chapter organization
5. **AI Layer**: Generate structured summaries using GPT-4.1 via AJAX
6. **Presentation Layer**: Responsive web interface with mobile optimization

## Common Development Commands

### Setup
```bash
# Install dependencies for main script
pip install youtube-transcript-api

# Alternative: Install yt-dlp for simple_transcript.py
pip install yt-dlp

# For web application, summarization, and caching
pip install flask openai python-dotenv yt-dlp
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

### Data Processing
- All scripts extract 11-character YouTube video IDs from various URL formats
- Dual transcript format: detailed timestamps `[MM:SS] text` and readable paragraphs
- Chapter-aware formatting with automatic organization by video sections
- Intelligent caching prevents redundant API calls with 24-hour TTL

### Performance Optimizations
- AJAX-based AI summarization without page reloads
- Local file-based caching system with automatic cleanup
- Mobile-responsive UI with optimized padding and layout
- Efficient transcript processing using pre-formatted text for AI

### Error Handling & Reliability
- Graceful fallbacks for network connectivity issues
- Multiple transcript acquisition methods (youtube-transcript-api, yt-dlp, manual)
- Proxy support for restricted network environments
- Comprehensive error messaging and cache failure recovery

## Environment Configuration

The web application and summarization features require environment variables:

```bash
# Required for summarization
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4.1        # Optional, defaults to gpt-4.1
OPENAI_MAX_TOKENS=100000    # Optional, defaults to 100000
OPENAI_TEMPERATURE=0.7      # Optional, defaults to 0.7

# Optional proxy configuration
YOUTUBE_PROXY=proxy_ip:8080

# Flask configuration
FLASK_HOST=0.0.0.0          # Optional, defaults to 0.0.0.0
FLASK_PORT=33079            # Optional, defaults to 33079
FLASK_DEBUG=True            # Optional, defaults to True
```

## Web Application Features

### User Interface
- **`/`** - Home page with instructions and examples
- **`/watch?v=VIDEO_ID`** - Display transcript with video metadata, thumbnails, and chapters
- **Mobile-responsive design** with optimized padding and collapsible elements
- **Dual view modes**: Toggle between readable paragraphs and detailed timestamps
- **AJAX summarization**: Generate AI summaries without page reloads

### API Endpoints
- **`GET /api/transcript/VIDEO_ID`** - JSON API for transcript data with caching
- **`POST /api/summary`** - Generate summary from provided transcript data (efficient)
- **`GET /api/cache/info`** - Cache statistics and performance metrics
- **`POST /api/cache/cleanup`** - Manual cleanup of expired cache files

### Advanced Features
- **Chapter Organization**: Automatic detection and display of video chapters
- **Video Metadata**: Title, thumbnail, duration, uploader information
- **Intelligent Caching**: 24-hour TTL with automatic cleanup and cache statistics
- **Proxy Support**: Configurable proxy for both transcript and chapter extraction

### AI Summarization Features
- **GPT-4.1 Integration**: Latest OpenAI model with improved context understanding
- **Structured summary format** with organized sections:
  - Overview, Main Topics, Key Takeaways & Insights
  - Actionable Strategies, Specific Details & Examples
  - Warnings & Common Mistakes, Resources & Next Steps
- **Efficient processing**: Uses pre-formatted transcript data to avoid redundant downloads