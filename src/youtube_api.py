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
    
    def get_channel_videos(self, channel_name, max_results=5, days_back=30):
        """Get latest videos from a channel using YouTube Data API within specified time range"""
        if not self.service:
            raise Exception("YouTube Data API not available or not configured")
        
        try:
            # Get import settings
            from .database_storage import database_storage
            import_settings = database_storage.get_import_settings()
            
            # Apply settings if available
            if import_settings:
                max_results = min(max_results, import_settings.get('max_results_limit', 50))
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
            primary_strategy = import_settings.get('import_strategy', 'uploads_playlist') if import_settings else 'uploads_playlist'
            fallback_strategies = import_settings.get('fallback_strategies', 'activities_api,search_api') if import_settings else 'activities_api,search_api'
            
            # Convert fallback strategies string to list
            if isinstance(fallback_strategies, str):
                fallback_strategies = [s.strip() for s in fallback_strategies.split(',')]
            
            # Create ordered list of strategies to try
            strategies_to_try = [primary_strategy] + [s for s in fallback_strategies if s != primary_strategy]
            
            if import_settings.get('log_import_operations', True):
                print(f"Using import strategies: {strategies_to_try}")
            
            # Try each strategy in order
            for strategy in strategies_to_try:
                videos = self._try_import_strategy(strategy, actual_channel_id, channel_name, max_results, days_back)
                if videos:
                    return videos
            
            # If all strategies failed, return empty list
            print("All import strategies failed")
            return []
            
        except Exception as e:
            print(f"Error fetching channel videos: {e}")
            raise Exception(f"Failed to fetch videos from channel: {str(e)}")

    def _try_import_strategy(self, strategy, channel_id, channel_name, max_results, days_back):
        """Try a specific import strategy and return videos if successful"""
        try:
            if strategy == 'uploads_playlist':
                return self._try_uploads_playlist_strategy(channel_id, channel_name, max_results)
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

    def _try_uploads_playlist_strategy(self, channel_id, channel_name, max_results):
        """Try to get videos using uploads playlist strategy"""
        try:
            channel_request = self.service.channels().list(
                part='contentDetails',
                id=channel_id
            )
            channel_response = channel_request.execute()
            
            if channel_response.get('items'):
                uploads_playlist_id = channel_response['items'][0]['contentDetails']['relatedPlaylists']['uploads']
                print(f"Found uploads playlist: {uploads_playlist_id}")
                
                # Get videos from the uploads playlist
                playlist_request = self.service.playlistItems().list(
                    part='snippet',
                    playlistId=uploads_playlist_id,
                    maxResults=max_results,
                    order='date'
                )
                playlist_response = playlist_request.execute()
                
                videos = []
                for item in playlist_response.get('items', []):
                    video_id = item['snippet']['resourceId']['videoId']
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
                    print(f"Found {len(videos)} videos from uploads playlist")
                    return videos
                    
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
                if snippet.get('channelTitle', '').lower() == channel_name.lower():
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


# Global YouTube API instance
youtube_api = YouTubeAPI()