# YouTube Transcript Downloader & AI Summarizer

A comprehensive toolkit for downloading YouTube transcripts with multiple implementation approaches and AI-powered summarization capabilities.

## Features

### Core Functionality
- **Multiple Transcript Methods**: `youtube-transcript-api`, `yt-dlp`, and manual web scraping
- **Network Resilience**: Proxy support for cloud environments and restricted networks
- **Format Flexibility**: Accepts video IDs, full URLs, or short URLs

### Web Application
- **Clean Web Interface**: Responsive UI for viewing transcripts
- **AI-Powered Summarization**: OpenAI GPT integration for intelligent video summaries
- **RESTful API**: JSON endpoints for programmatic access
- **Real-time Processing**: Live transcript fetching and summarization

### Summarization Features
- **Structured Summaries**: Organized sections including overview, key takeaways, and actionable strategies
- **Configurable AI Models**: Support for different OpenAI models and parameters
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
- **Summary JSON**: `http://localhost:33079/api/summary/VIDEO_ID`

### Examples

```bash
# Command line usage
python3 download_transcript.py "https://www.youtube.com/watch?v=FjHtZnjNEBU"

# Web interface with summary
http://localhost:33079/watch?v=FjHtZnjNEBU&summarize=true

# API endpoints
curl http://localhost:33079/api/transcript/FjHtZnjNEBU
curl http://localhost:33079/api/summary/FjHtZnjNEBU
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

### Configuration
- **`.env`** - Environment variables (create from examples above)
- **`CLAUDE.md`** - Development guidelines and project documentation

## AI Summarization Structure

The AI summarization feature provides structured summaries with the following sections:

- **Overview** - Brief 2-3 sentence summary of the video content
- **Main Topics Covered** - Primary themes and subjects discussed
- **Key Takeaways & Insights** - Most important points and conclusions
- **Actionable Strategies** - Practical advice and implementable steps
- **Specific Details & Examples** - Important statistics, case studies, and examples
- **Warnings & Common Mistakes** - Pitfalls and errors to avoid
- **Resources & Next Steps** - Tools, links, and recommended follow-up actions

## Network Considerations

- Cloud provider IPs are commonly blocked by YouTube
- Proxy support available for restricted environments
- Multiple fallback methods for different network conditions
- Environment-based proxy configuration for flexibility