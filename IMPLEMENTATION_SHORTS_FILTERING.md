# YouTube Shorts Filtering Implementation

## Overview

This implementation adds the ability to control whether YouTube Shorts (videos ≤ 60 seconds) are imported during channel video import operations. By default, Shorts are **disabled** to focus on full-length content.

## Key Components

### 1. Database Setting (`sql/add_import_shorts_setting.sql`)

```sql
INSERT INTO import_settings (setting_key, setting_value, setting_type, description) VALUES
('import_shorts', 'false', 'boolean', 'Import YouTube Shorts (videos ≤ 60 seconds). Default: false')
```

**Default**: `false` (Shorts are NOT imported by default)

### 2. Duration Filtering (`src/youtube_api.py`)

#### New Method: `_filter_videos_by_duration(videos, import_settings)`

**Features:**
- **Efficient batching**: Processes up to 50 videos per YouTube API call
- **Conservative approach**: Includes videos with unknown duration
- **Detailed logging**: Shows filtering decisions for each video
- **Shorts definition**: Videos ≤ 60 seconds are considered Shorts

**Logic:**
```python
if import_shorts == True:
    return all_videos  # No filtering
else:
    return only_videos_longer_than_60_seconds
```

### 3. API Integration (`src/routes/api.py`)

#### Channel Import Endpoint: `POST /@<channel_handle>/import`

**New Parameter**: `import_shorts` (optional)
- **Type**: Boolean
- **Default**: Uses database setting (`false`)
- **Override**: Per-request override of global setting

**Example Usage:**
```json
{
  "max_results": 25,
  "days_back": 30,
  "import_shorts": false
}
```

### 4. Updated Method Signatures

#### `youtube_api.get_channel_videos()`
```python
def get_channel_videos(self, channel_name, max_results=5, days_back=30, import_settings_override=None)
```

**Parameters:**
- `import_settings_override`: Optional settings dictionary to override database settings

## How It Works

### 1. **Setting Retrieval**
- Database stores `import_shorts: false` by default
- API requests can override per-request with `import_shorts` parameter

### 2. **Video Collection**
- Uses existing strategies: `uploads_playlist` → `activities_api` → `search_api`
- Collects video basic information (title, video_id, publish date)

### 3. **Duration Filtering**
- Makes additional YouTube Data API calls to get `contentDetails` for duration
- Parses ISO 8601 duration format (`PT1M30S` → 90 seconds)
- Filters out videos ≤ 60 seconds if `import_shorts = false`

### 4. **Processing**
- Only filtered videos proceed to transcript extraction and AI summarization
- Saves API quota and processing time by excluding unwanted content

## Usage Examples

### Default Behavior (Shorts Disabled)
```bash
POST /@channelname/import
{
  "max_results": 20,
  "days_back": 30
}
# Result: Only videos > 60 seconds are imported
```

### Enable Shorts for Specific Request
```bash
POST /@channelname/import
{
  "max_results": 20,
  "days_back": 30,
  "import_shorts": true
}
# Result: All videos (including Shorts) are imported
```

### Change Global Default
```sql
UPDATE import_settings 
SET setting_value = 'true' 
WHERE setting_key = 'import_shorts';
# All future imports will include Shorts unless overridden
```

## Performance Considerations

### API Quota Usage
- **Additional API calls**: Duration filtering requires extra YouTube Data API calls
- **Batching optimization**: Processes up to 50 videos per API call
- **Cost-benefit**: Saves processing time on unwanted Shorts content

### Conservative Approach
- **Unknown durations**: Included rather than excluded (prevents data loss)
- **Error handling**: Falls back to including all videos if filtering fails
- **Logging**: Detailed logs help debug filtering decisions

## Benefits

1. **Content Focus**: Exclude short-form content to focus on substantial videos
2. **Processing Efficiency**: Skip transcript extraction/AI summarization for Shorts
3. **Flexible Control**: Global default + per-request override capability
4. **User Choice**: Users can still import Shorts when desired

## Technical Details

### Shorts Classification
- **Definition**: Videos with duration ≤ 60 seconds
- **YouTube Standard**: Aligns with YouTube's 60-second Shorts limit
- **Boundary Cases**: 60 seconds exactly is classified as a Short

### Error Handling
- **API failures**: Include all videos if duration data unavailable
- **Parse errors**: Include videos with unparseable durations
- **Network issues**: Graceful degradation with detailed logging

### Future Enhancements
- **Duration ranges**: Could add min/max duration filters
- **Content type detection**: Could detect other content types beyond duration
- **Caching**: Could cache duration data to reduce API calls