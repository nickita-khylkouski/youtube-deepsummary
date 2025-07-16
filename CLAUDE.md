# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

YouTube Deep Summary is a comprehensive toolkit for downloading YouTube transcripts with multiple implementation approaches, AI-powered summarization using GPT-4.1, and a responsive web interface with Supabase database integration. The project handles various network restrictions and provides both command-line tools and a web application with persistent storage for transcripts, summaries, memory snippets, and channel management.

## 📁 Project Structure & Documentation

**For detailed project structure and architecture documentation, see:**
- **[`.cursor/project-structure.mdc`](.cursor/project-structure.mdc)** - Comprehensive project structure with module descriptions, dependencies, and usage examples

### Quick Structure Overview

### Command-Line Tools (`/tools`)
- **`tools/download_transcript.py`** - Main implementation using `youtube-transcript-api` library with proxy support
- **`tools/simple_transcript.py`** - Alternative implementation using `yt-dlp` for broader compatibility
- **`tools/download_transcript_manual.py`** - Manual web scraping fallback (no external dependencies)

### Web Application
- **`app.py`** - Main Flask application entry point with blueprint registration and configuration

### Core Modules (`/src`)
The application follows a modular architecture with all source code organized in the `/src` directory:

#### Configuration & Infrastructure
- **`src/config.py`** - Centralized configuration management with environment variables
- **`src/database_storage.py`** - Supabase database integration for persistent storage
- **`src/legacy_file_storage.py`** - Legacy file-based storage system (deprecated, replaced by database storage)

#### Core Processing Components (Modular Architecture)
- **`src/transcript_extractor.py`** - YouTube transcript extraction with multiple methods and language fallback
- **`src/chapter_extractor.py`** - Video chapter extraction and metadata using yt-dlp
- **`src/summarizer.py`** - OpenAI GPT-4.1 powered AI summarization with chapter awareness (main implementation)
- **`src/transcript_formatter.py`** - Multiple transcript formatting options (readability, timestamps, SRT)
- **`src/snippet_manager.py`** - Memory snippets business logic (creation, grouping, filtering, validation)
- **`src/video_processing.py`** - Video processing pipeline orchestration using the above components
- **`src/transcript_summarizer.py`** - Legacy compatibility wrapper (delegates to `src/summarizer.py`)
- **`src/youtube_api.py`** - YouTube Data API integration for channel and video information

#### Chat Components (Modular Architecture)
- **`src/chat_manager.py`** - Core chat business logic (session management, message processing, AI coordination)
- **`src/conversation_context.py`** - Context building from channel summaries with length management
- **`src/chat_formatter.py`** - Message formatting, prompt creation, and response processing

#### Web Interface (`/src/routes`)
- **`src/routes/main.py`** - Main routes: home page, `/watch` redirects, favicon
- **`src/routes/api.py`** - API endpoints for transcript data, summaries, and video operations
- **`src/routes/channels.py`** - Channel management: overview, videos, summaries
- **`src/routes/videos.py`** - Video display and transcript viewing
- **`src/routes/snippets.py`** - Memory snippets management and display
- **`src/routes/chat.py`** - Channel chat interface and API endpoints (uses modular chat components)

#### Utilities
- **`src/utils/helpers.py`** - Utility functions: video ID extraction, markdown conversion, URL parsing

### Database & SQL (`/sql`)
- **`sql/create_tables.sql`** - Main database schema for Supabase setup
- **`sql/create_memory_snippets_table.sql`** - Memory snippets table creation
- **`sql/migration_*.sql`** - Database migration scripts for schema updates
- **`sql/add_*.sql`** - Column addition scripts for schema evolution
- **`sql/fix_*.sql`** - Database fixes and corrections

### Utility Scripts (`/scripts`)
- **`scripts/update_channel_handles.py`** - Update YouTube channel handles in database using YouTube Data API

### Testing (`/tests`)
- **`tests/test_chapters.py`** - Test script for debugging chapter extraction functionality

### Architecture
The system follows a **modular layered architecture** with clear separation of concerns and independent components:

