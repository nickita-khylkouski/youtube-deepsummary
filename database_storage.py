#!/usr/bin/env python3
"""
Database storage module using Supabase for YouTube Deep Search
Replaces the file-based transcript_cache.py
"""

import os
import time
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
    
    def get(self, video_id: str) -> Optional[Dict]:
        """
        Get cached transcript data for video ID from database
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            Cached data dict or None if not found
        """
        try:
            # Get video metadata
            video_response = self.supabase.table('youtube_videos').select('*').eq('video_id', video_id).execute()
            
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
            
            # Reconstruct the cache format
            cached_data = {
                'video_id': video_id,
                'timestamp': time.mktime(self._parse_datetime(video_data['created_at']).timetuple()),
                'transcript': transcript_data['transcript_data'],
                'video_info': {
                    'title': video_data['title'],
                    'uploader': video_data['uploader'],
                    'duration': video_data['duration'],
                    'chapters': chapters
                },
                'formatted_transcript': transcript_data['formatted_transcript']
            }
            
            print(f"Database HIT for video {video_id}")
            return cached_data
            
        except Exception as e:
            print(f"Database read error for {video_id}: {e}")
            return None
    
    def set(self, video_id: str, transcript: List[Dict], video_info: Dict, formatted_transcript: str):
        """
        Store transcript data for video ID in database
        
        Args:
            video_id: YouTube video ID
            transcript: Raw transcript data
            video_info: Video metadata (title, chapters, etc.)
            formatted_transcript: Formatted readable transcript
        """
        try:
            # Insert or update video metadata
            video_data = {
                'video_id': video_id,
                'title': video_info.get('title'),
                'uploader': video_info.get('uploader'),
                'duration': video_info.get('duration'),
                'thumbnail_url': f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg",
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
    
    def save_summary(self, video_id: str, summary: str, model_used: str = 'gpt-4.1'):
        """
        Save AI summary for a video
        
        Args:
            video_id: YouTube video ID
            summary: Generated summary text
            model_used: AI model used for summary
        """
        try:
            summary_data = {
                'video_id': video_id,
                'summary_text': summary,
                'model_used': model_used,
                'updated_at': datetime.now(timezone.utc).isoformat()
            }
            
            # Delete existing summary and insert new one
            self.supabase.table('summaries').delete().eq('video_id', video_id).execute()
            self.supabase.table('summaries').insert(summary_data).execute()
            
            print(f"Summary saved for video {video_id}")
            
        except Exception as e:
            print(f"Error saving summary for {video_id}: {e}")
            raise
    
    def get_summary(self, video_id: str) -> Optional[str]:
        """
        Get saved summary for a video
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            Summary text or None if not found
        """
        try:
            response = self.supabase.table('summaries').select('summary_text').eq('video_id', video_id).execute()
            
            if response.data and len(response.data) > 0:
                return response.data[0]['summary_text']
            return None
            
        except Exception as e:
            print(f"Error getting summary for {video_id}: {e}")
            return None
    
    def clear_expired(self):
        """
        Remove expired cache files - for database, we'll keep everything
        This method is kept for compatibility with the old cache interface
        """
        print("Database storage doesn't expire - keeping all data")
        return
    
    def get_cache_info(self) -> Dict:
        """Get database statistics"""
        try:
            # Alternative count method - get all records and count them
            videos_response = self.supabase.table('youtube_videos').select('video_id').execute()
            videos_count = len(videos_response.data) if videos_response.data else 0
            
            transcripts_response = self.supabase.table('transcripts').select('video_id').execute()
            transcripts_count = len(transcripts_response.data) if transcripts_response.data else 0
            
            summaries_response = self.supabase.table('summaries').select('video_id').execute()
            summaries_count = len(summaries_response.data) if summaries_response.data else 0
            
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
        try:
            # Get all videos with their transcripts and summaries
            response = self.supabase.table('youtube_videos')\
                .select('*, transcripts(transcript_data), summaries(summary_text), video_chapters(chapters_data)')\
                .order('created_at', desc=True)\
                .execute()
            
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
                
                cached_videos.append({
                    'video_id': video['video_id'],
                    'title': video['title'] or 'Unknown Title',
                    'uploader': video['uploader'] or 'Unknown Channel',
                    'duration': video['duration'],
                    'chapters_count': chapters_count,
                    'transcript_entries': transcript_entries,
                    'cache_age_hours': round(cache_age_hours, 1),
                    'is_valid': True,  # Database entries are always valid
                    'cache_timestamp': time.mktime(created_at.timetuple()),
                    'file_size': 0,  # Not applicable for database
                    'has_summary': has_summary,
                    'created_at': video['created_at']
                })
            
            return cached_videos
            
        except Exception as e:
            print(f"Error getting all cached videos: {e}")
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

    def get_all_videos_with_summaries_grouped_by_channel(self) -> Dict[str, List[Dict]]:
        """
        Get all videos that have summaries, along with their summary text,
        grouped by channel (uploader).

        Returns:
            A dictionary where keys are channel names (uploader) and values are lists
            of video dictionaries. Each video dictionary contains:
            {'video_id': str, 'title': str, 'uploader': str, 'summary_text': str}
        """
        try:
            # Query to select video_id, title, uploader from youtube_videos
            # and summary_text from summaries, joining on video_id.
            # The join ensures we only get videos that have a summary.
            # The foreign key relationship should be: summaries.video_id -> youtube_videos.video_id

            # Correct Supabase query:
            # We need to fetch from youtube_videos and do a join with summaries.
            # The select string should specify columns from both tables.
            # Supabase foreign key joins look like: table!fk_column(joined_table_columns)
            # Or, if the FK is on the 'summaries' table pointing to 'youtube_videos',
            # we can query 'youtube_videos' and specify a join to 'summaries'.
            # Let's assume 'summaries' has a 'video_id' FK to 'youtube_videos.video_id'.
            # And 'youtube_videos' has 'uploader'.

            response = self.supabase.table('youtube_videos') \
                .select('video_id, title, uploader, summaries(summary_text)') \
                .not_.is_('summaries', 'null')  # Ensures we only get videos with at least one summary
                .order('uploader', desc=False) \
                .order('created_at', desc=True) \
                .execute()

            if not response.data:
                print("No videos with summaries found.")
                return {}

            grouped_summaries: Dict[str, List[Dict]] = {}
            for item in response.data:
                uploader = item.get('uploader') or "Unknown Channel"
                # Ensure 'summaries' is a list and not empty, and access its first element for summary_text
                summary_info = item.get('summaries')
                summary_text = None
                if isinstance(summary_info, list) and len(summary_info) > 0:
                    summary_text = summary_info[0].get('summary_text')

                if summary_text is None: # Skip if no actual summary text, though .not_.is_ should prevent this
                    continue

                video_details = {
                    'video_id': item['video_id'],
                    'title': item.get('title') or "Unknown Title",
                    'summary_text': summary_text
                    # 'uploader' is the key in grouped_summaries, so not needed inside the list item itself
                }

                if uploader not in grouped_summaries:
                    grouped_summaries[uploader] = []
                grouped_summaries[uploader].append(video_details)

            print(f"Found summaries for {len(grouped_summaries)} channels.")
            return grouped_summaries

        except Exception as e:
            print(f"Error getting all videos with summaries grouped by channel: {e}")
            # import traceback
            # traceback.print_exc() # For more detailed error during development
            return {}


# Global database storage instance
database_storage = DatabaseStorage()