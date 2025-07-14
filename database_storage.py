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

    def _ensure_channel_exists(self, channel_id: str, channel_name: str):
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
                self.supabase.table('youtube_channels').insert(channel_data).execute()
                print(f"Created new channel: {channel_name} ({channel_id})")
            
        except Exception as e:
            print(f"Error ensuring channel exists: {e}")

    def get(self, video_id: str) -> Optional[Dict]:
        """
        Get cached transcript data for video ID from database

        Args:
            video_id: YouTube video ID

        Returns:
            Cached data dict or None if not found
        """
        try:
            # Get video metadata with channel information
            video_response = self.supabase.table('youtube_videos')\
                .select('*, youtube_channels(channel_name, channel_id, thumbnail_url)')\
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

            # Extract channel information
            channel_info = None
            if video_data.get('youtube_channels') and len(video_data['youtube_channels']) > 0:
                channel_info = video_data['youtube_channels'][0]

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

    def set(self, video_id: str, transcript: List[Dict], video_info: Dict, formatted_transcript: str, channel_id: str = None):
        """
        Store transcript data for video ID in database

        Args:
            video_id: YouTube video ID
            transcript: Raw transcript data
            video_info: Video metadata (title, chapters, etc.)
            formatted_transcript: Formatted readable transcript
        """
        try:
            # Handle channel information
            if channel_id:
                self._ensure_channel_exists(channel_id, video_info.get('channel_name', 'Unknown Channel'))

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

            # Insert or update video metadata
            video_data = {
                'video_id': video_id,
                'title': video_info.get('title'),
                'channel_id': channel_id,
                'duration': video_info.get('duration'),
                'thumbnail_url': f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg",
                'published_at': published_at,
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
            # Get all videos with their transcripts, summaries, and channel information
            # Use LEFT JOIN approach to handle missing foreign key constraints
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

                # Get channel information (manually fetch if channel_id exists)
                channel_name = 'Unknown Channel'
                channel_id = video.get('channel_id')
                
                if channel_id:
                    try:
                        # Fetch channel information from youtube_channels table
                        channel_response = self.supabase.table('youtube_channels')\
                            .select('channel_name, channel_id')\
                            .eq('channel_id', channel_id)\
                            .execute()
                        
                        if channel_response.data and len(channel_response.data) > 0:
                            channel_name = channel_response.data[0]['channel_name']
                    except Exception as e:
                        print(f"Warning: Could not fetch channel info for {channel_id}: {e}")

                cached_videos.append({
                    'video_id': video['video_id'],
                    'title': video['title'] or 'Unknown Title',
                    'channel_name': channel_name,
                    'channel_id': channel_id,
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
                            .select('channel_name, channel_id')\
                            .eq('channel_id', channel_id)\
                            .execute()
                        
                        if channel_response.data and len(channel_response.data) > 0:
                            channel_info = channel_response.data[0]
                            for video in videos:
                                video['channel_name'] = channel_info['channel_name']
                                video['channel_id'] = channel_info['channel_id']
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

    

    def get_all_channels(self):
        """Get all channels with video counts and summary counts"""
        try:
            # Get channels from youtube_channels table using simple queries (no JOINs)
            channels_result = self.supabase.table('youtube_channels')\
                .select('*')\
                .order('created_at', desc=True)\
                .execute()
            
            if channels_result.data:
                print(f"Found {len(channels_result.data)} channels in youtube_channels table")
                
                # Get all summaries for efficiency
                summaries_result = self.supabase.table('summaries').select('video_id').execute()
                summarized_video_ids = {s['video_id'] for s in summaries_result.data if s.get('video_id')}
                
                channels = []
                for channel in channels_result.data:
                    channel_id = channel['channel_id']
                    channel_name = channel['channel_name']
                    
                    # Get videos for this channel
                    channel_videos = self.get_videos_by_channel(channel_id=channel_id)
                    print(f"Channel {channel_name} ({channel_id}): Found {len(channel_videos)} videos")
                    
                    # Count summaries for this channel
                    summary_count = sum(1 for v in channel_videos if v.get('video_id') in summarized_video_ids)
                    
                    # Get recent videos (limit to 3 most recent)
                    recent_videos = {}
                    for video in channel_videos[:3]:
                        video_id = video['video_id']
                        recent_videos[video_id] = {
                            'video_info': {
                                'title': video.get('title'),
                                'thumbnail_url': f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg",
                                'duration': video.get('duration'),
                                'channel_name': video.get('channel_name')
                            },
                            'video_id': video_id,
                            'has_summary': video_id in summarized_video_ids
                        }
                    
                    channels.append({
                        'channel_id': channel_id,
                        'name': channel_name,
                        'video_count': len(channel_videos),
                        'summary_count': summary_count,
                        'thumbnail_url': channel.get('thumbnail_url'),
                        'recent_videos': recent_videos
                    })
                
                # Sort by video count
                return sorted(channels, key=lambda x: x['video_count'], reverse=True)
                
        except Exception as e:
            print(f"Error getting all channels: {e}")
            return []

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
                                    'channel_name, channel_id'
                                ).eq('channel_id', channel_id).execute()
                                
                                if channel_result.data:
                                    snippet['channel_name'] = channel_result.data[0]['channel_name']
                                    snippet['channel_id'] = channel_result.data[0]['channel_id']
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


# Global database storage instance
database_storage = DatabaseStorage()