#### Layer Structure
1. **Configuration Layer** (`src/config.py`): Environment variables and application settings
2. **Data Layer** (`src/utils/helpers.py`): Extract video ID from YouTube URLs using regex patterns
3. **Storage Layer** (`src/database_storage.py`): Supabase database with tables for videos, transcripts, chapters, summaries, and memory_snippets
4. **Core Processing Components** (New Modular Architecture):
   - **Transcript Extraction** (`src/transcript_extractor.py`): YouTube transcript extraction with multiple methods
   - **Chapter Extraction** (`src/chapter_extractor.py`): Video chapter extraction and metadata using yt-dlp
   - **AI Summarization** (`src/summarizer.py`): OpenAI GPT-4.1 powered summarization with chapter awareness
   - **Transcript Formatting** (`src/transcript_formatter.py`): Multiple formatting options (readability, timestamps, SRT)
5. **Orchestration Layer** (`src/video_processing.py`): Coordinates the core processing components
6. **Integration Layer** (`src/youtube_api.py`): YouTube Data API integration for channel and video information
7. **Knowledge Layer** (database + snippets routes): Memory snippets with text selection, formatting preservation, and tagging
8. **Presentation Layer** (`src/routes/`): Responsive web interface with mobile optimization, channel management, and personal knowledge base

#### Modular Architecture Benefits

**✅ Separation of Concerns**: Each module has a single, well-defined responsibility
- `transcript_extractor.py` → Only handles transcript extraction
- `chapter_extractor.py` → Only handles chapter extraction
- `summarizer.py` → Only handles AI summarization
- `transcript_formatter.py` → Only handles formatting

**✅ Independent Components**: Modules can be used independently without dependencies
```python
# Use components independently
from src.transcript_extractor import transcript_extractor
from src.chapter_extractor import chapter_extractor
from src.summarizer import summarizer
```

**✅ Easy to Test**: Each module can be tested in isolation
```python
# Test transcript extraction independently
python3 -c "from src.transcript_extractor import extract_transcript; print('✓ Available')"

# Test chapter extraction independently
python3 tests/test_chapters.py
```

**✅ Easy to Extend**: New methods can be added without affecting existing functionality
- Add new transcript extraction methods to `transcript_extractor.py`
- Add new formatting options to `transcript_formatter.py`
- Add new summarization models to `summarizer.py`

**✅ Maintainable**: Clear boundaries make code easier to understand and modify
- Bug fixes are isolated to specific modules
- Updates to one component don't affect others
- Code is easier to review and understand

**✅ Reusable**: Components can be used across different parts of the application
- API endpoints can use components directly
- Command-line tools can import and use components
- Future features can reuse existing components

#### Module Dependencies
- **`app.py`** → Imports all route blueprints and initializes Flask application
- **Route modules** → Import orchestration layer and utilities
- **Orchestration layer** (`video_processing.py`) → Coordinates core processing components
- **Core processing components** → Independent modules with minimal dependencies
- **Utilities** → Self-contained helper functions with minimal dependencies

**Key Design Principle**: **Depend on abstractions, not concretions**
- Routes depend on the orchestration layer, not individual components
- Components can be swapped or extended without changing dependent code
- Clear interfaces between modules enable easy testing and modification

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
python3 tools/download_transcript.py "https://www.youtube.com/watch?v=VIDEO_ID" [proxy_ip]

# yt-dlp version
python3 tools/simple_transcript.py "https://www.youtube.com/watch?v=VIDEO_ID"

# Manual fallback
python3 tools/download_transcript_manual.py "https://www.youtube.com/watch?v=VIDEO_ID"

# Web application (requires .env configuration)
python3 app.py

# Using startup script with proxy configuration
./start_server.sh

# Testing chapter extraction
python3 tests/test_chapters.py

