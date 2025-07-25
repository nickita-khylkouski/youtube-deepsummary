"""
YouTube API integration module
"""
import os
from datetime import datetime, timedelta

try:
    from googleapiclient.discovery import build
    YOUTUBE_API_AVAILABLE = True
except ImportError:
    YOUTUBE_API_AVAILABLE = False
    print("Warning: google-api-python-client not available. Install with: pip install google-api-python-client")

from .config import Config
from .utils.helpers import extract_channel_id_or_name


class YouTubeAPI:
    """YouTube Data API wrapper"""
    
    def __init__(self):
        self.service = None
        if YOUTUBE_API_AVAILABLE and Config.YOUTUBE_API_KEY:
            try:
                self.service = build('youtube', 'v3', developerKey=Config.YOUTUBE_API_KEY)
            except Exception as e:
                print(f"Failed to initialize YouTube API service: {e}")
    
    def is_available(self):
        """Check if YouTube API is available and configured"""
        return self.service is not None
    
    def get_channel_info(self, channel_id):
        """Get channel information from YouTube API (handle, title, description)"""
        if not self.service:
            return None
        
        try:
            # Fetch channel information including handle, title, and description
            channel_request = self.service.channels().list(
                part='snippet,brandingSettings',
                id=channel_id
            )
            channel_response = channel_request.execute()
            
            if channel_response.get('items'):
                item = channel_response['items'][0]
                
                # Initialize result dictionary
                channel_info = {
                    'handle': None,
                    'title': None,
                    'description': None,
                    'thumbnail_url': None
                }
                
                # Get basic info from snippet
                if 'snippet' in item:
                    snippet = item['snippet']
                    channel_info['title'] = snippet.get('title')
                    channel_info['description'] = snippet.get('description')
                    
                    # Get thumbnail URL (prefer high quality, fallback to medium, then default)
                    thumbnails = snippet.get('thumbnails', {})
                    if 'high' in thumbnails:
                        channel_info['thumbnail_url'] = thumbnails['high']['url']
                    elif 'medium' in thumbnails:
                        channel_info['thumbnail_url'] = thumbnails['medium']['url']
                    elif 'default' in thumbnails:
                        channel_info['thumbnail_url'] = thumbnails['default']['url']
                    
                    # Try to get handle from snippet.customUrl (most common location)
                    if 'customUrl' in snippet:
                        custom_url = snippet['customUrl']
                        if custom_url and custom_url.startswith('@'):
                            channel_info['handle'] = custom_url
                
                # Check brandingSettings if no handle found
                if not channel_info['handle'] and 'brandingSettings' in item:
                    if 'channel' in item['brandingSettings']:
                        branding_channel = item['brandingSettings']['channel']
                        if 'customUrl' in branding_channel:
                            custom_url = branding_channel['customUrl']
                            if custom_url and custom_url.startswith('@'):
                                channel_info['handle'] = custom_url
                
                return channel_info
            
            return None
            
        except Exception as e:
            print(f"Error fetching channel info for {channel_id}: {e}")
            return None
    
    def get_channel_handle(self, channel_id):
        """Get channel handle from YouTube API (backward compatibility)"""
        channel_info = self.get_channel_info(channel_id)
        return channel_info['handle'] if channel_info else None
    
    def get_video_info(self, video_id):
        """Get comprehensive video information from YouTube Data API"""
        if not self.service:
            return None
        
        try:
            # Request comprehensive video information
            video_request = self.service.videos().list(
                part='snippet,contentDetails,statistics',
                id=video_id
            )
            video_response = video_request.execute()
            
            if not video_response.get('items'):
                return None
            
            item = video_response['items'][0]
            snippet = item.get('snippet', {})
            content_details = item.get('contentDetails', {})
            statistics = item.get('statistics', {})
            
            # Parse duration from ISO 8601 format (PT4M13S -> 253 seconds)
            duration_seconds = None
            if 'duration' in content_details:
                duration_seconds = self._parse_iso8601_duration(content_details['duration'])
            
            # Get the best thumbnail URL
            thumbnail_url = None
            thumbnails = snippet.get('thumbnails', {})
            # Priority: maxresdefault > high > medium > default
            for quality in ['maxresdefault', 'high', 'medium', 'default']:
                if quality in thumbnails:
                    thumbnail_url = thumbnails[quality]['url']
                    break
            
            # Parse published date
            published_at = snippet.get('publishedAt')
            upload_date = None
            if published_at:
                try:
                    from datetime import datetime
                    # Convert from ISO format to YYYYMMDD format (yt-dlp compatible)
                    dt = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
                    upload_date = dt.strftime('%Y%m%d')
                except:
                    upload_date = published_at
            
            return {
                'title': snippet.get('title', 'Unknown Title'),
                'description': snippet.get('description', ''),
                'channel_name': snippet.get('channelTitle', 'Unknown Channel'),
                'channel_id': snippet.get('channelId'),
                'duration': duration_seconds,
                'upload_date': upload_date,
                'published_at': published_at,
                'thumbnail': thumbnail_url,
                'tags': snippet.get('tags', []),
                'category_id': snippet.get('categoryId'),
                'view_count': int(statistics.get('viewCount', 0)) if statistics.get('viewCount') else None,
                'like_count': int(statistics.get('likeCount', 0)) if statistics.get('likeCount') else None,
                'comment_count': int(statistics.get('commentCount', 0)) if statistics.get('commentCount') else None,
                'definition': content_details.get('definition'),  # 'hd' or 'sd'
                'caption': content_details.get('caption') == 'true',  # Boolean
                'licensed_content': content_details.get('licensedContent') == 'true',
                'api_source': 'youtube_data_api'
            }
            
        except Exception as e:
            print(f"Error fetching video info from YouTube Data API for {video_id}: {e}")
            return None
    
    def _parse_iso8601_duration(self, duration_str):
        """
        Parse ISO 8601 duration string (PT4M13S) to seconds
        
        Args:
            duration_str: ISO 8601 duration string like 'PT4M13S'
            
        Returns:
            Duration in seconds (int) or None if parsing fails
        """
        import re
        
        if not duration_str:
            return None
        
        # Pattern to match PT1H2M3S, PT2M3S, PT3S, etc.
        pattern = r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?'
        match = re.match(pattern, duration_str)
        
        if not match:
            return None
        
        hours = int(match.group(1)) if match.group(1) else 0
        minutes = int(match.group(2)) if match.group(2) else 0
        seconds = int(match.group(3)) if match.group(3) else 0
        
        return hours * 3600 + minutes * 60 + seconds
    
    def get_channel_videos(self, channel_name, max_results=5, days_back=30, import_settings_override=None):
        """Get latest videos from a channel using YouTube Data API within specified time range"""
        if not self.service:
            raise Exception("YouTube Data API not available or not configured")
        
        try:
            # Get import settings (use override if provided)
            from .database_storage import database_storage
            if import_settings_override:
                import_settings = import_settings_override
            else:
                import_settings = database_storage.get_import_settings()
            
            # Apply settings if available
            if import_settings:
                # Ensure proper type conversion to prevent comparison errors
                max_results_limit = int(import_settings.get('max_results_limit', 50))
                max_results = min(max_results, max_results_limit)
                if import_settings.get('log_import_operations', True):
                    print(f"Using import settings: max_results={max_results}, days_back={days_back}")
            
            # First, try to get the channel ID from the database
            actual_channel_id = None
            
            # Check if we have a channel record with this name
            channel_info = database_storage.get_channel_by_name(channel_name)
            if channel_info:
                actual_channel_id = channel_info['channel_id']
                print(f"Found channel ID {actual_channel_id} from database for channel {channel_name}")
            else:
                # Try to find an existing video from this channel to get the channel ID
                existing_videos = database_storage.get_videos_by_channel(channel_name=channel_name)
                if existing_videos:
                    # Use yt-dlp or video info to try to get channel ID from an existing video
                    sample_video_id = existing_videos[0]['video_id']
                    try:
                        # Try to extract channel info from existing video
                        video_request = self.service.videos().list(
                            part='snippet',
                            id=sample_video_id
                        )
                        video_response = video_request.execute()
                        if video_response.get('items'):
                            actual_channel_id = video_response['items'][0]['snippet']['channelId']
                            print(f"Found channel ID {actual_channel_id} from existing video {sample_video_id}")
                            
                            # Get channel information if available
                            channel_info = self.get_channel_info(actual_channel_id)
                            
                            # Create/update channel record
                            database_storage._ensure_channel_exists(actual_channel_id, channel_name, channel_info)
                    except Exception as e:
                        print(f"Could not get channel ID from existing video: {e}")
            
            # If we still don't have channel ID, try different search approaches
            if not actual_channel_id:
                channel_id, name_type = extract_channel_id_or_name(channel_name)
                
                if name_type == 'id':
                    actual_channel_id = channel_id
                else:
                    # Try exact channel name search first
                    search_request = self.service.search().list(
                        part='snippet',
                        q=f'"{channel_name}"',  # Use quotes for exact match
                        type='channel',
                        maxResults=5  # Get more results to find exact match
                    )
                    search_response = search_request.execute()
                    
                    print(f"Search returned {len(search_response.get('items', []))} results for '{channel_name}'")
                    for i, item in enumerate(search_response.get('items', [])):
                        print(f"  {i+1}. {item['snippet']['title']} (ID: {item['id']['channelId']})")
                    
                    # Look for exact match in channel titles
                    best_match = None
                    exact_match = None
                    
                    for item in search_response.get('items', []):
                        item_title = item['snippet']['title']
                        
                        # Check for exact match (case-insensitive)
                        if item_title.lower() == channel_name.lower():
                            exact_match = item
                            print(f"Found exact channel match: {item_title} -> {item['id']['channelId']}")
                            break
                        
                        # Check for close match (contains the search term)
                        elif channel_name.lower() in item_title.lower() or item_title.lower() in channel_name.lower():
                            if not best_match:
                                best_match = item
                                print(f"Found potential match: {item_title} -> {item['id']['channelId']}")
                    
                    if exact_match:
                        actual_channel_id = exact_match['id']['channelId']
                    elif best_match:
                        actual_channel_id = best_match['id']['channelId']
                        print(f"Using best match: {best_match['snippet']['title']} -> {actual_channel_id}")
                    elif search_response.get('items'):
                        # Fallback to first result
                        actual_channel_id = search_response['items'][0]['id']['channelId']
                        found_name = search_response['items'][0]['snippet']['title']
                        print(f"Using first search result: {found_name} -> {actual_channel_id}")
                    
                    if not actual_channel_id:
                        raise Exception(f"Channel '{channel_name}' not found")
            
            # Now get the latest videos from the specific channel using the channel ID
            print(f"Fetching videos for channel ID: {actual_channel_id}")
            
            # Get import strategy from settings
            strategy = import_settings.get('import_strategy', 'uploads_playlist') if import_settings else 'uploads_playlist'
            
            if import_settings.get('log_import_operations', True):
                print(f"Using import strategy: {strategy}")
            
            # Use only the selected primary strategy (no fallbacks)
            fetch_size = self._calculate_fetch_size(max_results, import_settings)
            videos = self._try_import_strategy(strategy, actual_channel_id, channel_name, fetch_size, days_back)
            
            if videos:
                # Apply duration filtering based on import_shorts setting
                duration_filtered = self._filter_videos_by_duration(videos, import_settings)
                
                # Filter out existing videos and limit to target amount
                filter_result = self._filter_existing_videos(duration_filtered, import_settings, max_results)
                
                # Return both videos and metadata
                return {
                    'videos': filter_result['videos'],
                    'metadata': {
                        'total_found': filter_result['total_found'],
                        'existing_count': filter_result['existing_count'],
                        'new_count': filter_result['new_count'],
                        'strategy_used': strategy
                    }
                }
            
            # If the strategy failed, return empty result with metadata
            print(f"Import strategy '{strategy}' found no videos")
            return {
                'videos': [],
                'metadata': {
                    'total_found': 0,
                    'existing_count': 0,
                    'new_count': 0,
                    'strategy_used': strategy
                }
            }
            
        except Exception as e:
            print(f"Error fetching channel videos: {e}")
            raise Exception(f"Failed to fetch videos from channel: {str(e)}")

    def _try_import_strategy(self, strategy, channel_id, channel_name, max_results, days_back):
        """Try a specific import strategy and return videos if successful"""
        try:
            if strategy == 'uploads_playlist':
                return self._try_uploads_playlist_strategy(channel_id, channel_name, max_results, days_back)
            elif strategy == 'activities_api':
                return self._try_activities_api_strategy(channel_id, channel_name, max_results, days_back)
            elif strategy == 'search_api':
                return self._try_search_api_strategy(channel_id, channel_name, max_results, days_back)
            else:
                print(f"Unknown import strategy: {strategy}")
                return []
        except Exception as e:
            print(f"Strategy {strategy} failed: {e}")
            return []

    def _try_uploads_playlist_strategy(self, channel_id, channel_name, max_results, days_back):
        """Try to get videos using uploads playlist strategy with date filtering"""
        try:
            # Get import settings for logging
            from .database_storage import database_storage
            import_settings = database_storage.get_import_settings()
            if not import_settings:
                import_settings = {}
            channel_request = self.service.channels().list(
                part='contentDetails',
                id=channel_id
            )
            channel_response = channel_request.execute()
            
            if channel_response.get('items'):
                uploads_playlist_id = channel_response['items'][0]['contentDetails']['relatedPlaylists']['uploads']
                print(f"Found uploads playlist: {uploads_playlist_id}")
                
                # Calculate cutoff date for filtering
                cutoff_date = datetime.utcnow() - timedelta(days=days_back)
                print(f"Filtering videos published after: {cutoff_date.isoformat()}")
                
                # 🚀 PROPER PAGINATION: Fetch videos using nextPageToken with smart stopping
                videos = []
                next_page_token = None
                pages_fetched = 0
                max_pages = 20  # Safety limit to prevent infinite loops
                consecutive_existing_videos = 0  # Track consecutive existing videos for early stopping
                
                print(f"📄 Starting pagination to find videos within {days_back} days...")
                
                while pages_fetched < max_pages:
                    # Fetch 50 videos per page (max allowed)
                    playlist_request = self.service.playlistItems().list(
                        part='snippet',
                        playlistId=uploads_playlist_id,
                        maxResults=50,  # Always use max to minimize API calls
                        pageToken=next_page_token
                    )
                    playlist_response = playlist_request.execute()
                    pages_fetched += 1
                    
                    current_page_videos = []
                    videos_beyond_cutoff = 0
                    
                    for item in playlist_response.get('items', []):
                        video_id = item['snippet']['resourceId']['videoId']
                        snippet = item['snippet']
                        
                        # Parse published date and check if it's within the time range
                        published_at = snippet.get('publishedAt', '')
                        include_video = True
                        
                        if published_at:
                            try:
                                # Parse ISO format: "2024-01-15T10:30:00Z"
                                published_date = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
                                # Convert to UTC for comparison (remove timezone info)
                                published_date_utc = published_date.replace(tzinfo=None)
                                
                                # Check if video is within date range
                                if published_date_utc < cutoff_date:
                                    videos_beyond_cutoff += 1
                                    include_video = False
                                    if import_settings.get('log_import_operations', True):
                                        print(f"Excluding video {video_id}: published {published_at} (before cutoff {cutoff_date.isoformat()})")
                                else:
                                    if import_settings.get('log_import_operations', True):
                                        print(f"Including video {video_id}: published {published_at} (after cutoff {cutoff_date.isoformat()})")
                                    
                            except Exception as e:
                                print(f"Could not parse date {published_at} for video {video_id}: {e}")
                                # If we can't parse the date, include the video to be safe
                                include_video = True
                        
                        if include_video:
                            # Check if this video already exists for early stopping optimization
                            from .database_storage import database_storage
                            existing_video = database_storage.get(video_id)
                            
                            current_page_videos.append({
                                'video_id': video_id,
                                'title': snippet.get('title', ''),
                                'description': snippet.get('description', ''),
                                'published_at': published_at,
                                'thumbnail_url': snippet.get('thumbnails', {}).get('medium', {}).get('url', ''),
                                'channel_name': snippet.get('channelTitle', channel_name),
                                'channel_id': channel_id
                            })
                            
                            # Track consecutive existing videos for early stopping
                            if existing_video:
                                consecutive_existing_videos += 1
                            else:
                                consecutive_existing_videos = 0  # Reset counter when we find a new video
                    
                    videos.extend(current_page_videos)
                    print(f"📄 Page {pages_fetched}: Found {len(current_page_videos)} videos in date range, {videos_beyond_cutoff} beyond cutoff")
                    
                    # Check if we should continue paginating
                    next_page_token = playlist_response.get('nextPageToken')
                    
                    # Stop conditions:
                    # 1. No more pages
                    # 2. All videos on this page were beyond cutoff (we've gone too far back)
                    # 3. We have enough videos within the date range (early stopping for efficiency)
                    # 4. Too many consecutive existing videos (likely all remaining videos are already imported)
                    if not next_page_token:
                        print(f"📄 No more pages available")
                        break
                    elif videos_beyond_cutoff == len(playlist_response.get('items', [])):
                        print(f"📄 All videos on page {pages_fetched} are beyond cutoff date - stopping pagination")
                        break
                    elif len(videos) >= max_results:  # Stop as soon as we have enough videos
                        print(f"📄 Found enough videos ({len(videos)}) for target ({max_results}) - stopping pagination early")
                        break
                    elif consecutive_existing_videos >= 10 and max_results <= 10:  # For small requests, stop if we hit many existing videos
                        print(f"📄 Found {consecutive_existing_videos} consecutive existing videos for small request - stopping pagination early")
                        break
                
                print(f"📄 Pagination complete: {pages_fetched} pages fetched, {len(videos)} total videos in date range")
                
                if videos:
                    print(f"Found {len(videos)} videos from uploads playlist within {days_back} days")
                    return videos
                else:
                    print(f"No videos found in uploads playlist within {days_back} days")
                    
        except Exception as e:
            print(f"Uploads playlist method failed: {e}")
        
        return []

    def _try_activities_api_strategy(self, channel_id, channel_name, max_results, days_back):
        """Try to get videos using activities API strategy"""
        try:
            activities_request = self.service.activities().list(
                part='snippet,contentDetails',
                channelId=channel_id,
                maxResults=max_results,
                publishedAfter=(datetime.utcnow() - timedelta(days=days_back)).isoformat() + 'Z'
            )
            activities_response = activities_request.execute()
            
            videos = []
            for item in activities_response.get('items', []):
                if (item['snippet']['type'] == 'upload' and 
                    'contentDetails' in item and 
                    'upload' in item['contentDetails']):
                    
                    video_id = item['contentDetails']['upload']['videoId']
                    snippet = item['snippet']
                    
                    videos.append({
                        'video_id': video_id,
                        'title': snippet.get('title', ''),
                        'description': snippet.get('description', ''),
                        'published_at': snippet.get('publishedAt', ''),
                        'thumbnail_url': snippet.get('thumbnails', {}).get('medium', {}).get('url', ''),
                        'channel_name': snippet.get('channelTitle', channel_name),
                        'channel_id': channel_id
                    })
            
            if videos:
                print(f"Found {len(videos)} recent uploads using activities API")
                return videos
                
        except Exception as e:
            print(f"Activities API failed: {e}")
        
        return []

    def _try_search_api_strategy(self, channel_id, channel_name, max_results, days_back):
        """Try to get videos using search API strategy"""
        try:
            search_request = self.service.search().list(
                part='snippet',
                channelId=channel_id,
                type='video',
                order='date',
                maxResults=max_results,
                publishedAfter=(datetime.utcnow() - timedelta(days=days_back)).isoformat() + 'Z'
            )
            search_response = search_request.execute()
            
            videos = []
            for item in search_response.get('items', []):
                video_id = item['id']['videoId']
                snippet = item['snippet']
                
                # Double-check that this video is actually from the right channel
                if snippet.get('channelTitle', '').strip().lower() == channel_name.strip().lower():
                    videos.append({
                        'video_id': video_id,
                        'title': snippet.get('title', ''),
                        'description': snippet.get('description', ''),
                        'published_at': snippet.get('publishedAt', ''),
                        'thumbnail_url': snippet.get('thumbnails', {}).get('medium', {}).get('url', ''),
                        'channel_name': snippet.get('channelTitle', channel_name),
                        'channel_id': channel_id
                    })
            
            if videos:
                print(f"Found {len(videos)} videos using search API")
                return videos
                
        except Exception as e:
            print(f"Search API failed: {e}")
        
        return []

    def _calculate_fetch_size(self, target_new_videos, import_settings):
        """Calculate how many videos to fetch initially to account for existing ones being filtered out"""
        try:
            skip_existing_videos = import_settings.get('skipExistingVideos', import_settings.get('skip_existing_videos', True))
            
            if not skip_existing_videos:
                # If not filtering existing videos, fetch exactly what's requested
                return target_new_videos
            
            # For channels with many existing videos, we need to fetch more to find new ones
            # Use a more aggressive multiplier for larger requests
            if target_new_videos <= 10:
                multiplier = 3  # Fetch 3x for small requests
            elif target_new_videos <= 20:
                multiplier = 4  # Fetch 4x for medium requests  
            else:
                multiplier = 5  # Fetch 5x for large requests
            
            fetch_size = min(target_new_videos * multiplier, 200)  # Increased max from 100 to 200
            
            if import_settings.get('log_import_operations', True):
                print(f"📊 Fetch strategy: targeting {target_new_videos} new videos, fetching {fetch_size} total to account for existing videos")
            
            return fetch_size
            
        except Exception as e:
            print(f"Error calculating fetch size: {e}")
            return target_new_videos


    def _filter_existing_videos(self, videos, import_settings, target_new_videos):
        """Filter out existing videos and return up to target_new_videos new videos with metadata"""
        try:
            # Check if skip_existing_videos is enabled
            skip_existing_videos = import_settings.get('skipExistingVideos', import_settings.get('skip_existing_videos', True))
            
            if not skip_existing_videos:
                # If not skipping existing videos, return videos up to the target limit
                return {
                    'videos': videos[:target_new_videos],
                    'total_found': len(videos),
                    'existing_count': 0,
                    'new_count': len(videos[:target_new_videos])
                }
            
            from .database_storage import database_storage
            
            new_videos = []
            existing_count = 0
            
            # Check each video to see if it already exists
            for video in videos:
                video_id = video['video_id']
                existing_video = database_storage.get(video_id)
                
                if existing_video:
                    existing_count += 1
                    if import_settings.get('log_import_operations', True):
                        print(f"⏭️ Skipping existing video: {video_id}")
                else:
                    new_videos.append(video)
                    if import_settings.get('log_import_operations', True):
                        print(f"✅ Found new video: {video_id} - {video.get('title', 'Unknown')}")
                    
                    # Stop when we have enough new videos
                    if len(new_videos) >= target_new_videos:
                        break
            
            if import_settings.get('log_import_operations', True):
                print(f"🎯 Filtering results: {len(new_videos)} new videos selected (target: {target_new_videos})")
                print(f"📊 Stats: {existing_count} existing videos skipped, {len(videos)} total videos processed")
            
            return {
                'videos': new_videos,
                'total_found': len(videos),
                'existing_count': existing_count,
                'new_count': len(new_videos)
            }
                
        except Exception as e:
            print(f"Error filtering existing videos: {e}")
            # If filtering fails, return original videos (be conservative)
            return {
                'videos': videos[:target_new_videos],
                'total_found': len(videos),
                'existing_count': 0,
                'new_count': len(videos[:target_new_videos])
            }

    def _filter_videos_by_duration(self, videos, import_settings):
        """Filter videos based on duration (Shorts vs full videos) according to import_shorts setting"""
        try:
            # Get import_shorts setting (default: False - don't import Shorts)
            import_shorts = import_settings.get('import_shorts', False)
            
            if import_settings.get('log_import_operations', True):
                print(f"Duration filtering: import_shorts={import_shorts}")
            
            # If import_shorts is True, return all videos (no filtering needed)
            if import_shorts:
                print(f"Importing all videos (including Shorts): {len(videos)} videos")
                return videos
            
            # Need to get detailed video info to check durations
            # Batch video IDs for efficient API calls (up to 50 per request)
            video_ids = [video['video_id'] for video in videos]
            filtered_videos = []
            
            # Process videos in batches of 50 (YouTube API limit)
            batch_size = 50
            for i in range(0, len(video_ids), batch_size):
                batch_ids = video_ids[i:i + batch_size]
                batch_videos_dict = {video['video_id']: video for video in videos[i:i + batch_size]}
                
                try:
                    # Get video details including duration
                    video_request = self.service.videos().list(
                        part='contentDetails',
                        id=','.join(batch_ids)
                    )
                    video_response = video_request.execute()
                    
                    for item in video_response.get('items', []):
                        video_id = item['id']
                        content_details = item.get('contentDetails', {})
                        
                        # Parse duration
                        duration_seconds = None
                        if 'duration' in content_details:
                            duration_seconds = self._parse_iso8601_duration(content_details['duration'])
                        
                        # Filter out Shorts (videos <= 60 seconds)
                        if duration_seconds is None:
                            # If we can't get duration, include the video (be conservative)
                            filtered_videos.append(batch_videos_dict[video_id])
                            if import_settings.get('log_import_operations', True):
                                print(f"Video {video_id}: duration unknown, including")
                        elif duration_seconds > 60:
                            # Full video (> 60 seconds) - include it
                            filtered_videos.append(batch_videos_dict[video_id])
                            if import_settings.get('log_import_operations', True):
                                print(f"Video {video_id}: {duration_seconds}s (full video), including")
                        else:
                            # Short video (<= 60 seconds) - exclude it
                            if import_settings.get('log_import_operations', True):
                                print(f"Video {video_id}: {duration_seconds}s (Short), excluding")
                
                except Exception as e:
                    print(f"Error getting video details for batch: {e}")
                    # If we can't get details, include all videos in this batch (be conservative)
                    filtered_videos.extend([batch_videos_dict[vid] for vid in batch_ids])
            
            total_filtered = len(videos) - len(filtered_videos)
            if total_filtered > 0:
                print(f"Filtered out {total_filtered} Shorts, {len(filtered_videos)} videos remaining")
            else:
                print(f"No Shorts found, {len(filtered_videos)} videos remaining")
            
            return filtered_videos
            
        except Exception as e:
            print(f"Error during duration filtering: {e}")
            # If filtering fails, return original videos (be conservative)
            return videos


# Global YouTube API instance
youtube_api = YouTubeAPI()