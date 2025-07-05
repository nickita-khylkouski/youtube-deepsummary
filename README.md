# YouTube Deep Summary

A comprehensive toolkit for downloading YouTube transcripts with multiple implementation approaches, AI-powered summarization, and intelligent caching capabilities.

## Features

### Core Functionality
- **Multiple Transcript Methods**: `youtube-transcript-api`, `yt-dlp`, and manual web scraping
- **Network Resilience**: Proxy support for cloud environments and restricted networks
- **Format Flexibility**: Accepts video IDs, full URLs, or short URLs

### Web Application
- **Clean Web Interface**: Responsive UI for viewing transcripts with mobile optimization
- **AI-Powered Summarization**: OpenAI GPT-4.1 integration for intelligent video summaries
- **RESTful API**: JSON endpoints for programmatic access
- **Real-time Processing**: AJAX-based summarization without page reloads
- **Chapter Organization**: Automatic video chapter detection and structured display
- **Dual View Modes**: Toggle between readable paragraphs and detailed timestamps

### Advanced Features
- **Intelligent Caching**: Local file-based caching with 24-hour TTL for improved performance
- **Video Metadata**: Automatic extraction of titles, thumbnails, duration, and uploader info
- **Chapter Support**: Organized transcript display by video chapters when available
- **Mobile Responsive**: Optimized interface for mobile devices with reduced padding
- **Proxy Support**: Configurable proxy settings for restricted network environments

### Summarization Features
- **Structured Summaries**: Organized sections including overview, key takeaways, and actionable strategies
- **GPT-4.1 Integration**: Latest OpenAI model with improved instruction following and context understanding
- **Efficient Processing**: Uses pre-formatted transcript data to avoid redundant API calls
- **Error Handling**: Graceful fallbacks when summarization fails

## Setup

### Dependencies

1. **Core transcript downloading**:
```bash
pip install youtube-transcript-api
# OR for yt-dlp approach
pip install yt-dlp
```

2. **Web application and AI summarization**:
```bash
pip install flask openai python-dotenv
```

### Environment Configuration

Create a `.env` file or set environment variables:

```bash
# Required for AI summarization
OPENAI_API_KEY=your_openai_api_key

# Optional OpenAI configuration
OPENAI_MODEL=gpt-4.1
OPENAI_MAX_TOKENS=100000
OPENAI_TEMPERATURE=0.7

# Optional proxy configuration
YOUTUBE_PROXY=proxy_ip:8080

# Optional Flask configuration
FLASK_HOST=0.0.0.0
FLASK_PORT=33079
FLASK_DEBUG=True
```

### Starting the Application

```bash
# Web application
python3 app.py

# OR using start script
./start_server.sh
```

## Usage

### Command Line Scripts

```bash
# Main implementation with proxy support
python3 download_transcript.py "https://www.youtube.com/watch?v=VIDEO_ID" [proxy_ip]

# yt-dlp alternative
python3 simple_transcript.py "https://www.youtube.com/watch?v=VIDEO_ID"

# Manual web scraping fallback
python3 download_transcript_manual.py "https://www.youtube.com/watch?v=VIDEO_ID"
```

### Web Interface

- **Home**: `http://localhost:33079/`
- **Transcript**: `http://localhost:33079/watch?v=VIDEO_ID`
- **With AI Summary**: `http://localhost:33079/watch?v=VIDEO_ID&summarize=true`

### API Endpoints

- **Transcript JSON**: `http://localhost:33079/api/transcript/VIDEO_ID`
- **Summary with Data**: `POST http://localhost:33079/api/summary` (with transcript data in body)
- **Cache Info**: `http://localhost:33079/api/cache/info`
- **Cache Cleanup**: `POST http://localhost:33079/api/cache/cleanup`

### Examples

```bash
# Command line usage
python3 download_transcript.py "https://www.youtube.com/watch?v=FjHtZnjNEBU"

# Web interface (summary generated via AJAX)
http://localhost:33079/watch?v=FjHtZnjNEBU

# API endpoints
curl http://localhost:33079/api/transcript/FjHtZnjNEBU
curl http://localhost:33079/api/cache/info

# AJAX summary request (made automatically by web interface)
curl -X POST http://localhost:33079/api/summary \
  -H "Content-Type: application/json" \
  -d '{"video_id": "FjHtZnjNEBU", "formatted_transcript": "..."}'
```

### Supported Input Formats

- Video ID: `FjHtZnjNEBU`
- Full URL: `https://www.youtube.com/watch?v=FjHtZnjNEBU`
- Short URL: `https://youtu.be/FjHtZnjNEBU`

## Project Structure

### Core Scripts
- **`download_transcript.py`** - Main implementation using `youtube-transcript-api` with proxy support
- **`simple_transcript.py`** - Alternative using `yt-dlp` for broader compatibility  
- **`download_transcript_manual.py`** - Manual web scraping fallback

### Web Application
- **`app.py`** - Flask web application with transcript viewing and AI summarization
- **`transcript_summarizer.py`** - OpenAI-powered summarization module
- **`templates/`** - HTML templates for web interface

### Configuration & Caching
- **`.env`** - Environment variables (create from examples above)
- **`CLAUDE.md`** - Development guidelines and project documentation
- **`cache/`** - Local transcript cache directory (auto-created, 24h TTL)
- **`transcript_cache.py`** - Caching module with file-based storage

## AI Summarization Structure

The AI summarization feature provides structured summaries with the following sections:

- **Overview** - Brief 2-3 sentence summary of the video content
- **Main Topics Covered** - Primary themes and subjects discussed
- **Key Takeaways & Insights** - Most important points and conclusions
- **Actionable Strategies** - Practical advice and implementable steps
- **Specific Details & Examples** - Important statistics, case studies, and examples
- **Warnings & Common Mistakes** - Pitfalls and errors to avoid
- **Resources & Next Steps** - Tools, links, and recommended follow-up actions

## Performance & Caching

### Intelligent Caching System
- **24-hour TTL**: Transcripts cached locally for 1 day
- **File-based storage**: JSON cache files in `cache/` directory
- **Automatic cleanup**: Expired files removed on startup
- **Cache statistics**: Monitor cache performance via API endpoints

### Network Considerations
- **Cloud provider IPs** are commonly blocked by YouTube
- **Proxy support** available for restricted environments via `YOUTUBE_PROXY` env var
- **Multiple fallback methods** for different network conditions
- **Reduced API calls** through intelligent caching system

### Performance Optimizations
- **AJAX summarization**: No page reloads for AI summary generation
- **Efficient transcript processing**: Uses formatted text for summarization
- **Mobile-optimized UI**: Reduced padding and responsive design
- **Chapter organization**: Structured content display for better readability