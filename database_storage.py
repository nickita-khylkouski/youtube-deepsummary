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
    
    def get_videos_with_summaries_by_channel(self, channel_name: str) -> List[Dict]:
        """Get all videos with AI summaries from a specific channel"""
        try:
            # Get videos from specific channel that have summaries
            response = self.supabase.table('youtube_videos')\
                .select('*, summaries(summary_text, model_used, created_at)')\
                .eq('uploader', channel_name)\
                .not_.is_('summaries.summary_text', 'null')\
                .order('created_at', desc=True)\
                .execute()
            
            videos_with_summaries = []
            
            for video in response.data:
                if video.get('summaries') and len(video['summaries']) > 0:
                    summary_data = video['summaries'][0]
                    
                    # Calculate summary age
                    summary_created_at = self._parse_datetime(summary_data['created_at'])
                    summary_age_hours = (datetime.now(timezone.utc) - summary_created_at).total_seconds() / 3600
                    
                    videos_with_summaries.append({
                        'video_id': video['video_id'],
                        'title': video['title'] or 'Unknown Title',
                        'uploader': video['uploader'],
                        'duration': video['duration'],
                        'thumbnail_url': video['thumbnail_url'],
                        'created_at': video['created_at'],
                        'summary_text': summary_data['summary_text'],
                        'model_used': summary_data['model_used'],
                        'summary_created_at': summary_data['created_at'],
                        'summary_age_hours': round(summary_age_hours, 1)
                    })
            
            return videos_with_summaries
            
        except Exception as e:
            print(f"Error getting videos with summaries for channel {channel_name}: {e}")
            return []
    
    def get_channels_with_summaries(self) -> List[Dict]:
        """Get list of channels that have AI summaries"""
        try:
            # Get unique channels that have at least one summary
            response = self.supabase.table('youtube_videos')\
                .select('uploader, summaries(video_id)')\
                .not_.is_('summaries.video_id', 'null')\
                .execute()
            
            # Count summaries per channel
            channel_summary_counts = {}
            for video in response.data:
                uploader = video['uploader']
                if uploader and uploader != 'Unknown Channel':
                    if uploader not in channel_summary_counts:
                        channel_summary_counts[uploader] = 0
                    if video.get('summaries') and len(video['summaries']) > 0:
                        channel_summary_counts[uploader] += 1
            
            # Convert to list of channel objects
            channels = []
            for channel_name, summary_count in channel_summary_counts.items():
                if summary_count > 0:  # Only include channels with summaries
                    channels.append({
                        'name': channel_name,
                        'summary_count': summary_count
                    })
            
            # Sort by summary count (descending)
            channels.sort(key=lambda x: x['summary_count'], reverse=True)
            
            return channels
            
        except Exception as e:
            print(f"Error getting channels with summaries: {e}")
            return []


# Global database storage instance
database_storage = DatabaseStorage()