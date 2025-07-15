# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

YouTube Deep Summary is a comprehensive toolkit for downloading YouTube transcripts with multiple implementation approaches, AI-powered summarization using GPT-4.1, and a responsive web interface with Supabase database integration. The project handles various network restrictions and provides both command-line tools and a web application with persistent storage for transcripts, summaries, memory snippets, and channel management.

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
2. **Storage Layer**: Supabase database with tables for videos, transcripts, chapters, summaries, and memory_snippets
3. **Acquisition Layer**: Download transcript and video metadata using multiple methods
4. **Processing Layer**: Format transcript into readable paragraphs with chapter organization
5. **AI Layer**: Generate structured summaries using GPT-4.1 via AJAX
6. **Knowledge Layer**: Memory snippets with text selection, formatting preservation, and tagging
7. **Presentation Layer**: Responsive web interface with mobile optimization, channel management, and personal knowledge base

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
- **Consolidated import logic**: Single `process_video_complete()` function handles all video imports
- **Automatic video import**: `/watch?v=VIDEO_ID` URLs automatically import videos if not found in database

### Performance Optimizations
- AJAX-based AI summarization without page reloads
- **Consolidated video import**: Eliminates duplicate import logic across multiple endpoints
- Mobile-responsive UI with optimized padding and layout
- Efficient transcript processing using pre-formatted text for AI
- **Server-side markdown rendering**: AI summaries properly formatted with HTML conversion

### Error Handling & Reliability
- Graceful fallbacks for network connectivity issues
- Multiple transcript acquisition methods (youtube-transcript-api, yt-dlp, manual)
- Proxy support for restricted network environments
- Comprehensive error messaging and cache failure recovery
- **Unified import function**: Consistent error handling across all import operations

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

# Required for importing channel videos (YouTube Data API v3)
YOUTUBE_API_KEY=your_youtube_api_key

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
- **`/watch?v=VIDEO_ID`** - **Auto-import and redirect**: Automatically imports videos if not found, then redirects to SEO-friendly URLs
- **`/@handle/video-title-slug`** - SEO-friendly video pages with clickable channel names linking to channel overview
- **`/memory-snippets`** - Personal knowledge base with saved text snippets grouped by video
- **`/channels`** - Browse all channels with saved videos
- **`/@handle`** - Channel overview page with statistics, navigation, and recent videos
- **`/@handle/videos`** - View all videos from a specific channel by handle
- **`/@handle/summaries`** - View all summaries from a specific channel by handle
- **`/@handle/snippets`** - View memory snippets from a specific channel by handle
- **`/videos`** - Videos listing and management
- **Mobile-responsive design** with optimized padding and collapsible elements
- **Handle-based routing**: Clean URLs using channel handles (/@channelname) instead of IDs

**Recent Improvements**:
- **Automatic video import**: `/watch?v=VIDEO_ID` URLs now automatically import videos and redirect to SEO-friendly URLs
- **Clickable channel names**: Channel names on video pages are now clickable links to channel overview pages
- **Properly formatted AI summaries**: Server-side markdown conversion ensures summaries display with correct formatting
- **Breadcrumb navigation**: Easy navigation between channel overview and sub-pages
- **Dual view modes**: Toggle between readable paragraphs and detailed timestamps
- **AJAX summarization**: Generate AI summaries without page reloads
- **Memory snippets**: Text selection from summaries and transcripts with formatting preservation

### API Endpoints
- **`GET /api/transcript/VIDEO_ID`** - **Auto-import enabled**: JSON API for transcript data with automatic video import if not found
- **`POST /api/summary`** - Generate summary from provided transcript data (efficient)
- **`GET /api/memory-snippets`** - Retrieve saved memory snippets with optional video filtering
- **`POST /api/memory-snippets`** - Save new memory snippet with text, context, and tags
- **`DELETE /api/memory-snippets/<snippet_id>`** - Delete specific memory snippet
- **`PUT /api/memory-snippets/<snippet_id>/tags`** - Update tags for specific memory snippet
- **`POST /api/@handle/import`** - Import latest videos from a YouTube channel with transcripts and AI summaries
- **`GET /api/cache/info`** - Legacy cache statistics (deprecated)
- **`POST /api/cache/cleanup`** - Legacy cache cleanup (deprecated)
- **`GET /api/storage/stats`** - Database storage statistics and metrics

