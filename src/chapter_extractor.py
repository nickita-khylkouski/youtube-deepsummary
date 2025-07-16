#!/usr/bin/env python3
"""
YouTube Chapter Extractor

A module that handles chapter extraction from YouTube videos using yt-dlp
and provides fallback methods for chapter detection.
"""

import os
import re
from typing import List, Dict, Optional


class ChapterExtractor:
    """Handles chapter extraction from YouTube videos"""
    
    def __init__(self):
        """Initialize the chapter extractor with proxy configuration"""
        self.proxy = os.getenv('YOUTUBE_PROXY')
    
    def extract_video_info(self, video_id: str, extract_chapters: bool = True) -> Dict[str, any]:
        """
        Extract comprehensive video information using YouTube Data API as primary source,
        with yt-dlp fallback for chapters and additional metadata
        
        Args:
            video_id: YouTube video ID
            extract_chapters: Whether to extract chapter information (default: True)
            
        Returns:
            Dictionary containing video information including chapters
        """
        # Try YouTube Data API first (faster, more reliable for basic metadata)
        youtube_api_data = self._extract_info_youtube_api(video_id)
        
        # If chapters are needed or YouTube API failed, try yt-dlp
        yt_dlp_data = None
        if extract_chapters or not youtube_api_data:
            yt_dlp_data = self._extract_info_yt_dlp(video_id, extract_chapters)
        
        # Merge data sources with YouTube Data API taking priority for most fields
        merged_data = self._merge_video_info(youtube_api_data, yt_dlp_data)
        
        # Add chapters from yt-dlp if requested
        if extract_chapters and yt_dlp_data and yt_dlp_data.get('chapters'):
            merged_data['chapters'] = yt_dlp_data['chapters']
        elif not extract_chapters:
            merged_data['chapters'] = None
        
        return merged_data
    
    def _extract_info_youtube_api(self, video_id: str) -> Dict[str, any]:
        """Extract video info using YouTube Data API"""
        try:
            from .youtube_api import youtube_api
            
            if not youtube_api.is_available():
                print(f"YouTube Data API not available for video {video_id}")
                return None
            
            print(f"Extracting video info using YouTube Data API for {video_id}")
            api_data = youtube_api.get_video_info(video_id)
            
            if api_data:
                print(f"Successfully got video info from YouTube Data API for {video_id}")
                return api_data
            else:
                print(f"No data returned from YouTube Data API for {video_id}")
                return None
                
        except Exception as e:
            print(f"Error extracting video info with YouTube Data API for {video_id}: {e}")
            return None
    
    def _extract_info_yt_dlp(self, video_id: str, extract_chapters: bool = True) -> Dict[str, any]:
        """Extract video info using yt-dlp (primarily for chapters)"""
        try:
            import yt_dlp
            print(f"Extracting video info using yt-dlp for {video_id}")
            
            # Configure yt-dlp options
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
            }
            
            # Add proxy configuration if available
            if self.proxy:
                ydl_opts['proxy'] = f'http://{self.proxy}'
                print(f"Using proxy for yt-dlp extraction: {self.proxy}")
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                video_info = ydl.extract_info(
                    f'https://www.youtube.com/watch?v={video_id}', 
                    download=False
                )
                
                # Extract chapters only if requested
                formatted_chapters = None
                if extract_chapters:
                    chapters = video_info.get('chapters', [])
                    if chapters:
                        formatted_chapters = []
                        for chapter in chapters:
                            formatted_chapters.append({
                                'title': chapter.get('title', 'Unknown Chapter'),
                                'time': chapter.get('start_time', 0)
                            })
                
                return {
                    'title': video_info.get('title', 'Unknown Title'),
                    'chapters': formatted_chapters,
                    'duration': video_info.get('duration'),
                    'channel_name': video_info.get('channel', video_info.get('uploader', 'Unknown Channel')),
                    'channel_id': video_info.get('channel_id'),
                    'description': video_info.get('description', ''),
                    'view_count': video_info.get('view_count'),
                    'like_count': video_info.get('like_count'),
                    'upload_date': video_info.get('upload_date'),
                    'thumbnail': video_info.get('thumbnail'),
                    'tags': video_info.get('tags', []),
                    'api_source': 'yt_dlp'
                }
                
        except ImportError:
            print("yt-dlp not available for video info extraction")
            return None
        except Exception as e:
            print(f"Error extracting video info with yt-dlp for {video_id}: {e}")
            return None
    
    def _merge_video_info(self, youtube_api_data: Dict, yt_dlp_data: Dict) -> Dict[str, any]:
        """Merge video info from YouTube Data API and yt-dlp, prioritizing YouTube Data API"""
        
        if not youtube_api_data and not yt_dlp_data:
            return self._extract_info_fallback("")
        
        if not youtube_api_data:
            return yt_dlp_data or self._extract_info_fallback("")
        
        if not yt_dlp_data:
            return youtube_api_data
        
        # YouTube Data API takes priority for most fields
        merged = youtube_api_data.copy()
        
        # Use yt-dlp data as fallback for missing fields
        fallback_fields = [
            'title', 'description', 'channel_name', 'channel_id', 
            'duration', 'thumbnail', 'upload_date', 'view_count', 
            'like_count', 'tags'
        ]
        
        for field in fallback_fields:
            if not merged.get(field) and yt_dlp_data.get(field):
                merged[field] = yt_dlp_data[field]
                merged[f'{field}_source'] = 'yt_dlp_fallback'
        
        # Always prefer yt-dlp for chapters (YouTube Data API doesn't provide them)
        if yt_dlp_data.get('chapters'):
            merged['chapters'] = yt_dlp_data['chapters']
        
        # Set primary source indicator
        merged['primary_source'] = 'youtube_data_api'
        
        return merged
    
    def extract_chapters_only(self, video_id: str) -> Optional[List[Dict]]:
        """
        Extract only chapter information from a video
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            List of chapters or None if no chapters found
        """
        video_info = self.extract_video_info(video_id)
        return video_info.get('chapters')
    
    def _extract_info_fallback(self, video_id: str, extract_chapters: bool = True) -> Dict[str, any]:
        """
        Fallback method to extract basic video info without yt-dlp
        This is a basic implementation that could be enhanced with web scraping
        
        Args:
            video_id: YouTube video ID
            extract_chapters: Whether to extract chapter information (default: True)
            
        Returns:
            Basic video information dictionary
        """
        print(f"Using fallback method for video {video_id}")
        return {
            'title': f'Video {video_id}',
            'chapters': None if not extract_chapters else None,
            'duration': None,
            'channel_name': 'Unknown Channel',
            'channel_id': None,
            'description': '',
            'view_count': None,
            'like_count': None,
            'upload_date': None,
            'thumbnail': f'https://img.youtube.com/vi/{video_id}/maxresdefault.jpg',
            'tags': []
        }
    
    def parse_chapters_from_description(self, description: str) -> Optional[List[Dict]]:
        """
        Parse chapters from video description text
        
        Args:
            description: Video description text
            
        Returns:
            List of parsed chapters or None if no chapters found
        """
        if not description:
            return None
        
        # Common timestamp patterns
        timestamp_patterns = [
            r'(\d{1,2}:\d{2}(?::\d{2})?)\s*[-–—]\s*(.+)',  # MM:SS - Title or HH:MM:SS - Title
            r'(\d{1,2}:\d{2}(?::\d{2})?)\s+(.+)',         # MM:SS Title or HH:MM:SS Title
            r'(\d{1,2}:\d{2}(?::\d{2})?)\s*[:\-–—]\s*(.+)', # MM:SS: Title or MM:SS - Title
        ]
        
        chapters = []
        lines = description.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            for pattern in timestamp_patterns:
                match = re.search(pattern, line)
                if match:
                    timestamp_str = match.group(1)
                    title = match.group(2).strip()
                    
                    # Convert timestamp to seconds
                    time_seconds = self._timestamp_to_seconds(timestamp_str)
                    
                    chapters.append({
                        'title': title,
                        'time': time_seconds
                    })
                    break
        
        # Sort chapters by time and return only if we have multiple chapters
        if len(chapters) >= 2:
            chapters.sort(key=lambda x: x['time'])
            return chapters
        
        return None
    
    def _timestamp_to_seconds(self, timestamp_str: str) -> int:
        """
        Convert timestamp string to seconds
        
        Args:
            timestamp_str: Timestamp in format MM:SS or HH:MM:SS
            
        Returns:
            Time in seconds
        """
        parts = timestamp_str.split(':')
        if len(parts) == 2:  # MM:SS
            minutes, seconds = map(int, parts)
            return minutes * 60 + seconds
        elif len(parts) == 3:  # HH:MM:SS
            hours, minutes, seconds = map(int, parts)
            return hours * 3600 + minutes * 60 + seconds
        else:
            return 0
    
    def validate_chapters(self, chapters: List[Dict], video_duration: Optional[int] = None) -> List[Dict]:
        """
        Validate and clean up chapter data
        
        Args:
            chapters: List of chapter dictionaries
            video_duration: Video duration in seconds (optional)
            
        Returns:
            Cleaned and validated chapter list
        """
        if not chapters:
            return []
        
        # Remove duplicates and sort by time
        seen_times = set()
        valid_chapters = []
        
        for chapter in chapters:
            time = chapter.get('time', 0)
            title = chapter.get('title', '').strip()
            
            # Skip if no title or duplicate time
            if not title or time in seen_times:
                continue
            
            # Skip if time is beyond video duration
            if video_duration and time > video_duration:
                continue
            
            seen_times.add(time)
            valid_chapters.append({
                'title': title,
                'time': time
            })
        
        # Sort by time
        valid_chapters.sort(key=lambda x: x['time'])
        
        return valid_chapters
    
    def format_chapter_timestamp(self, seconds) -> str:
        """
        Format seconds into readable timestamp
        
        Args:
            seconds: Time in seconds (int or float)
            
        Returns:
            Formatted timestamp string
        """
        # Convert to int to handle both int and float inputs
        seconds = int(seconds) if seconds is not None else 0
        
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        seconds = seconds % 60
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes:02d}:{seconds:02d}"


# Global chapter extractor instance
chapter_extractor = ChapterExtractor()


def extract_video_info(video_id: str, extract_chapters: bool = True) -> Dict[str, any]:
    """
    Convenience function to extract video info using the global extractor
    
    Args:
        video_id: YouTube video ID
        extract_chapters: Whether to extract chapter information (default: True)
        
    Returns:
        Dictionary containing video information
    """
    return chapter_extractor.extract_video_info(video_id, extract_chapters)


def extract_video_chapters(video_id: str) -> Optional[List[Dict]]:
    """
    Convenience function to extract only chapters using the global extractor
    
    Args:
        video_id: YouTube video ID
        
    Returns:
        List of chapters or None
    """
    return chapter_extractor.extract_chapters_only(video_id)