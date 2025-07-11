#!/usr/bin/env python3
"""
Database storage module using Supabase for YouTube Deep Summary
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

    def get_videos_by_channel(self, channel_name: str) -> List[Dict]:
        """Get all videos from a specific channel"""
        try:
            # Query videos by uploader (channel name)
            response = self.supabase.table('youtube_videos')\
                .select('*')\
                .eq('uploader', channel_name)\
                .order('created_at', desc=True)\
                .execute()

            return response.data if response.data else []

        except Exception as e:
            print(f"Error getting videos for channel {channel_name}: {e}")
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

    

    def get_all_channels(self):
        """Get all channels with video counts and summary counts"""
        try:
            # Try RPC first (will fail if function doesn't exist)
            try:
                result = self.supabase.rpc('get_channel_stats').execute()
                if result.data:
                    return result.data
            except Exception as rpc_error:
                print(f"RPC get_channel_stats not available: {rpc_error}")
            
            # Fallback: get channels manually
            print("Using fallback method to get channels...")
            videos_result = self.supabase.table('youtube_videos').select('video_id, uploader').execute()
            summaries_result = self.supabase.table('summaries').select('video_id').execute()

            print(f"Found {len(videos_result.data)} videos total")
            
            # Count videos by channel
            channel_counts = {}
            for video in videos_result.data:
                uploader = video.get('uploader')
                if uploader and uploader.strip():  # Check for non-empty uploader
                    channel_counts[uploader] = channel_counts.get(uploader, 0) + 1

            print(f"Found {len(channel_counts)} unique channels")
            
            if not channel_counts:
                print("No channels found - videos may have empty/null uploader field")
                return []

            # Get video IDs that have summaries
            summarized_video_ids = {s['video_id'] for s in summaries_result.data if s.get('video_id')}
            print(f"Found {len(summarized_video_ids)} videos with summaries")

            # Count summaries by channel
            channels = []
            for channel_name, video_count in channel_counts.items():
                # Get videos for this channel to count summaries
                channel_videos = self.get_videos_by_channel(channel_name)
                summary_count = sum(1 for v in channel_videos if v.get('video_id') in summarized_video_ids)

                channels.append({
                    'name': channel_name,
                    'video_count': video_count,
                    'summary_count': summary_count
                })
                print(f"Channel '{channel_name}': {video_count} videos, {summary_count} summaries")

            return sorted(channels, key=lambda x: x['video_count'], reverse=True)

        except Exception as e:
            print(f"Error getting all channels: {e}")
            return []

    def save_memory(self, video_id: str, selected_text: str, source_type: str = 'transcript', 
                   context_text: str = None, timestamp_seconds: int = None, note: str = None) -> bool:
        """
        Save a user memory (selected text snippet)
        
        Args:
            video_id: YouTube video ID
            selected_text: The text selected by the user
            source_type: 'transcript' or 'summary'
            context_text: Additional context around the selection
            timestamp_seconds: For transcript memories, the timestamp
            note: User's optional note
            
        Returns:
            bool: True if successful
        """
        try:
            memory_data = {
                'video_id': video_id,
                'selected_text': selected_text,
                'context_text': context_text,
                'source_type': source_type,
                'timestamp_seconds': timestamp_seconds,
                'note': note,
                'created_at': datetime.now(timezone.utc).isoformat()
            }
            
            self.supabase.table('memories').insert(memory_data).execute()
            print(f"Memory saved for video {video_id}: {selected_text[:50]}...")
            return True
            
        except Exception as e:
            print(f"Error saving memory for {video_id}: {e}")
            return False

    def get_memories(self, video_id: str = None, group_by_channel: bool = False) -> List[Dict]:
        """
        Get memories, optionally filtered by video ID and/or grouped by channel
        
        Args:
            video_id: Optional video ID filter
            group_by_channel: If True, returns memories grouped by channel
            
        Returns:
            List of memory dictionaries or grouped channel dictionaries
        """
        try:
            query = self.supabase.table('memories')\
                .select('*, youtube_videos(title, uploader, thumbnail_url)')\
                .order('created_at', desc=True)
                
            if video_id:
                query = query.eq('video_id', video_id)
                
            response = query.execute()
            
            memories = []
            for memory in response.data:
                video_info = memory.get('youtube_videos')
                memories.append({
                    'id': memory['id'],
                    'video_id': memory['video_id'],
                    'selected_text': memory['selected_text'],
                    'context_text': memory['context_text'],
                    'source_type': memory['source_type'],
                    'timestamp_seconds': memory['timestamp_seconds'],
                    'note': memory['note'],
                    'created_at': memory['created_at'],
                    'video_title': video_info.get('title') if video_info else None,
                    'video_uploader': video_info.get('uploader') if video_info else None,
                    'thumbnail_url': video_info.get('thumbnail_url') if video_info else f"https://img.youtube.com/vi/{memory['video_id']}/maxresdefault.jpg"
                })
            
            if group_by_channel:
                return self._group_memories_by_channel(memories)
            else:
                return memories
            
        except Exception as e:
            print(f"Error getting memories: {e}")
            return []

    def _group_memories_by_channel(self, memories: List[Dict]) -> List[Dict]:
        """
        Group memories by channel
        
        Args:
            memories: List of memory dictionaries
            
        Returns:
            List of channel dictionaries with grouped memories
        """
        channels = {}
        
        for memory in memories:
            uploader = memory.get('video_uploader') or 'Unknown Channel'
            
            if uploader not in channels:
                channels[uploader] = {
                    'channel_name': uploader,
                    'memory_count': 0,
                    'memories': []
                }
            
            channels[uploader]['memories'].append(memory)
            channels[uploader]['memory_count'] += 1
        
        # Sort channels by memory count (descending)
        return sorted(channels.values(), key=lambda x: x['memory_count'], reverse=True)

    def delete_memory(self, memory_id: str) -> bool:
        """
        Delete a specific memory
        
        Args:
            memory_id: UUID of the memory to delete
            
        Returns:
            bool: True if successful
        """
        try:
            response = self.supabase.table('memories').delete().eq('id', memory_id).execute()
            print(f"Memory deleted: {memory_id}")
            return True
            
        except Exception as e:
            print(f"Error deleting memory {memory_id}: {e}")
            return False

    def get_memory_stats(self) -> Dict:
        """Get statistics about saved memories"""
        try:
            response = self.supabase.table('memories').select('id, source_type, video_id').execute()
            
            total_memories = len(response.data) if response.data else 0
            transcript_memories = sum(1 for m in response.data if m.get('source_type') == 'transcript')
            summary_memories = sum(1 for m in response.data if m.get('source_type') == 'summary')
            unique_videos = len(set(m['video_id'] for m in response.data)) if response.data else 0
            
            return {
                'total_memories': total_memories,
                'transcript_memories': transcript_memories,
                'summary_memories': summary_memories,
                'unique_videos': unique_videos
            }
            
        except Exception as e:
            print(f"Error getting memory stats: {e}")
            return {
                'total_memories': 0,
                'transcript_memories': 0,
                'summary_memories': 0,
                'unique_videos': 0
            }


# Global database storage instance
database_storage = DatabaseStorage()