# Testing modular components independently
python3 -c "from src.transcript_extractor import transcript_extractor; print('✓ Transcript extractor available')"
python3 -c "from src.chapter_extractor import chapter_extractor; print('✓ Chapter extractor available')"
python3 -c "from src.summarizer import summarizer; print('✓ AI summarizer available')"
python3 -c "from src.transcript_formatter import transcript_formatter; print('✓ Transcript formatter available')"
python3 -c "from src.snippet_manager import snippet_manager; print('✓ Snippet manager available')"
```

## Network Considerations

- Cloud provider IPs are commonly blocked by YouTube
- `download_transcript.py` supports HTTP proxy configuration (port 8080)
- `simple_transcript.py` uses yt-dlp which may have better network handling
- Manual script attempts direct web scraping but has limited success

## Key Implementation Details

### Data Processing (Modular Architecture)
- **Video ID Extraction** (`src/utils/helpers.py`): Extract 11-character YouTube video IDs from various URL formats
- **Transcript Extraction** (`src/transcript_extractor.py`): Multiple methods with language fallback
- **Chapter Extraction** (`src/chapter_extractor.py`): Video chapters and metadata using yt-dlp
- **Transcript Formatting** (`src/transcript_formatter.py`): Multiple formats (readable paragraphs, timestamps, SRT)
- **AI Summarization** (`src/summarizer.py`): Chapter-aware GPT-4.1 summaries with proper formatting
- **Orchestration** (`src/video_processing.py`): Coordinates all components in `process_video_complete()`
- **Automatic video import**: `/watch?v=VIDEO_ID` URLs automatically import videos if not found in database

### Performance Optimizations
- AJAX-based AI summarization without page reloads
- **Consolidated video import**: Eliminates duplicate import logic across multiple endpoints
- Mobile-responsive UI with optimized padding and layout
- Efficient transcript processing using pre-formatted text for AI
- **Server-side markdown rendering**: AI summaries properly formatted with HTML conversion

### Error Handling & Reliability (Modular Benefits)
- **Isolated Error Handling**: Each module handles its own errors without affecting others
- **Graceful Fallbacks**: Multiple transcript acquisition methods in `transcript_extractor.py`
- **Proxy Support**: Consistent proxy handling across `transcript_extractor.py` and `chapter_extractor.py`
- **Component-Level Recovery**: Failures in one component don't break the entire pipeline
- **Comprehensive Logging**: Each module provides detailed error messages for debugging
- **Unified Import Function**: `video_processing.py` orchestrates all components with consistent error handling

## Environment Configuration

The web application and summarization features require environment variables:

```bash
# Required for summarization
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4.1        # Optional, defaults to gpt-4.1
OPENAI_MAX_TOKENS=100000    # Optional, defaults to 100000 (NOTE: max_tokens is now ignored to avoid API limits)
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
# Run SQL commands from sql/create_tables.sql in your Supabase SQL editor
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
python3 tests/test_chapters.py

# Test basic transcript functionality
python3 tools/download_transcript.py "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

# Test modular components
python3 -c "from src.transcript_extractor import transcript_extractor; print('✓ Transcript extractor available')"
python3 -c "from src.chapter_extractor import chapter_extractor; print('✓ Chapter extractor available')"
python3 -c "from src.summarizer import summarizer; print('✓ AI summarizer available')"
python3 -c "from src.transcript_formatter import transcript_formatter; print('✓ Transcript formatter available')"

# Test all components together
python3 -c "from src.video_processing import video_processor; print('✓ Video processor with modular components available')"
```

## Development Best Practices (Modular Architecture)

### When Adding New Features

**✅ Follow the modular architecture principles:**

1. **Single Responsibility**: Each module should have one clear purpose
2. **Dependency Injection**: Components should be injected, not directly instantiated
3. **Interface Segregation**: Modules should depend on abstractions, not concrete implementations
4. **Open/Closed Principle**: Modules should be open for extension, closed for modification

### Code Organization Guidelines

**✅ Adding New Processing Methods:**
- **Transcript extraction methods** → Add to `src/transcript_extractor.py`
- **Chapter extraction methods** → Add to `src/chapter_extractor.py`
- **Summarization models** → Add to `src/summarizer.py`
- **Formatting options** → Add to `src/transcript_formatter.py`
- **Snippet processing methods** → Add to `src/snippet_manager.py`

**✅ Adding New API Endpoints:**
- RESTful endpoints → Add to appropriate blueprint in `src/routes/`
- Use the orchestration layer (`video_processing.py`) for complex operations
- Don't call individual components directly from routes

**✅ Adding New Utilities:**
- Helper functions → Add to `src/utils/helpers.py`
- Configuration options → Add to `src/config.py`
- Database operations → Add to `src/database_storage.py`

### Testing Strategy

**✅ Unit Testing:**
```python
# Test individual components in isolation
from src.transcript_extractor import TranscriptExtractor
from src.chapter_extractor import ChapterExtractor
from src.summarizer import TranscriptSummarizer
from src.transcript_formatter import TranscriptFormatter
from src.snippet_manager import SnippetManager

