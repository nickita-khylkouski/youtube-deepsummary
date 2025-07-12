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

    def get_notes(self) -> str:
        """
        Get user notes content from database, with file fallback
        
        Returns:
            Notes content as string, empty string if none exist
        """
        try:
            # Get the latest notes entry (there should only be one)
            response = self.supabase.table('user_notes')\
                .select('notes_content')\
                .order('updated_at', desc=True)\
                .limit(1)\
                .execute()
            
            if response.data and len(response.data) > 0:
                return response.data[0]['notes_content']
            else:
                # No notes exist yet, return empty string
                return ''

        except Exception as e:
            print(f"Error getting notes from database: {e}")
            # Fallback to file-based storage
            try:
                import os
                notes_file = 'user_notes.txt'
                if os.path.exists(notes_file):
                    with open(notes_file, 'r', encoding='utf-8') as f:
                        return f.read()
                return ''
            except Exception as file_error:
                print(f"File fallback also failed: {file_error}")
                return ''

    def save_notes(self, notes_content: str) -> bool:
        """
        Save user notes to database, with file fallback
        
        Args:
            notes_content: The notes content to save
            
        Returns:
            True if successful, False if failed
        """
        try:
            # Check if notes record already exists
            existing_response = self.supabase.table('user_notes')\
                .select('id')\
                .order('updated_at', desc=True)\
                .limit(1)\
                .execute()
            
            if existing_response.data and len(existing_response.data) > 0:
                # Update existing notes
                note_id = existing_response.data[0]['id']
                response = self.supabase.table('user_notes')\
                    .update({
                        'notes_content': notes_content,
                        'updated_at': datetime.now(timezone.utc).isoformat()
                    })\
                    .eq('id', note_id)\
                    .execute()
                print(f"Notes updated: {note_id}")
            else:
                # Create new notes record
                response = self.supabase.table('user_notes')\
                    .insert({
                        'notes_content': notes_content,
                        'updated_at': datetime.now(timezone.utc).isoformat()
                    })\
                    .execute()
                print(f"New notes created")
            
            return True

        except Exception as e:
            print(f"Error saving notes to database: {e}")
            # Fallback to file-based storage
            try:
                notes_file = 'user_notes.txt'
                with open(notes_file, 'w', encoding='utf-8') as f:
                    f.write(notes_content)
                print(f"Notes saved to file fallback: {notes_file}")
                return True
            except Exception as file_error:
                print(f"File fallback also failed: {file_error}")
                return False

    def append_to_notes(self, text_to_append: str) -> bool:
        """
        Append text to existing notes
        
        Args:
            text_to_append: Text to append to current notes
            
        Returns:
            True if successful, False if failed
        """
        try:
            current_notes = self.get_notes()
            updated_notes = current_notes + text_to_append
            return self.save_notes(updated_notes)

        except Exception as e:
            print(f"Error appending to notes: {e}")
            return False

    def save_snippet(self, video_id: str, snippet_text: str, source_type: str) -> str:
        """
        Save a highlighted text snippet
        
        Args:
            video_id: YouTube video ID
            snippet_text: The highlighted text
            source_type: 'transcript' or 'summary'
            
        Returns:
            Snippet ID if successful, None if failed
        """
        try:
            snippet_data = {
                'video_id': video_id,
                'snippet_text': snippet_text,
                'source_type': source_type,
                'updated_at': datetime.now(timezone.utc).isoformat()
            }

            response = self.supabase.table('user_snippets').insert(snippet_data).execute()
            
            if response.data and len(response.data) > 0:
                snippet_id = response.data[0]['id']
                print(f"Snippet saved for video {video_id}: {snippet_id}")
                return snippet_id
            else:
                print(f"Failed to save snippet for video {video_id}")
                return None

        except Exception as e:
            print(f"Error saving snippet for {video_id}: {e}")
            # Fallback to file-based storage for snippets too
            try:
                import json
                snippets_file = 'user_snippets.json'
                
                # Load existing snippets
                try:
                    with open(snippets_file, 'r', encoding='utf-8') as f:
                        snippets = json.load(f)
                except (FileNotFoundError, json.JSONDecodeError):
                    snippets = []
                
                # Add new snippet
                snippet_id = str(len(snippets) + 1)
                snippets.append({
                    'id': snippet_id,
                    'video_id': video_id,
                    'snippet_text': snippet_text,
                    'source_type': source_type,
                    'created_at': datetime.now(timezone.utc).isoformat()
                })
                
                # Save back to file
                with open(snippets_file, 'w', encoding='utf-8') as f:
                    json.dump(snippets, f, indent=2)
                    
                print(f"Snippet saved to file fallback: {snippet_id}")
                return snippet_id
                
            except Exception as file_error:
                print(f"File fallback also failed: {file_error}")
                return None

    def get_snippets_by_video(self, video_id: str = None) -> List[Dict]:
        """
        Get snippets, optionally filtered by video ID
        
        Args:
            video_id: Optional video ID to filter snippets
            
        Returns:
            List of snippet dictionaries grouped by video
        """
        try:
            query = self.supabase.table('user_snippets')\
                .select('*, youtube_videos(title, uploader, thumbnail_url)')\
                .order('created_at', desc=True)
            
            if video_id:
                query = query.eq('video_id', video_id)
            
            response = query.execute()
            
            snippets = []
            for snippet in response.data:
                video_info = snippet.get('youtube_videos', {})
                snippets.append({
                    'id': snippet['id'],
                    'video_id': snippet['video_id'],
                    'snippet_text': snippet['snippet_text'],
                    'source_type': snippet['source_type'],
                    'created_at': snippet['created_at'],
                    'video_title': video_info.get('title'),
                    'video_uploader': video_info.get('uploader'),
                    'thumbnail_url': video_info.get('thumbnail_url') or f"https://img.youtube.com/vi/{snippet['video_id']}/maxresdefault.jpg"
                })
            
            return snippets

        except Exception as e:
            print(f"Error getting snippets from database: {e}")
            # Fallback to file-based storage
            try:
                import json
                snippets_file = 'user_snippets.json'
                
                with open(snippets_file, 'r', encoding='utf-8') as f:
                    file_snippets = json.load(f)
                
                # Filter by video_id if specified
                if video_id:
                    file_snippets = [s for s in file_snippets if s.get('video_id') == video_id]
                
                # Add video info from database for file snippets
                for snippet in file_snippets:
                    vid = snippet.get('video_id')
                    if vid:
                        try:
                            video_response = self.supabase.table('youtube_videos').select('title, uploader').eq('video_id', vid).execute()
                            if video_response.data and len(video_response.data) > 0:
                                video_data = video_response.data[0]
                                snippet['video_title'] = video_data.get('title')
                                snippet['video_uploader'] = video_data.get('uploader')
                            snippet['thumbnail_url'] = f"https://img.youtube.com/vi/{vid}/maxresdefault.jpg"
                        except:
                            snippet['video_title'] = vid
                            snippet['video_uploader'] = 'Unknown'
                            snippet['thumbnail_url'] = f"https://img.youtube.com/vi/{vid}/maxresdefault.jpg"
                
                return file_snippets
                
            except Exception as file_error:
                print(f"File fallback also failed: {file_error}")
                return []

    def get_snippets_grouped_by_video(self) -> Dict[str, Dict]:
        """
        Get all snippets grouped by video
        
        Returns:
            Dictionary with video_id as key and video info + snippets as value
        """
        try:
            snippets = self.get_snippets_by_video()
            grouped = {}
            
            for snippet in snippets:
                video_id = snippet['video_id']
                if video_id not in grouped:
                    grouped[video_id] = {
                        'video_id': video_id,
                        'video_title': snippet['video_title'],
                        'video_uploader': snippet['video_uploader'],
                        'thumbnail_url': snippet['thumbnail_url'],
                        'snippets': []
                    }
                grouped[video_id]['snippets'].append(snippet)
            
            return grouped
            
        except Exception as e:
            print(f"Error grouping snippets: {e}")
            return {}

    def get_snippets_grouped_by_channel(self) -> Dict[str, Dict]:
        """
        Get all snippets grouped by channel and then by video
        
        Returns:
            Dictionary with channel name as key and channel info + videos as value
        """
        try:
            snippets = self.get_snippets_by_video()
            grouped = {}
            
            for snippet in snippets:
                video_id = snippet['video_id']
                uploader = snippet['video_uploader'] or 'Unknown Channel'
                
                # Initialize channel if not exists
                if uploader not in grouped:
                    grouped[uploader] = {
                        'channel_name': uploader,
                        'videos': {},
                        'total_snippets': 0,
                        'recent_thumbnails': []  # Store recent video thumbnails
                    }
                
                # Initialize video if not exists in this channel
                if video_id not in grouped[uploader]['videos']:
                    grouped[uploader]['videos'][video_id] = {
                        'video_id': video_id,
                        'video_title': snippet['video_title'],
                        'video_uploader': snippet['video_uploader'],
                        'thumbnail_url': snippet['thumbnail_url'],
                        'snippets': [],
                        'latest_snippet_date': snippet['created_at']
                    }
                
                # Add snippet to video
                grouped[uploader]['videos'][video_id]['snippets'].append(snippet)
                grouped[uploader]['total_snippets'] += 1
                
                # Update latest snippet date for this video
                if snippet['created_at'] > grouped[uploader]['videos'][video_id]['latest_snippet_date']:
                    grouped[uploader]['videos'][video_id]['latest_snippet_date'] = snippet['created_at']
            
            # Add recent thumbnails for each channel (up to 4 most recent videos)
            for channel_name, channel_data in grouped.items():
                # Sort videos by latest snippet date
                sorted_videos = sorted(channel_data['videos'].items(), 
                                     key=lambda x: x[1]['latest_snippet_date'], 
                                     reverse=True)
                
                # Get up to 4 recent video thumbnails
                channel_data['recent_thumbnails'] = [
                    {
                        'video_id': video_id,
                        'thumbnail_url': video_data['thumbnail_url'],
                        'video_title': video_data['video_title']
                    }
                    for video_id, video_data in sorted_videos[:4]
                    if video_data['thumbnail_url']
                ]
            
            # Sort channels by total snippets (descending)
            sorted_channels = dict(sorted(grouped.items(), 
                                        key=lambda x: x[1]['total_snippets'], 
                                        reverse=True))
            
            return sorted_channels
            
        except Exception as e:
            print(f"Error grouping snippets by channel: {e}")
            return {}

    def delete_snippet(self, snippet_id: str) -> bool:
        """
        Delete a snippet by ID
        
        Args:
            snippet_id: UUID of the snippet to delete
            
        Returns:
            True if successful, False if failed
        """
        try:
            response = self.supabase.table('user_snippets').delete().eq('id', snippet_id).execute()
            
            if response.data and len(response.data) > 0:
                print(f"Snippet deleted: {snippet_id}")
                return True
            else:
                print(f"Snippet not found or already deleted: {snippet_id}")
                return False

        except Exception as e:
            print(f"Error deleting snippet {snippet_id}: {e}")
            # Fallback to file-based storage
            try:
                import json
                snippets_file = 'user_snippets.json'
                
                with open(snippets_file, 'r', encoding='utf-8') as f:
                    snippets = json.load(f)
                
                # Remove snippet with matching ID
                original_length = len(snippets)
                snippets = [s for s in snippets if s.get('id') != snippet_id]
                
                if len(snippets) < original_length:
                    with open(snippets_file, 'w', encoding='utf-8') as f:
                        json.dump(snippets, f, indent=2)
                    print(f"Snippet deleted from file: {snippet_id}")
                    return True
                else:
                    print(f"Snippet not found in file: {snippet_id}")
                    return False
                    
            except Exception as file_error:
                print(f"File fallback also failed: {file_error}")
                return False


# Global database storage instance
database_storage = DatabaseStorage()