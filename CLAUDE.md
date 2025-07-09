# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

YouTube Deep Summary is a comprehensive toolkit for downloading YouTube transcripts with multiple implementation approaches, AI-powered summarization using GPT-4.1, and a responsive web interface with Supabase database integration. The project handles various network restrictions and provides both command-line tools and a web application with persistent storage for transcripts, summaries, and channel management.

## Core Scripts

### Primary Scripts
- **`download_transcript.py`** - Main implementation using `youtube-transcript-api` library with proxy support
- **`simple_transcript.py`** - Alternative implementation using `yt-dlp` for broader compatibility
- **`download_transcript_manual.py`** - Manual web scraping fallback (no external dependencies)

### Web Application & Advanced Features
- **`app.py`** - Flask web application with transcript viewing, AI summarization, and database storage
- **`transcript_summarizer.py`** - OpenAI GPT-4.1 powered summarization with chapter support
- **`database_storage.py`** - Supabase database integration for persistent storage
- **`transcript_cache.py`** - Legacy file-based caching system (replaced by database storage)

### Architecture
The system follows a layered architecture:
1. **Data Layer**: Extract video ID from YouTube URLs using regex patterns
2. **Storage Layer**: Supabase database with tables for videos, transcripts, chapters, and summaries
3. **Acquisition Layer**: Download transcript and video metadata using multiple methods
4. **Processing Layer**: Format transcript into readable paragraphs with chapter organization
5. **AI Layer**: Generate structured summaries using GPT-4.1 via AJAX
6. **Presentation Layer**: Responsive web interface with mobile optimization and channel management

## Common Development Commands

### Setup
```bash
# Install all dependencies from requirements.txt
pip install -r requirements.txt

# Or install individual packages
pip install flask youtube-transcript-api openai python-dotenv yt-dlp supabase markdown
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

# Using startup script with proxy configuration
./start_server.sh

# Testing chapter extraction
python3 test_chapters.py
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

# Required for database storage
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_anon_key

# Optional proxy configuration
YOUTUBE_PROXY=proxy_ip:8080

# Flask configuration
FLASK_HOST=0.0.0.0          # Optional, defaults to 0.0.0.0
FLASK_PORT=33079            # Optional, defaults to 33079
FLASK_DEBUG=True            # Optional, defaults to True
```

## Database Setup

The application uses Supabase for persistent storage. Initialize tables using:

```bash
# Run SQL commands from create_tables.sql in your Supabase SQL editor
# This creates tables for: youtube_videos, transcripts, video_chapters, summaries
```

## Deployment

### Docker Deployment
```bash
# Build Docker image
docker build -t youtube-deep-search .

# Run with environment variables
docker run -p 33079:33079 \
  -e OPENAI_API_KEY=your_key \
  -e SUPABASE_URL=your_url \
  -e SUPABASE_KEY=your_key \
  youtube-deep-search
```

## Web Application Features

### User Interface
- **`/`** - Home page with instructions and examples
- **`/watch?v=VIDEO_ID`** - Display transcript with video metadata, thumbnails, and chapters
- **`/channels`** - Browse all channels with saved videos
- **`/channel/<channel_name>/videos`** - View all videos from a specific channel
- **`/channel/<channel_name>/summaries`** - View all summaries from a specific channel
- **`/storage`** - Database storage statistics and management
- **Mobile-responsive design** with optimized padding and collapsible elements
- **Dual view modes**: Toggle between readable paragraphs and detailed timestamps
- **AJAX summarization**: Generate AI summaries without page reloads

### API Endpoints
- **`GET /api/transcript/VIDEO_ID`** - JSON API for transcript data with database storage
- **`POST /api/summary`** - Generate summary from provided transcript data (efficient)
- **`GET /api/cache/info`** - Legacy cache statistics (deprecated)
- **`POST /api/cache/cleanup`** - Legacy cache cleanup (deprecated)
- **`GET /api/storage/stats`** - Database storage statistics and metrics

### Advanced Features
- **Chapter Organization**: Automatic detection and display of video chapters
- **Video Metadata**: Title, thumbnail, duration, uploader information
- **Persistent Storage**: Supabase database with tables for videos, transcripts, chapters, and summaries
- **Channel Management**: Browse videos and summaries organized by YouTube channels
- **Proxy Support**: Configurable proxy for both transcript and chapter extraction

### AI Summarization Features
- **GPT-4.1 Integration**: Latest OpenAI model with improved context understanding
- **Structured summary format** with organized sections:
  - Overview, Main Topics, Key Takeaways & Insights
  - Actionable Strategies, Specific Details & Examples
  - Warnings & Common Mistakes, Resources & Next Steps
- **Efficient processing**: Uses pre-formatted transcript data to avoid redundant downloads

## Database Schema

The application uses four main tables in Supabase:

### youtube_videos
- **video_id** (VARCHAR 11, unique) - YouTube video identifier
- **title, uploader, duration, thumbnail_url** - Video metadata
- **created_at, updated_at** - Timestamps

### transcripts
- **video_id** (FK to youtube_videos) - Links to video
- **transcript_data** (JSONB) - Raw transcript with timestamps
- **formatted_transcript** (TEXT) - Readable paragraph format
- **language_used** - Transcript language code

### video_chapters
- **video_id** (FK to youtube_videos) - Links to video
- **chapters_data** (JSONB) - Array of chapter objects with timestamps

### summaries
- **video_id** (FK to youtube_videos) - Links to video
- **summary_text** (TEXT) - AI-generated summary
- **model_used** - OpenAI model identifier (defaults to gpt-4.1)

## Testing

```bash
# Test chapter extraction functionality
python3 test_chapters.py

# Test basic transcript functionality
python3 download_transcript.py "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
```