**Import Logic Consolidation**: All video import operations now use the unified `process_video_complete()` function, ensuring consistent behavior across `/watch` routes, API endpoints, and channel imports.

### Advanced Features
- **Chapter Organization**: Automatic detection and display of video chapters
- **Video Metadata**: Title, thumbnail, duration, uploader information
- **Persistent Storage**: Supabase database with tables for channels, videos, transcripts, chapters, summaries, and memory_snippets
- **Memory Snippets**: Personal knowledge base with text selection, HTML formatting preservation, and tagging system
- **Channel Overview Pages**: Dedicated channel hubs with statistics, navigation cards, and recent videos display
- **Channel Management**: Browse videos and summaries organized by YouTube channels using handle-based routing
- **Channel Video Import**: Import latest videos from YouTube channels with automatic transcript and AI summary generation
- **Handle-Based URLs**: Clean, user-friendly URLs using channel handles (/@channelname) instead of channel IDs
- **Breadcrumb Navigation**: Consistent navigation flow with breadcrumbs linking back to channel overview
- **Proxy Support**: Configurable proxy for both transcript and chapter extraction

### Channel Overview Architecture
- **Handle-Based Routing**: All channel URLs use handles (/@channelname) for clean, user-friendly URLs
- **Central Hub Design**: Each channel has a dedicated overview page serving as the main entry point
- **Statistics Dashboard**: Real-time counts of videos, AI summaries, and memory snippets with color-coded cards
- **Navigation Cards**: Interactive cards with hover effects linking to videos, summaries, and snippets
- **Recent Videos Grid**: Visual display of latest 6 videos with thumbnails and metadata
- **Channel Actions**: Import latest videos and direct links to YouTube channel
- **Breadcrumb Navigation**: Consistent navigation flow from sub-pages back to channel overview
- **Responsive Design**: Mobile-optimized layout with proper CSS breakpoints and transitions
- **Conditional Display**: Disabled cards for sections with no content (summaries/snippets)
- **Error Handling**: 404 responses for non-existent channels with proper error pages

#### URL Structure
```
/@handle              → Channel Overview (main hub)
/@handle/videos       → Videos List with breadcrumbs
/@handle/summaries    → AI Summaries with breadcrumbs  
/@handle/snippets     → Memory Snippets with breadcrumbs
```

#### Navigation Flow
1. `/channels` - Browse all channels with overview links
2. `/@handle` - Channel hub with statistics and navigation
3. Sub-pages with breadcrumb navigation back to overview
4. Individual content items (videos, summaries, snippets)

### AI Summarization Features
- **GPT-4.1 Integration**: Latest OpenAI model with improved context understanding
- **Structured summary format** with organized sections:
  - Overview, Main Topics, Key Takeaways & Insights
  - Actionable Strategies, Specific Details & Examples
  - Warnings & Common Mistakes, Resources & Next Steps
- **Efficient processing**: Uses pre-formatted transcript data to avoid redundant downloads
- **Proper markdown rendering**: Server-side conversion of markdown to HTML for proper formatting
- **Bullet point processing**: Automatic conversion of bullet points (`•`) to proper HTML lists
- **Consistent formatting**: Both individual video pages and channel summary pages use unified markdown processing

## Database Schema

The application uses six main tables in Supabase:

### youtube_channels
- **channel_id** (VARCHAR 24, unique) - YouTube channel identifier (UCxxxxx format)
- **channel_name** (TEXT) - Display name of the channel
- **handle** (TEXT) - Channel handle for clean URLs (@channelname format)
- **channel_url, channel_description** - Channel metadata
- **subscriber_count, video_count** - Channel statistics
- **thumbnail_url** - Channel avatar/thumbnail
- **created_at, updated_at** - Timestamps

### youtube_videos
- **video_id** (VARCHAR 11, unique) - YouTube video identifier
- **channel_id** (FK to youtube_channels) - Links to channel
- **title, uploader, duration, thumbnail_url** - Video metadata (uploader kept for backward compatibility)
- **published_at** - When video was published on YouTube
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

### memory_snippets
- **video_id** (FK to youtube_videos) - Links to video
- **snippet_text** (TEXT) - Selected text with preserved HTML formatting
- **context_before, context_after** (TEXT) - Surrounding text context
- **tags** (TEXT[]) - Array of custom tags for organization
- **created_at, updated_at** - Timestamps

## Testing

```bash
# Test chapter extraction functionality
python3 test_chapters.py

# Test basic transcript functionality
python3 download_transcript.py "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
```