# Each component can be tested independently
extractor = TranscriptExtractor()
chapters = ChapterExtractor()
summarizer = TranscriptSummarizer()
formatter = TranscriptFormatter()
snippet_mgr = SnippetManager()
```

**✅ Integration Testing:**
```python
# Test component interactions through the orchestration layer
from src.video_processing import VideoProcessor

processor = VideoProcessor()
result = processor.process_video_complete('VIDEO_ID')
```

### Error Handling Best Practices

**✅ Component-Level Error Handling:**
- Each module handles its own errors and provides meaningful error messages
- Use try-catch blocks within components to handle specific error scenarios
- Log errors with sufficient context for debugging

**✅ Graceful Degradation:**
- If one component fails, the system should continue with available functionality
- Provide fallback options when possible (e.g., multiple transcript extraction methods)
- Return meaningful error responses to users

### Extending the System

**✅ Adding New Transcript Sources:**
```python
# Add new methods to src/transcript_extractor.py
class TranscriptExtractor:
    def extract_transcript_from_new_source(self, video_id: str) -> List[Dict]:
        # Implementation for new source
        pass
```

**✅ Adding New Summarization Models:**
```python
# Add new methods to src/summarizer.py (main implementation)
class TranscriptSummarizer:
    def summarize_with_new_model(self, transcript_content: str) -> str:
        # Implementation for new model
        pass

# Legacy wrapper in src/transcript_summarizer.py automatically delegates to new implementation
```

**✅ Adding New Output Formats:**
```python
# Add new methods to src/transcript_formatter.py
class TranscriptFormatter:
    def format_as_new_format(self, transcript: List[Dict]) -> str:
        # Implementation for new format
        pass
```

**✅ Adding New Snippet Processing Methods:**
```python
# Add new methods to src/snippet_manager.py
class SnippetManager:
    def process_snippets_with_new_logic(self, snippets: List[Dict]) -> List[Dict]:
        # Implementation for new processing logic
        pass
    
    def export_snippets_to_new_format(self, snippets: List[Dict]) -> str:
        # Implementation for new export format
        pass
```

### Performance Considerations

**✅ Modular Performance Benefits:**
- **Lazy Loading**: Components are only loaded when needed
- **Caching**: Each component can implement its own caching strategy
- **Parallel Processing**: Independent components can be processed in parallel
- **Resource Management**: Components manage their own resources (API clients, connections)

### Maintenance Guidelines

**✅ Regular Maintenance Tasks:**
- **Component Updates**: Update individual components without affecting others
- **Dependency Management**: Keep component dependencies isolated and up-to-date
- **Code Reviews**: Review components independently for better focus
- **Documentation**: Maintain component-level documentation with usage examples

**✅ Monitoring and Debugging:**
- **Component Health**: Monitor each component's health independently
- **Error Tracking**: Track errors by component for better debugging
- **Performance Metrics**: Measure performance of individual components
- **Logging**: Use structured logging with component identification

### Migration Path

**✅ From Legacy Code:**
- Summarization logic consolidated from `transcript_summarizer.py` to `src/summarizer.py`
- Legacy `transcript_summarizer.py` now serves as a compatibility wrapper
- All other legacy functions have been migrated to appropriate modules
- Existing functionality is preserved while gaining modular benefits
- No breaking changes for existing code using the legacy interface

**✅ Future Enhancements:**
- Easy to add new AI models to `summarizer.py` (single source of truth for summarization)
- Simple to add new transcript sources to `transcript_extractor.py`
- Straightforward to add new output formats to `transcript_formatter.py`
- Clear path for adding new processing steps to the pipeline
- Legacy compatibility maintained automatically through delegation pattern

This modular architecture provides a solid foundation for scalable, maintainable, and extensible development of the YouTube Deep Summary application.