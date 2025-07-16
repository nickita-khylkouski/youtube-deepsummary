#!/usr/bin/env python3
"""
Database storage module using Supabase for YouTube Deep Summary
Replaces the legacy file-based storage system (legacy_file_storage.py)
"""

import os
import time
import re
import unicodedata
from typing import Optional, Dict, List
from datetime import datetime, timezone
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class DatabaseStorage:
    """Supabase database storage for YouTube transcripts, summaries, and metadata"""

    def _parse_datetime(self, datetime_str: str) -> datetime:
        """Parse datetime string with variable microsecond precision"""
        # Replace Z with +00:00 for proper timezone parsing
        datetime_str = datetime_str.replace('Z', '+00:00')

        # Handle variable microsecond precision by padding with zeros if needed
        if '+' in datetime_str and '.' in datetime_str:
            timestamp_part, tz_part = datetime_str.rsplit('+', 1)
            if '.' in timestamp_part:
                date_part, microsec_part = timestamp_part.rsplit('.', 1)
                # Pad microseconds to 6 digits
                microsec_part = microsec_part.ljust(6, '0')
                datetime_str = f"{date_part}.{microsec_part}+{tz_part}"

        return datetime.fromisoformat(datetime_str)

    def __init__(self):
        """Initialize Supabase client"""
        self.url = os.getenv('SUPABASE_URL')
        self.key = os.getenv('SUPABASE_API_KEY')

        if not self.url or not self.key:
            raise ValueError("SUPABASE_URL and SUPABASE_API_KEY must be set in environment variables")

        # Temporarily clear proxy environment variables for Supabase
        original_http_proxy = os.environ.pop('HTTP_PROXY', None)
        original_https_proxy = os.environ.pop('HTTPS_PROXY', None)
        original_http_proxy_lower = os.environ.pop('http_proxy', None)
        original_https_proxy_lower = os.environ.pop('https_proxy', None)

        try:
            # Create Supabase client without any proxy interference
            self.supabase: Client = create_client(self.url, self.key)
        finally:
            # Restore original proxy settings
            if original_http_proxy:
                os.environ['HTTP_PROXY'] = original_http_proxy
            if original_https_proxy:
                os.environ['HTTPS_PROXY'] = original_https_proxy
            if original_http_proxy_lower:
                os.environ['http_proxy'] = original_http_proxy_lower
            if original_https_proxy_lower:
                os.environ['https_proxy'] = original_https_proxy_lower
        print("Database storage initialized with Supabase (no proxy)")

    def _generate_url_slug(self, title: str) -> str:
        """Generate a URL-friendly slug from a video title using only ASCII characters."""
        if not title:
            return "untitled-video"
        
        # Normalize unicode characters
        title = unicodedata.normalize('NFKD', title)
        
        # Convert to lowercase
        title = title.lower()
        
        # Basic transliteration for common characters
        transliteration_map = {
            'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo',
            'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
            'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
            'ф': 'f', 'х': 'kh', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'shch',
            'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya',
            'ä': 'a', 'ö': 'o', 'ü': 'u', 'ß': 'ss', 'ç': 'c', 'ñ': 'n',
            'é': 'e', 'è': 'e', 'ê': 'e', 'ë': 'e', 'à': 'a', 'á': 'a', 'â': 'a',
            'ã': 'a', 'ì': 'i', 'í': 'i', 'î': 'i', 'ï': 'i', 'ò': 'o', 'ó': 'o',
            'ô': 'o', 'õ': 'o', 'ù': 'u', 'ú': 'u', 'û': 'u', 'ý': 'y', 'ÿ': 'y'
        }
        
        # Apply transliteration
        for char, replacement in transliteration_map.items():
            title = title.replace(char, replacement)
        
        # Remove any remaining non-ASCII characters
        # Keep only ASCII letters, numbers, spaces, and hyphens
        title = re.sub(r'[^a-zA-Z0-9\s-]', '', title)
        
        # Replace spaces and multiple hyphens with single hyphens
        title = re.sub(r'[-\s]+', '-', title)
        
        # Remove leading/trailing hyphens
        title = title.strip('-')
        
        # Limit length to 100 characters
        if len(title) > 100:
            title = title[:100].rstrip('-')
        
        # Ensure it's not empty
        if not title:
            return "untitled-video"
        
        return title

    def _ensure_unique_url_slug(self, base_slug: str, video_id: str = None) -> str:
        """Ensure the URL slug is unique by appending numbers if necessary."""
        try:
            # Check if the base slug is already taken
            query = self.supabase.table('youtube_videos').select('video_id').eq('url_path', base_slug)
            
            # If we're updating an existing video, exclude it from the check
            if video_id:
                query = query.neq('video_id', video_id)
            
            response = query.execute()
            
            if not response.data:
                return base_slug
            
            # Find a unique slug by appending numbers
            counter = 1
            while True:
                candidate_slug = f"{base_slug}-{counter}"
                query = self.supabase.table('youtube_videos').select('video_id').eq('url_path', candidate_slug)
                
                if video_id:
                    query = query.neq('video_id', video_id)
                
                response = query.execute()
                
                if not response.data:
                    return candidate_slug
                
                counter += 1
                
        except Exception as e:
            print(f"Error ensuring unique URL slug: {e}")
            return base_slug

    def _ensure_channel_exists(self, channel_id: str, channel_name: str, channel_info: dict = None):
        """Ensure a channel exists in the database, create if not found"""
        try:
            # Check if channel exists
            existing = self.supabase.table('youtube_channels').select('channel_id').eq('channel_id', channel_id).execute()
            
            if not existing.data:
                # Create new channel record
                channel_data = {
                    'channel_id': channel_id,
                    'channel_name': channel_name,
                    'created_at': datetime.now(timezone.utc).isoformat(),
                    'updated_at': datetime.now(timezone.utc).isoformat()
                }
                
                # Add channel info if provided
                if channel_info:
                    self._add_channel_info_to_data(channel_data, channel_info, channel_name)
                
                self.supabase.table('youtube_channels').insert(channel_data).execute()
                print(f"Created new channel: {channel_name} ({channel_id})")
            else:
                # Update existing channel with new info if provided
                if channel_info:
                    update_data = {'updated_at': datetime.now(timezone.utc).isoformat()}
                    self._add_channel_info_to_data(update_data, channel_info, channel_name)
                    
                    if len(update_data) > 1:  # More than just updated_at
                        self.supabase.table('youtube_channels').update(update_data).eq('channel_id', channel_id).execute()
                        print(f"Updated channel info for existing channel: {channel_name}")
            
        except Exception as e:
            print(f"Error ensuring channel exists: {e}")
    
    def _add_channel_info_to_data(self, channel_data: dict, channel_info: dict, channel_name: str):
        """Helper method to add channel info to data dict, checking if columns exist"""
        if not channel_info:
            return
            
        # Handle - check if column exists
        if channel_info.get('handle'):
            try:
                self.supabase.table('youtube_channels').select('handle').limit(1).execute()
                channel_data['handle'] = channel_info['handle']
                print(f"Adding handle {channel_info['handle']} for channel {channel_name}")
            except Exception as e:
                if 'handle' in str(e):
                    print(f"Handle column doesn't exist yet, skipping handle for {channel_name}")
                else:
                    print(f"Error checking handle column: {e}")
        
        # Title - check if column exists and update both channel_title and channel_name
        if channel_info.get('title'):
            try:
                self.supabase.table('youtube_channels').select('channel_title').limit(1).execute()
                channel_data['channel_title'] = channel_info['title']
                # Also update channel_name to use the proper title instead of "Unknown Channel"
                channel_data['channel_name'] = channel_info['title']
                print(f"Adding title '{channel_info['title']}' for channel {channel_name}")
            except Exception as e:
                if 'channel_title' in str(e):
                    print(f"Channel title column doesn't exist yet, skipping title for {channel_name}")
                    # Still update channel_name even if channel_title column doesn't exist
                    channel_data['channel_name'] = channel_info['title']
                else:
                    print(f"Error checking channel title column: {e}")
                    # Still update channel_name on other errors
                    channel_data['channel_name'] = channel_info['title']
        
        # Description - check if column exists
        if channel_info.get('description'):
            try:
                self.supabase.table('youtube_channels').select('channel_description').limit(1).execute()
                channel_data['channel_description'] = channel_info['description']
                print(f"Adding description for channel {channel_name}")
            except Exception as e:
                if 'channel_description' in str(e):
                    print(f"Channel description column doesn't exist yet, skipping description for {channel_name}")
                else:
                    print(f"Error checking channel description column: {e}")
        
        # Thumbnail URL - check if column exists
        if channel_info.get('thumbnail_url'):
            try:
                self.supabase.table('youtube_channels').select('thumbnail_url').limit(1).execute()
                channel_data['thumbnail_url'] = channel_info['thumbnail_url']
                print(f"Adding thumbnail URL for channel {channel_name}")
            except Exception as e:
                if 'thumbnail_url' in str(e):
                    print(f"Thumbnail URL column doesn't exist yet, skipping thumbnail for {channel_name}")
                else:
                    print(f"Error checking thumbnail URL column: {e}")
        
        # Derive channel URL from handle
        if channel_info.get('handle'):
            try:
                self.supabase.table('youtube_channels').select('channel_url').limit(1).execute()
                channel_data['channel_url'] = f"https://www.youtube.com/{channel_info['handle']}"
                print(f"Adding URL for channel {channel_name}")
            except Exception as e:
                if 'channel_url' in str(e):
                    print(f"Channel URL column doesn't exist yet, skipping URL for {channel_name}")
                else:
                    print(f"Error checking channel URL column: {e}")

    def get(self, video_id: str) -> Optional[Dict]:
        """
        Get cached transcript data for video ID from database

        Args:
            video_id: YouTube video ID

        Returns:
            Cached data dict or None if not found
        """
        try:
            # Get video metadata without JOIN to avoid foreign key issues
            video_response = self.supabase.table('youtube_videos')\
                .select('*')\
                .eq('video_id', video_id)\
                .execute()

            if not video_response.data or len(video_response.data) == 0:
                print(f"Database MISS for video {video_id}")
                return None

            video_data = video_response.data[0]

            # Get transcript
            transcript_response = self.supabase.table('transcripts').select('*').eq('video_id', video_id).execute()

            if not transcript_response.data or len(transcript_response.data) == 0:
                print(f"Database MISS - no transcript for video {video_id}")
                return None

            transcript_data = transcript_response.data[0]

            # Get chapters (optional)
            chapters_response = self.supabase.table('video_chapters').select('*').eq('video_id', video_id).execute()
            chapters = chapters_response.data[0].get('chapters_data') if chapters_response.data and len(chapters_response.data) > 0 else None

            # Get channel information separately to avoid foreign key issues
            channel_info = None
            channel_id = video_data.get('channel_id')
            if channel_id:
                try:
                    channel_response = self.supabase.table('youtube_channels')\
                        .select('channel_name, channel_id, thumbnail_url')\
                        .eq('channel_id', channel_id)\
                        .execute()
                    
                    if channel_response.data and len(channel_response.data) > 0:
                        channel_info = channel_response.data[0]
                except Exception as e:
                    print(f"Warning: Could not fetch channel info for {channel_id}: {e}")
                    channel_info = None

            # Reconstruct the cache format with enhanced channel information
            cached_data = {
                'video_id': video_id,
                'timestamp': time.mktime(self._parse_datetime(video_data['created_at']).timetuple()),
                'transcript': transcript_data['transcript_data'],
                'video_info': {
                    'title': video_data['title'],
                    'duration': video_data['duration'],
                    'chapters': chapters,
                    'channel_id': video_data.get('channel_id'),
                    'youtube_channels': channel_info
                },
                'formatted_transcript': transcript_data['formatted_transcript']
            }

            print(f"Database HIT for video {video_id}")
            return cached_data

        except Exception as e:
            print(f"Database read error for {video_id}: {e}")
            return None

    def set(self, video_id: str, transcript: List[Dict], video_info: Dict, formatted_transcript: str, channel_id: str = None, channel_info: dict = None):
        """
        Store transcript data for video ID in database

        Args:
            video_id: YouTube video ID
            transcript: Raw transcript data
            video_info: Video metadata (title, chapters, etc.)
            formatted_transcript: Formatted readable transcript
            channel_id: YouTube channel ID
            channel_info: Channel info dict with handle, title, description
        """
        try:
            # Handle channel information
            if channel_id:
                self._ensure_channel_exists(channel_id, video_info.get('channel_name', 'Unknown Channel'), channel_info)

            # Parse published_at if available
            published_at = video_info.get('published_at') or video_info.get('upload_date')
            if published_at and isinstance(published_at, str) and len(published_at) == 8:
                # Convert YYYYMMDD format to ISO datetime
                try:
                    from datetime import datetime as dt
                    parsed_date = dt.strptime(published_at, '%Y%m%d')
                    published_at = parsed_date.isoformat() + 'Z'
                except:
                    published_at = None

            # Generate URL path from title
            title = video_info.get('title', '')
            base_slug = self._generate_url_slug(title)
            url_path = self._ensure_unique_url_slug(base_slug, video_id)

            # Insert or update video metadata
            video_data = {
                'video_id': video_id,
                'title': title,
                'channel_id': channel_id,
                'duration': video_info.get('duration'),
                'thumbnail_url': f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg",
                'published_at': published_at,
                'url_path': url_path,
                'updated_at': datetime.now(timezone.utc).isoformat()
            }

            # Use upsert to insert or update (on_conflict specifies the unique constraint)
            self.supabase.table('youtube_videos').upsert(video_data, on_conflict='video_id').execute()

            # Insert or update transcript
            transcript_data = {
                'video_id': video_id,
                'transcript_data': transcript,
                'formatted_transcript': formatted_transcript,
                'language_used': 'en',  # Default, could be enhanced
                'updated_at': datetime.now(timezone.utc).isoformat()
            }

            # Delete existing transcript and insert new one
            self.supabase.table('transcripts').delete().eq('video_id', video_id).execute()
            self.supabase.table('transcripts').insert(transcript_data).execute()

            # Insert or update chapters if available
            chapters = video_info.get('chapters')
            print(f"Chapters data for {video_id}: {chapters}")
            if chapters:
                chapters_data = {
                    'video_id': video_id,
                    'chapters_data': chapters,
                    'updated_at': datetime.now(timezone.utc).isoformat()
                }

                # Delete existing chapters and insert new ones
                self.supabase.table('video_chapters').delete().eq('video_id', video_id).execute()
                self.supabase.table('video_chapters').insert(chapters_data).execute()
                print(f"Chapters saved for {video_id}: {len(chapters)} chapters")
            else:
                print(f"No chapters found for video {video_id}")

            print(f"Database SAVED for video {video_id}")

        except Exception as e:
            print(f"Database write error for {video_id}: {e}")
            raise

    def save_summary(self, video_id: str, summary: str, model_used: str = 'gpt-4.1', prompt_id: int = None, prompt_name: str = None):
        """
        Save AI summary for a video (creates new history entry instead of overwriting)

        Args:
            video_id: YouTube video ID
            summary: Generated summary text
            model_used: AI model used for summary
            prompt_id: ID of the prompt used (optional)
            prompt_name: Name of the prompt used (optional)
        """
        try:
            summary_data = {
                'video_id': video_id,
                'summary_text': summary,
                'model_used': model_used,
                'prompt_id': prompt_id,
                'prompt_name': prompt_name or 'Default Summary',
                'is_current': True,
                'created_at': datetime.now(timezone.utc).isoformat(),
                'updated_at': datetime.now(timezone.utc).isoformat()
            }

            # Insert new summary (trigger will handle version numbering and current flag management)
            result = self.supabase.table('summaries').insert(summary_data).execute()

            if result.data:
                print(f"Summary saved for video {video_id} (version {result.data[0].get('version_number', 'unknown')})")
                return result.data[0].get('summary_id')
            else:
                print(f"Failed to save summary for video {video_id}")
                return None

        except Exception as e:
            print(f"Error saving summary for {video_id}: {e}")
            raise

    def get_summary(self, video_id: str) -> Optional[str]:
        """
        Get current saved summary for a video

        Args:
            video_id: YouTube video ID

        Returns:
            Summary text or None if not found
        """
        try:
            response = self.supabase.table('summaries')\
                .select('summary_text')\
                .eq('video_id', video_id)\
                .eq('is_current', True)\
                .execute()

            if response.data and len(response.data) > 0:
                return response.data[0]['summary_text']
            return None

        except Exception as e:
            print(f"Error getting summary for {video_id}: {e}")
            return None

    def get_summary_history(self, video_id: str) -> List[Dict]:
        """
        Get all summary history for a video

        Args:
            video_id: YouTube video ID

        Returns:
            List of summary history entries
        """
        try:
            response = self.supabase.table('summaries')\
                .select('summary_id, summary_text, model_used, prompt_id, prompt_name, is_current, version_number, created_at, updated_at')\
                .eq('video_id', video_id)\
                .order('version_number', desc=True)\
                .execute()

            return response.data if response.data else []

        except Exception as e:
            print(f"Error getting summary history for {video_id}: {e}")
            return []

    def get_summary_by_id(self, summary_id: int) -> Optional[Dict]:
        """
        Get specific summary by ID

        Args:
            summary_id: Summary ID

        Returns:
            Summary data or None if not found
        """
        try:
            response = self.supabase.table('summaries')\
                .select('*')\
                .eq('summary_id', summary_id)\
                .execute()

            if response.data and len(response.data) > 0:
                return response.data[0]
            return None

        except Exception as e:
            print(f"Error getting summary by ID {summary_id}: {e}")
            return None

    def set_current_summary(self, video_id: str, summary_id: int) -> bool:
        """
        Set a specific summary as current for a video

        Args:
            video_id: YouTube video ID
            summary_id: Summary ID to set as current

        Returns:
            Success status
        """
        try:
            # Update the specific summary to be current (trigger will handle others)
            result = self.supabase.table('summaries')\
                .update({'is_current': True})\
                .eq('video_id', video_id)\
                .eq('summary_id', summary_id)\
                .execute()

            return bool(result.data)

        except Exception as e:
            print(f"Error setting current summary for {video_id}: {e}")
            return False

    def delete_summary_by_id(self, summary_id: int) -> bool:
        """
        Delete a specific summary by ID

        Args:
            summary_id: Summary ID to delete

        Returns:
            Success status
        """
        try:
            result = self.supabase.table('summaries')\
                .delete()\
                .eq('summary_id', summary_id)\
                .execute()

            return bool(result.data)

        except Exception as e:
            print(f"Error deleting summary {summary_id}: {e}")
            return False

    def clear_expired(self):
        """
        Remove expired cache files - for database, we'll keep everything
        This method is kept for compatibility with the old cache interface
        """
        print("Database storage doesn't expire - keeping all data")
        return

    def get_cache_info(self) -> Dict:
        """Get database statistics using efficient count queries"""
        try:
            # Use count='exact' for efficient counting without fetching data
            videos_response = self.supabase.table('youtube_videos').select('video_id', count='exact').execute()
            videos_count = videos_response.count if videos_response.count is not None else 0

            transcripts_response = self.supabase.table('transcripts').select('video_id', count='exact').execute()
            transcripts_count = transcripts_response.count if transcripts_response.count is not None else 0

            summaries_response = self.supabase.table('summaries').select('video_id', count='exact').execute()
            summaries_count = summaries_response.count if summaries_response.count is not None else 0

            print(f"Database stats: {videos_count} videos, {transcripts_count} transcripts, {summaries_count} summaries")

            return {
                'total_files': videos_count,
                'valid_files': videos_count,
                'expired_files': 0,  # Database doesn't expire
                'cache_dir': 'Supabase Database',
                'ttl_hours': 'Unlimited',
                'videos_count': videos_count,
                'transcripts_count': transcripts_count,
                'summaries_count': summaries_count
            }

        except Exception as e:
            print(f"Error getting database info: {e}")
            return {
                'total_files': 0,
                'valid_files': 0,
                'expired_files': 0,
                'cache_dir': 'Supabase Database (Error)',
                'ttl_hours': 'Unlimited',
                'videos_count': 0,
                'transcripts_count': 0,
                'summaries_count': 0
            }

    def get_all_cached_videos(self) -> List[Dict]:
        """Get list of all cached videos with metadata from database"""
        return self.get_cached_videos_paginated()['videos']

    def get_cached_videos_paginated(self, page: int = 1, per_page: int = 20, group_by_channel: bool = False) -> Dict:
        """Get paginated list of cached videos with metadata from database"""
        try:
            if group_by_channel:
                return self._get_videos_grouped_by_channel_paginated(page, per_page)
            
            # Calculate offset
            offset = (page - 1) * per_page
            
            # Get total count for pagination
            count_response = self.supabase.table('youtube_videos')\
                .select('video_id', count='exact')\
                .execute()
            total_videos = count_response.count if count_response.count is not None else 0
            
            # Get paginated videos with their transcripts, summaries, and channel information
            response = self.supabase.table('youtube_videos')\
                .select('*, transcripts(transcript_data), summaries(summary_text), video_chapters(chapters_data)')\
                .order('created_at', desc=True)\
                .range(offset, offset + per_page - 1)\
                .execute()
            
            # Get all unique channel IDs from the videos
            channel_ids = list(set(video.get('channel_id') for video in response.data if video.get('channel_id')))
            
            # Batch fetch all channel information in one query
            channels_info = {}
            if channel_ids:
                channels_response = self.supabase.table('youtube_channels')\
                    .select('channel_id, channel_name, handle')\
                    .in_('channel_id', channel_ids)\
                    .execute()
                
                for channel in channels_response.data:
                    channels_info[channel['channel_id']] = channel

            cached_videos = []

            for video in response.data:
                # Calculate transcript entries count
                transcript_entries = 0
                if video.get('transcripts') and len(video['transcripts']) > 0:
                    transcript_data = video['transcripts'][0].get('transcript_data', [])
                    transcript_entries = len(transcript_data) if transcript_data else 0

                # Calculate chapters count
                chapters_count = 0
                if video.get('video_chapters') and len(video['video_chapters']) > 0:
                    chapters_data = video['video_chapters'][0].get('chapters_data', [])
                    chapters_count = len(chapters_data) if chapters_data else 0

                # Calculate cache age
                created_at = self._parse_datetime(video['created_at'])
                cache_age_hours = (datetime.now(timezone.utc) - created_at).total_seconds() / 3600

                # Check if summary exists
                has_summary = video.get('summaries') and len(video['summaries']) > 0

                # Get channel information from batched data
                channel_name = 'Unknown Channel'
                channel_id = video.get('channel_id')
                handle = None
                
                if channel_id and channel_id in channels_info:
                    channel_info = channels_info[channel_id]
                    channel_name = channel_info.get('channel_name', 'Unknown Channel')
                    handle = channel_info.get('handle')

                cached_videos.append({
                    'video_id': video['video_id'],
                    'title': video['title'] or 'Unknown Title',
                    'channel_name': channel_name,
                    'channel_id': channel_id,
                    'handle': handle,
                    'duration': video['duration'],
                    'chapters_count': chapters_count,
                    'transcript_entries': transcript_entries,
                    'cache_age_hours': round(cache_age_hours, 1),
                    'is_valid': True,  # Database entries are always valid
                    'cache_timestamp': time.mktime(created_at.timetuple()),
                    'file_size': 0,  # Not applicable for database
                    'has_summary': has_summary,
                    'created_at': video['created_at'],
                    'url_path': video.get('url_path')
                })

            # Calculate pagination metadata
            total_pages = (total_videos + per_page - 1) // per_page
            has_prev = page > 1
            has_next = page < total_pages
            
            return {
                'videos': cached_videos,
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': total_videos,
                    'total_pages': total_pages,
                    'has_prev': has_prev,
                    'has_next': has_next,
                    'prev_page': page - 1 if has_prev else None,
                    'next_page': page + 1 if has_next else None
                }
            }

        except Exception as e:
            print(f"Error getting paginated cached videos: {e}")
            return {
                'videos': [],
                'pagination': {
                    'page': 1,
                    'per_page': per_page,
                    'total': 0,
                    'total_pages': 0,
                    'has_prev': False,
                    'has_next': False,
                    'prev_page': None,
                    'next_page': None
                }
            }

    def _get_videos_grouped_by_channel_paginated(self, page: int = 1, per_page: int = 5) -> Dict:
        """Get videos grouped by channel with pagination at the channel level"""
        try:
            # Calculate offset for channels
            offset = (page - 1) * per_page
            
            # Get channels that have videos with their video counts efficiently
            # First get all videos to count by channel
            videos_response = self.supabase.table('youtube_videos')\
                .select('channel_id')\
                .execute()
            
            # Count videos by channel
            channel_video_counts = {}
            for video in videos_response.data:
                channel_id = video.get('channel_id')
                if channel_id:
                    channel_video_counts[channel_id] = channel_video_counts.get(channel_id, 0) + 1
            
            # Get channel info for channels that have videos
            channel_ids_with_videos = list(channel_video_counts.keys())
            all_channels_with_counts = []
            
            if channel_ids_with_videos:
                channels_response = self.supabase.table('youtube_channels')\
                    .select('channel_id, channel_name, handle')\
                    .in_('channel_id', channel_ids_with_videos)\
                    .order('channel_name')\
                    .execute()
                
                for channel in channels_response.data:
                    channel_id = channel['channel_id']
                    all_channels_with_counts.append({
                        'channel_id': channel_id,
                        'channel_name': channel['channel_name'],
                        'handle': channel['handle'],
                        'video_count': channel_video_counts[channel_id]
                    })
            
            total_channels = len(all_channels_with_counts)
            
            # Get paginated channels
            paginated_channels = all_channels_with_counts[offset:offset + per_page]
            
            # For each channel, get some videos (limit to keep performance good)
            grouped_data = []
            videos_per_channel = 12  # Show up to 12 videos per channel
            
            for channel in paginated_channels:
                channel_id = channel['channel_id']
                channel_name = channel['channel_name']
                handle = channel['handle']
                total_videos_in_channel = channel['video_count']
                
                # Get videos for this channel
                videos_response = self.supabase.table('youtube_videos')\
                    .select('*, transcripts(transcript_data), summaries(summary_text), video_chapters(chapters_data)')\
                    .eq('channel_id', channel_id)\
                    .order('created_at', desc=True)\
                    .limit(videos_per_channel)\
                    .execute()
                
                channel_videos = []
                for video in videos_response.data:
                    # Process video data (same as regular pagination)
                    transcript_entries = 0
                    if video.get('transcripts') and len(video['transcripts']) > 0:
                        transcript_data = video['transcripts'][0].get('transcript_data', [])
                        transcript_entries = len(transcript_data) if transcript_data else 0

                    chapters_count = 0
                    if video.get('video_chapters') and len(video['video_chapters']) > 0:
                        chapters_data = video['video_chapters'][0].get('chapters_data', [])
                        chapters_count = len(chapters_data) if chapters_data else 0

                    created_at = self._parse_datetime(video['created_at'])
                    cache_age_hours = (datetime.now(timezone.utc) - created_at).total_seconds() / 3600
                    has_summary = video.get('summaries') and len(video['summaries']) > 0

                    channel_videos.append({
                        'video_id': video['video_id'],
                        'title': video['title'] or 'Unknown Title',
                        'channel_name': channel_name,
                        'channel_id': channel_id,
                        'handle': handle,
                        'duration': video['duration'],
                        'chapters_count': chapters_count,
                        'transcript_entries': transcript_entries,
                        'cache_age_hours': round(cache_age_hours, 1),
                        'is_valid': True,
                        'cache_timestamp': time.mktime(created_at.timetuple()),
                        'file_size': 0,
                        'has_summary': has_summary,
                        'created_at': video['created_at'],
                        'url_path': video.get('url_path')
                    })
                
                # Check if any videos in this channel have summaries for the summary link
                has_summaries = any(video['has_summary'] for video in channel_videos)
                
                grouped_data.append({
                    'channel_name': channel_name,
                    'channel_id': channel_id,
                    'handle': handle,
                    'video_count': total_videos_in_channel,
                    'videos_shown': len(channel_videos),
                    'has_summaries': has_summaries,
                    'videos': channel_videos
                })
            
            # Calculate pagination metadata for channels
            total_pages = (total_channels + per_page - 1) // per_page
            has_prev = page > 1
            has_next = page < total_pages
            
            return {
                'videos': grouped_data,  # This will be channel groups, not individual videos
                'is_grouped': True,
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': total_channels,  # Total channels, not videos
                    'total_pages': total_pages,
                    'has_prev': has_prev,
                    'has_next': has_next,
                    'prev_page': page - 1 if has_prev else None,
                    'next_page': page + 1 if has_next else None
                }
            }

        except Exception as e:
            print(f"Error getting grouped videos: {e}")
            import traceback
            traceback.print_exc()
            return {
                'videos': [],
                'is_grouped': True,
                'pagination': {
                    'page': 1,
                    'per_page': per_page,
                    'total': 0,
                    'total_pages': 0,
                    'has_prev': False,
                    'has_next': False,
                    'prev_page': None,
                    'next_page': None
                }
            }

    def get_video_by_url_path(self, url_path: str) -> Optional[Dict]:
        """Get a video by its URL path"""
        try:
            response = self.supabase.table('youtube_videos')\
                .select('*')\
                .eq('url_path', url_path)\
                .execute()
            
            if response.data and len(response.data) > 0:
                video = response.data[0]
                
                # Get channel information if available
                channel_name = 'Unknown Channel'
                channel_id = video.get('channel_id')
                handle = None
                
                if channel_id:
                    try:
                        channel_response = self.supabase.table('youtube_channels')\
                            .select('channel_name, channel_id, handle')\
                            .eq('channel_id', channel_id)\
                            .execute()
                        
                        if channel_response.data and len(channel_response.data) > 0:
                            channel_info = channel_response.data[0]
                            channel_name = channel_info['channel_name']
                            handle = channel_info.get('handle')
                    except Exception as e:
                        print(f"Warning: Could not fetch channel info for {channel_id}: {e}")
                
                return {
                    'video_id': video['video_id'],
                    'title': video['title'] or 'Unknown Title',
                    'channel_name': channel_name,
                    'channel_id': channel_id,
                    'handle': handle,
                    'duration': video['duration'],
                    'thumbnail_url': video.get('thumbnail_url'),
                    'published_at': video.get('published_at'),
                    'created_at': video['created_at'],
                    'url_path': video.get('url_path')
                }
            
            return None
            
        except Exception as e:
            print(f"Error getting video by url_path '{url_path}': {e}")
            return None

    def get_videos_by_channel(self, channel_name: str = None, channel_id: str = None) -> List[Dict]:
        """Get all videos from a specific channel (by name or ID)"""
        try:
            if channel_id:
                # Use channel_id directly - no JOIN to avoid foreign key issues
                query = self.supabase.table('youtube_videos')\
                    .select('*')\
                    .eq('channel_id', channel_id)\
                    .order('created_at', desc=True)
                
                response = query.execute()
                videos = response.data if response.data else []
                
                # Manually fetch channel information
                if videos and channel_id:
                    try:
                        channel_response = self.supabase.table('youtube_channels')\
                            .select('channel_name, channel_id, handle')\
                            .eq('channel_id', channel_id)\
                            .execute()
                        
                        if channel_response.data and len(channel_response.data) > 0:
                            channel_info = channel_response.data[0]
                            for video in videos:
                                video['channel_name'] = channel_info['channel_name']
                                video['channel_id'] = channel_info['channel_id']
                                video['handle'] = channel_info.get('handle')
                    except Exception as e:
                        print(f"Warning: Could not fetch channel info for {channel_id}: {e}")
                
                return videos
            
            elif channel_name:
                # Try to find channel by name first, then get videos by channel_id
                channel_info = self.get_channel_by_name(channel_name)
                if channel_info:
                    return self.get_videos_by_channel(channel_id=channel_info['channel_id'])
                else:
                    # No channel found
                    return []
            else:
                raise ValueError("Either channel_name or channel_id must be provided")

        except Exception as e:
            print(f"Error getting videos for channel {channel_name or channel_id}: {e}")
            return []

    def delete(self, video_id: str) -> bool:
        """Delete a video and all its associated data"""
        try:
            print(f"Deleting video {video_id} and all associated data...")

            # Delete summaries first (foreign key dependency)
            summaries_response = self.supabase.table('summaries').delete().eq('video_id', video_id).execute()
            print(f"Deleted summaries: {len(summaries_response.data) if summaries_response.data else 0}")

            # Delete chapters
            chapters_response = self.supabase.table('video_chapters').delete().eq('video_id', video_id).execute()
            print(f"Deleted chapters: {len(chapters_response.data) if chapters_response.data else 0}")

            # Delete transcripts
            transcripts_response = self.supabase.table('transcripts').delete().eq('video_id', video_id).execute()
            print(f"Deleted transcripts: {len(transcripts_response.data) if transcripts_response.data else 0}")

            # Delete the main video record
            video_response = self.supabase.table('youtube_videos').delete().eq('video_id', video_id).execute()
            print(f"Deleted video: {len(video_response.data) if video_response.data else 0}")

            return True

        except Exception as e:
            print(f"Error deleting video {video_id}: {e}")
            return False

    

    def get_all_channels(self, page: int = 1, per_page: int = 20):
        """Get all channels with video counts and summary counts - OPTIMIZED VERSION with pagination"""
        try:
            # Use optimized implementation with minimal database calls
            return self._get_all_channels_optimized(page, per_page)
            
        except Exception as e:
            print(f"Error in get_all_channels: {e}")
            import traceback
            traceback.print_exc()
            return {
                'channels': [],
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': 0,
                    'total_pages': 0,
                    'has_prev': False,
                    'has_next': False,
                    'prev_page': None,
                    'next_page': None
                }
            }

    def _get_all_channels_optimized(self, page: int = 1, per_page: int = 20):
        """Optimized implementation using minimal database calls with pagination"""
        try:
            # Calculate offset
            offset = (page - 1) * per_page
            
            # Get total count first for pagination
            total_channels_result = self.supabase.table('youtube_channels')\
                .select('channel_id', count='exact')\
                .not_.is_('handle', 'null')\
                .execute()
            
            total_channels = total_channels_result.count if total_channels_result.count else 0
            
            # Get ALL channels with basic info, only those with handles (required for URLs)
            # We need all channels first, then sort by latest video date, then paginate
            channels_result = self.supabase.table('youtube_channels')\
                .select('channel_id, channel_name, handle, thumbnail_url')\
                .not_.is_('handle', 'null')\
                .execute()
            
            if not channels_result.data:
                return {
                    'channels': [],
                    'pagination': {
                        'page': page,
                        'per_page': per_page,
                        'total': total_channels,
                        'total_pages': 0,
                        'has_prev': False,
                        'has_next': False,
                        'prev_page': None,
                        'next_page': None
                    }
                }
            
            # Get all channel IDs for filtering
            channel_ids = [ch['channel_id'] for ch in channels_result.data]
            
            # Get all videos for these channels in one query, with row numbering for recent videos
            all_videos_result = self.supabase.table('youtube_videos')\
                .select('video_id, channel_id, title, duration, url_path, created_at')\
                .in_('channel_id', channel_ids)\
                .order('channel_id, created_at', desc=True)\
                .execute()
            
            # Get all summaries in one query
            summaries_result = self.supabase.table('summaries')\
                .select('video_id')\
                .execute()
            
            summarized_video_ids = {s['video_id'] for s in summaries_result.data}
            
            # Process data in memory for efficiency
            channel_data = {}
            
            # Initialize channel data
            for channel in channels_result.data:
                channel_id = channel['channel_id']
                channel_data[channel_id] = {
                    'info': channel,
                    'video_count': 0,
                    'summary_count': 0,
                    'recent_videos': [],
                    'latest_video_date': None
                }
            
            # Process all videos in one pass
            for video in all_videos_result.data:
                channel_id = video['channel_id']
                if channel_id not in channel_data:
                    continue
                    
                # Count videos
                channel_data[channel_id]['video_count'] += 1
                
                # Count summaries
                if video['video_id'] in summarized_video_ids:
                    channel_data[channel_id]['summary_count'] += 1
                
                # Track the latest video date for sorting
                video_date = video.get('created_at')
                if video_date and (channel_data[channel_id]['latest_video_date'] is None or 
                                   video_date > channel_data[channel_id]['latest_video_date']):
                    channel_data[channel_id]['latest_video_date'] = video_date
                
                # Keep only the 3 most recent videos (already ordered by created_at desc)
                if len(channel_data[channel_id]['recent_videos']) < 3:
                    channel_data[channel_id]['recent_videos'].append(video)
            
            # Build final result
            channels = []
            for channel_id, data in channel_data.items():
                # Only include channels with videos
                if data['video_count'] == 0:
                    continue
                
                # Format recent videos
                recent_videos = {}
                for video in data['recent_videos']:
                    video_id = video['video_id']
                    recent_videos[video_id] = {
                        'video_info': {
                            'title': video.get('title'),
                            'thumbnail_url': f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg",
                            'duration': video.get('duration'),
                            'channel_name': data['info']['channel_name']
                        },
                        'video_id': video_id,
                        'url_path': video.get('url_path'),
                        'has_summary': video_id in summarized_video_ids
                    }
                
                channels.append({
                    'channel_id': channel_id,
                    'name': data['info']['channel_name'],
                    'handle': data['info']['handle'],
                    'video_count': data['video_count'],
                    'summary_count': data['summary_count'],
                    'thumbnail_url': data['info'].get('thumbnail_url'),
                    'recent_videos': recent_videos,
                    'latest_video_date': data['latest_video_date']
                })
            
            # Sort by latest video date desc (most recent first), then by video count desc
            channels.sort(key=lambda x: (
                x.get('latest_video_date', '') if x.get('latest_video_date') else '0000-00-00',  # Handle None dates
                -x['video_count']
            ), reverse=True)
            
            # Apply pagination AFTER sorting to ensure correct order
            total_channels_with_videos = len(channels)
            start_idx = (page - 1) * per_page
            end_idx = start_idx + per_page
            paginated_channels = channels[start_idx:end_idx]
            
            # Calculate pagination metadata based on channels with videos
            total_pages = (total_channels_with_videos + per_page - 1) // per_page
            has_prev = page > 1
            has_next = page < total_pages
            
            print(f"Optimized channels query: {len(paginated_channels)} channels on page {page}/{total_pages}, sorted by latest video date, reduced to ~4 DB calls total")
            
            return {
                'channels': paginated_channels,
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': total_channels_with_videos,
                    'total_pages': total_pages,
                    'has_prev': has_prev,
                    'has_next': has_next,
                    'prev_page': page - 1 if has_prev else None,
                    'next_page': page + 1 if has_next else None
                }
            }
            
        except Exception as e:
            print(f"Error in optimized get_all_channels: {e}")
            import traceback
            traceback.print_exc()
            return {
                'channels': [],
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': 0,
                    'total_pages': 0,
                    'has_prev': False,
                    'has_next': False,
                    'prev_page': None,
                    'next_page': None
                }
            }

    def save_memory_snippet(self, video_id: str, snippet_text: str, context_before: str = None, context_after: str = None, tags: list = None) -> bool:
        """Save a memory snippet to the database"""
        if not self.supabase:
            print("Database not initialized")
            return False

        try:
            # Check if memory_snippets table exists, if not create it
            try:
                # Test if table exists by trying a simple select
                self.supabase.table('memory_snippets').select('id').limit(1).execute()
            except Exception as table_error:
                if 'does not exist' in str(table_error):
                    print("memory_snippets table doesn't exist. Please create it manually in Supabase:")
                    print("""
                    CREATE TABLE memory_snippets (
                        id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
                        video_id VARCHAR(11) NOT NULL,
                        snippet_text TEXT NOT NULL,
                        context_before TEXT,
                        context_after TEXT,
                        tags TEXT[],
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                    );
                    """)
                    return False
                else:
                    raise table_error

            # Ensure tags is a list
            if tags is None:
                tags = []

            # Insert the memory snippet
            result = self.supabase.table('memory_snippets').insert({
                'video_id': video_id,
                'snippet_text': snippet_text,
                'context_before': context_before,
                'context_after': context_after,
                'tags': tags
            }).execute()

            if result.data:
                print(f"Memory snippet saved successfully for video {video_id}")
                return True
            else:
                print(f"Failed to save memory snippet for video {video_id}")
                return False

        except Exception as e:
            print(f"Error saving memory snippet: {e}")
            return False

    def get_memory_snippets(self, video_id: str = None, limit: int = 100) -> list:
        """Get memory snippets, optionally filtered by video_id"""
        if not self.supabase:
            print("Database not initialized")
            return []

        try:
            print(f"get_memory_snippets called with video_id={video_id}, limit={limit}")
            # Get memory snippets without JOINs to avoid foreign key issues
            query = self.supabase.table('memory_snippets').select(
                'id, video_id, snippet_text, context_before, context_after, tags, created_at'
            ).order('created_at', desc=True).limit(limit)

            if video_id:
                query = query.eq('video_id', video_id)

            result = query.execute()
            snippets = result.data if result.data else []
            
            # Get video information for each snippet separately
            for snippet in snippets:
                try:
                    video_result = self.supabase.table('youtube_videos').select(
                        'title, thumbnail_url, channel_id'
                    ).eq('video_id', snippet['video_id']).execute()
                    
                    if video_result.data:
                        video_data = video_result.data[0]
                        snippet['youtube_videos'] = video_data  # Store as object, not array
                        
                        # Get channel information if channel_id exists
                        channel_id = video_data.get('channel_id')
                        if channel_id:
                            try:
                                channel_result = self.supabase.table('youtube_channels').select(
                                    'channel_name, channel_id, thumbnail_url, handle'
                                ).eq('channel_id', channel_id).execute()
                                
                                if channel_result.data:
                                    channel_data = channel_result.data[0]
                                    snippet['channel_name'] = channel_data['channel_name']
                                    snippet['channel_id'] = channel_data['channel_id']
                                    snippet['channel_thumbnail_url'] = channel_data.get('thumbnail_url')
                                    snippet['handle'] = channel_data.get('handle')
                                else:
                                    snippet['channel_name'] = 'Unknown Channel'
                                    snippet['channel_id'] = channel_id
                            except Exception as channel_error:
                                print(f"Warning: Could not fetch channel info for {channel_id}: {channel_error}")
                                snippet['channel_name'] = 'Unknown Channel'
                                snippet['channel_id'] = channel_id
                        else:
                            snippet['channel_name'] = 'Unknown Channel'
                            snippet['channel_id'] = None
                    else:
                        snippet['youtube_videos'] = {}
                        snippet['channel_name'] = 'Unknown Channel'
                        snippet['channel_id'] = None
                        
                except Exception as video_error:
                    print(f"Error getting video info for {snippet['video_id']}: {video_error}")
                    snippet['youtube_videos'] = {}
                    snippet['channel_name'] = 'Unknown Channel'
                    snippet['channel_id'] = None
            
            print(f"get_memory_snippets returning {len(snippets)} snippets")
            return snippets
                
        except Exception as e:
            print(f"Error getting memory snippets: {e}")
            import traceback
            traceback.print_exc()
            return []

    def delete_memory_snippet(self, snippet_id: str) -> bool:
        """Delete a memory snippet by ID"""
        if not self.supabase:
            print("Database not initialized")
            return False

        try:
            result = self.supabase.table('memory_snippets').delete().eq('id', snippet_id).execute()
            
            if result.data:
                print(f"Memory snippet {snippet_id} deleted successfully")
                return True
            else:
                print(f"No memory snippet found with ID {snippet_id}")
                return False

        except Exception as e:
            print(f"Error deleting memory snippet: {e}")
            return False

    def update_memory_snippet_tags(self, snippet_id: str, tags: list) -> bool:
        """Update tags for a memory snippet"""
        if not self.supabase:
            print("Database not initialized")
            return False

        try:
            result = self.supabase.table('memory_snippets').update({
                'tags': tags,
                'updated_at': 'NOW()'
            }).eq('id', snippet_id).execute()
            
            if result.data:
                print(f"Memory snippet {snippet_id} tags updated successfully")
                return True
            else:
                print(f"Failed to update tags for memory snippet {snippet_id}")
                return False

        except Exception as e:
            print(f"Error updating memory snippet tags: {e}")
            return False

    def get_memory_snippets_stats(self) -> dict:
        """Get statistics about memory snippets"""
        if not self.supabase:
            print("Database not initialized")
            return {}

        try:
            # Get total count
            count_result = self.supabase.table('memory_snippets').select('id', count='exact').execute()
            total_snippets = count_result.count if count_result.count is not None else 0

            # Get snippets by video count
            videos_result = self.supabase.table('memory_snippets').select('video_id').execute()
            unique_videos = len(set(item['video_id'] for item in videos_result.data)) if videos_result.data else 0

            return {
                'total_snippets': total_snippets,
                'videos_with_snippets': unique_videos
            }

        except Exception as e:
            print(f"Error getting memory snippets stats: {e}")
            return {'total_snippets': 0, 'videos_with_snippets': 0}

    def get_channel_by_name(self, channel_name: str) -> Optional[Dict]:
        """Get channel by name"""
        try:
            result = self.supabase.table('youtube_channels')\
                .select('*')\
                .eq('channel_name', channel_name)\
                .execute()
            
            return result.data[0] if result.data else None
            
        except Exception as e:
            print(f"Error getting channel by name {channel_name}: {e}")
            return None

    def get_channel_by_id(self, channel_id: str) -> Optional[Dict]:
        """Get channel by ID"""
        try:
            result = self.supabase.table('youtube_channels')\
                .select('*')\
                .eq('channel_id', channel_id)\
                .execute()
            
            return result.data[0] if result.data else None
            
        except Exception as e:
            print(f"Error getting channel by ID {channel_id}: {e}")
            return None

    def get_channel_by_handle(self, handle: str) -> Optional[Dict]:
        """Get channel by handle (e.g., @channelname)"""
        try:
            # Ensure handle starts with @
            if not handle.startswith('@'):
                handle = f"@{handle}"
            
            result = self.supabase.table('youtube_channels')\
                .select('*')\
                .eq('handle', handle)\
                .execute()
            
            return result.data[0] if result.data else None
            
        except Exception as e:
            print(f"Error getting channel by handle {handle}: {e}")
            return None

    def update_channel_info(self, channel_id: str, **kwargs):
        """Update channel information"""
        try:
            update_data = {
                'updated_at': datetime.now(timezone.utc).isoformat(),
                **kwargs
            }
            
            result = self.supabase.table('youtube_channels')\
                .update(update_data)\
                .eq('channel_id', channel_id)\
                .execute()
            
            return bool(result.data)
            
        except Exception as e:
            print(f"Error updating channel {channel_id}: {e}")
            return False

    def delete_channel(self, channel_id: str) -> bool:
        """Delete a channel and all its associated data (videos, transcripts, summaries, snippets)"""
        try:
            print(f"Deleting channel {channel_id} and all associated data...")

            # First, get all videos for this channel
            videos_result = self.supabase.table('youtube_videos')\
                .select('video_id')\
                .eq('channel_id', channel_id)\
                .execute()
            
            video_ids = [video['video_id'] for video in videos_result.data] if videos_result.data else []
            
            if video_ids:
                print(f"Found {len(video_ids)} videos to delete for channel {channel_id}")
                
                # Delete all videos (this will cascade to transcripts, chapters, summaries, and snippets)
                for video_id in video_ids:
                    # Use the existing delete method which handles all cascading deletes
                    success = self.delete(video_id)
                    if not success:
                        print(f"Warning: Failed to delete video {video_id}")
                        # Continue with other videos even if one fails
            
            # Finally, delete the channel itself
            channel_response = self.supabase.table('youtube_channels')\
                .delete()\
                .eq('channel_id', channel_id)\
                .execute()
            
            if channel_response.data:
                print(f"Successfully deleted channel {channel_id}")
                return True
            else:
                print(f"No channel found with ID {channel_id}")
                return False

        except Exception as e:
            print(f"Error deleting channel {channel_id}: {e}")
            import traceback
            traceback.print_exc()
            return False

    # AI Prompts methods
    def get_ai_prompts(self) -> List[Dict]:
        """Get all AI prompts"""
        try:
            result = self.supabase.table('ai_prompts')\
                .select('*')\
                .order('is_default', desc=True)\
                .order('name')\
                .execute()
            
            return result.data if result.data else []
            
        except Exception as e:
            print(f"Error getting AI prompts: {e}")
            return []

    def get_ai_prompt_by_id(self, prompt_id: int) -> Optional[Dict]:
        """Get AI prompt by ID"""
        try:
            result = self.supabase.table('ai_prompts')\
                .select('*')\
                .eq('id', prompt_id)\
                .execute()
            
            return result.data[0] if result.data else None
            
        except Exception as e:
            print(f"Error getting AI prompt by ID {prompt_id}: {e}")
            return None

    def get_default_prompt(self) -> Optional[Dict]:
        """Get the default AI prompt"""
        try:
            result = self.supabase.table('ai_prompts')\
                .select('*')\
                .eq('is_default', True)\
                .execute()
            
            return result.data[0] if result.data else None
            
        except Exception as e:
            print(f"Error getting default AI prompt: {e}")
            return None

    def create_ai_prompt(self, name: str, prompt_text: str, is_default: bool = False, description: str = None) -> Optional[int]:
        """Create a new AI prompt"""
        try:
            prompt_data = {
                'name': name,
                'prompt_text': prompt_text,
                'is_default': is_default,
                'description': description
            }
            
            result = self.supabase.table('ai_prompts')\
                .insert(prompt_data)\
                .execute()
            
            if result.data and len(result.data) > 0:
                return result.data[0]['id']
            return None
            
        except Exception as e:
            print(f"Error creating AI prompt: {e}")
            return None

    def update_ai_prompt(self, prompt_id: int, name: str, prompt_text: str, is_default: bool = False, description: str = None) -> bool:
        """Update an existing AI prompt"""
        try:
            update_data = {
                'name': name,
                'prompt_text': prompt_text,
                'is_default': is_default,
                'description': description,
                'updated_at': datetime.now(timezone.utc).isoformat()
            }
            
            result = self.supabase.table('ai_prompts')\
                .update(update_data)\
                .eq('id', prompt_id)\
                .execute()
            
            return bool(result.data)
            
        except Exception as e:
            print(f"Error updating AI prompt {prompt_id}: {e}")
            return False

    def delete_ai_prompt(self, prompt_id: int) -> bool:
        """Delete an AI prompt (cannot delete default prompt)"""
        try:
            # Check if it's the default prompt
            prompt = self.get_ai_prompt_by_id(prompt_id)
            if prompt and prompt.get('is_default'):
                print(f"Cannot delete default prompt {prompt_id}")
                return False
            
            result = self.supabase.table('ai_prompts')\
                .delete()\
                .eq('id', prompt_id)\
                .execute()
            
            return bool(result.data)
            
        except Exception as e:
            print(f"Error deleting AI prompt {prompt_id}: {e}")
            return False

    def set_default_prompt(self, prompt_id: int) -> bool:
        """Set a prompt as the default (unsets other defaults)"""
        try:
            # The database trigger will handle unsetting other defaults
            result = self.supabase.table('ai_prompts')\
                .update({'is_default': True})\
                .eq('id', prompt_id)\
                .execute()
            
            return bool(result.data)
            
        except Exception as e:
            print(f"Error setting default prompt {prompt_id}: {e}")
            return False

    # Import Settings Methods
    def get_import_settings(self) -> Dict:
        """Get all import settings"""
        try:
            response = self.supabase.table('import_settings').select('*').execute()
            settings = {}
            
            for setting in response.data:
                key = setting['setting_key']
                value = setting['setting_value']
                setting_type = setting.get('setting_type', 'string')
                
                # Convert value based on type
                if setting_type == 'integer':
                    settings[key] = int(value) if value else 0
                elif setting_type == 'boolean':
                    settings[key] = value.lower() == 'true' if value else False
                else:
                    settings[key] = value
            
            return settings
        except Exception as e:
            print(f"Error getting import settings: {e}")
            return {}

    def get_import_setting(self, key: str, default=None):
        """Get a specific import setting"""
        try:
            response = self.supabase.table('import_settings').select('*').eq('setting_key', key).execute()
            
            if response.data:
                setting = response.data[0]
                value = setting['setting_value']
                setting_type = setting.get('setting_type', 'string')
                
                # Convert value based on type
                if setting_type == 'integer':
                    return int(value) if value else default
                elif setting_type == 'boolean':
                    return value.lower() == 'true' if value else default
                else:
                    return value
            
            return default
        except Exception as e:
            print(f"Error getting import setting {key}: {e}")
            return default

    def update_import_setting(self, key: str, value, setting_type: str = 'string') -> bool:
        """Update an import setting (insert if doesn't exist)"""
        try:
            # Convert value to string for storage
            if isinstance(value, bool):
                value_str = str(value).lower()
            else:
                value_str = str(value)
            
            # Try to update first
            response = self.supabase.table('import_settings').update({
                'setting_value': value_str,
                'setting_type': setting_type,
                'updated_at': datetime.now(timezone.utc).isoformat()
            }).eq('setting_key', key).execute()
            
            # If no rows were updated, try to insert
            if len(response.data) == 0:
                setting_data = {
                    'setting_key': key,
                    'setting_value': value_str,
                    'setting_type': setting_type,
                    'created_at': datetime.now(timezone.utc).isoformat(),
                    'updated_at': datetime.now(timezone.utc).isoformat()
                }
                
                response = self.supabase.table('import_settings').insert(setting_data).execute()
            
            return len(response.data) > 0
        except Exception as e:
            print(f"Error updating import setting {key}: {e}")
            return False

    def update_import_settings_batch(self, settings: Dict) -> bool:
        """Update multiple import settings at once"""
        try:
            for key, value in settings.items():
                # Determine setting type based on value
                if isinstance(value, bool):
                    setting_type = 'boolean'
                elif isinstance(value, int):
                    setting_type = 'integer'
                else:
                    setting_type = 'string'
                
                self.update_import_setting(key, value, setting_type)
            
            return True
        except Exception as e:
            print(f"Error updating import settings batch: {e}")
            return False


# Global database storage instance
database_storage = DatabaseStorage()