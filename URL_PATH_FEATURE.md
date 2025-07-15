# URL Path Feature Documentation

## Overview

The URL path feature adds SEO-friendly URL slugs to the YouTube Deep Summary application. Instead of using video IDs in URLs, the system now generates readable, URL-friendly paths based on video titles.

## Example URLs

**Before:**
- `/watch?v=dQw4w9WgXcQ`

**After:**
- `/watch/never-gonna-give-you-up-official-video`
- `/watch/how-to-build-a-youtube-app-with-python`
- `/watch/10-tips-for-better-code-must-watch`

## Database Changes

### New Column
- Added `url_path` column to `youtube_videos` table
- Type: `TEXT`
- Nullable: Yes (for backward compatibility)
- Indexed: Yes (for fast lookups)

### Database Schema Update
```sql
ALTER TABLE youtube_videos 
ADD COLUMN IF NOT EXISTS url_path TEXT;

CREATE INDEX IF NOT EXISTS idx_youtube_videos_url_path 
ON youtube_videos(url_path);
```

## URL Slug Generation Rules

### 1. Unicode Normalization
- Converts unicode characters to their ASCII equivalents
- Example: `café` → `cafe`

### 2. Lowercase Conversion
- All characters converted to lowercase
- Example: `Building Apps` → `building apps`

### 3. Special Character Removal
- Keeps only alphanumeric characters, spaces, hyphens, and underscores
- Example: `Python & JavaScript!` → `Python  JavaScript`

### 4. Space and Hyphen Consolidation
- Multiple spaces/hyphens become single hyphens
- Example: `Python  JavaScript` → `python-javascript`

### 5. Trimming
- Removes leading/trailing hyphens
- Example: `-python-javascript-` → `python-javascript`

### 6. Length Limiting
- Maximum 100 characters
- Truncates at word boundaries when possible
- Example: Very long title → `truncated-title-at-100-chars`

### 7. Fallback Handling
- Empty or invalid titles become `untitled-video`
- Ensures every video has a valid URL path

## Uniqueness Handling

### Duplicate Detection
- Checks for existing URL paths before saving
- Handles edge cases where titles might generate identical slugs

### Conflict Resolution
- Appends incremental numbers to ensure uniqueness
- Example: 
  - First video: `how-to-code`
  - Second video: `how-to-code-2`
  - Third video: `how-to-code-3`

### Update Safety
- When updating existing videos, excludes the current video from uniqueness checks
- Prevents unnecessary slug changes during updates

## Implementation Files

### 1. Database Migration
- **File**: `add_url_path_column.sql`
- **Purpose**: Adds the url_path column and index
- **Usage**: Run in Supabase SQL editor

### 2. Population Script
- **File**: `populate_url_paths.py`
- **Purpose**: Populates url_path for existing videos
- **Usage**: `python3 populate_url_paths.py`
- **Features**:
  - Skips videos that already have url_path
  - Handles uniqueness conflicts
  - Provides progress feedback

### 3. Database Storage Updates
- **File**: `database_storage.py`
- **New Methods**:
  - `_generate_url_slug()`: Creates URL-friendly slug from title
  - `_ensure_unique_url_slug()`: Ensures slug uniqueness
  - `get_video_by_url_path()`: Retrieves video by URL path
- **Updated Methods**:
  - `set()`: Auto-generates url_path when saving videos
  - `get_all_cached_videos()`: Includes url_path in returned data

### 4. Schema Updates
- **File**: `create_tables.sql`
- **Changes**: Added url_path column and index for new installations

### 5. Test Scripts
- **File**: `test_url_path.py`
- **Purpose**: Comprehensive testing of URL path functionality
- **Usage**: `python3 test_url_path.py`

## Installation Steps

### Step 1: Apply Database Migration
Run the following SQL in your Supabase SQL editor:
```sql
-- Add the url_path column
ALTER TABLE youtube_videos 
ADD COLUMN IF NOT EXISTS url_path TEXT;

-- Create an index for faster lookups
CREATE INDEX IF NOT EXISTS idx_youtube_videos_url_path 
ON youtube_videos(url_path);
```

### Step 2: Populate Existing Videos
```bash
python3 populate_url_paths.py
```

### Step 3: Test Installation
```bash
python3 test_url_path.py
```

## Usage Examples

### Generate URL Slug
```python
from database_storage import database_storage

# Generate a slug from a title
slug = database_storage._generate_url_slug("How to Build Amazing Apps!")
print(slug)  # Output: how-to-build-amazing-apps
```

### Get Video by URL Path
```python
from database_storage import database_storage

# Retrieve video by URL path
video = database_storage.get_video_by_url_path("how-to-build-amazing-apps")
if video:
    print(f"Found video: {video['title']}")
else:
    print("Video not found")
```

### Ensure Unique Slug
```python
from database_storage import database_storage

# Ensure slug is unique (appends numbers if needed)
unique_slug = database_storage._ensure_unique_url_slug("common-title")
print(unique_slug)  # Output: common-title or common-title-2, etc.
```

## Future Enhancements

### 1. URL Route Integration
- Add Flask routes that accept URL paths instead of video IDs
- Example: `/watch/video-title-slug` instead of `/watch?v=VIDEO_ID`

### 2. SEO Optimization
- Generate meta tags based on URL paths
- Improve search engine indexing

### 3. Custom URL Paths
- Allow users to customize URL paths for their videos
- Validate custom paths for uniqueness

### 4. URL History
- Track URL path changes for redirects
- Maintain SEO value during title updates

## Error Handling

### Database Errors
- Gracefully handles missing columns (backward compatibility)
- Provides meaningful error messages
- Fails safely without breaking existing functionality

### Edge Cases
- Empty titles → `untitled-video`
- Very long titles → Truncated to 100 characters
- Special characters → Converted to URL-safe equivalents
- Duplicate slugs → Automatic numbering

## Performance Considerations

### Database Index
- Created index on url_path column for fast lookups
- Queries by URL path are optimized for production use

### Slug Generation
- Efficient regex-based processing
- Minimal memory usage for large datasets
- Handles Unicode normalization properly

### Uniqueness Checking
- Optimized database queries
- Minimal overhead during video saves
- Batch processing friendly

## Testing

### Unit Tests
- `test_url_path.py`: Comprehensive functionality testing
- `populate_url_paths.py --test`: Slug generation testing

### Integration Tests
- Database connectivity
- Uniqueness enforcement
- Error handling

### Manual Testing
1. Generate slugs for various title formats
2. Test duplicate title handling
3. Verify database operations
4. Check backward compatibility

## Troubleshooting

### Common Issues

1. **Column doesn't exist error**
   - Solution: Apply database migration first
   - File: `add_url_path_column.sql`

2. **Duplicate slug conflicts**
   - Solution: Automatic numbering handles this
   - Check uniqueness logic in `_ensure_unique_url_slug()`

3. **Empty URL paths**
   - Solution: Fallback to `untitled-video`
   - Check title processing in `_generate_url_slug()`

### Debug Commands
```bash
# Test slug generation
python3 populate_url_paths.py --test

# Test database connectivity
python3 test_url_path.py

# Check existing video data
python3 -c "from database_storage import database_storage; print(len(database_storage.get_all_cached_videos()))"
```

## Version History

### v1.0.0
- Initial implementation
- Basic slug generation
- Database schema updates
- Population script
- Testing framework

---

For questions or issues, refer to the main project documentation or create an issue in the project repository. 